#!/usr/bin/env python3
"""
Nuvio -> your own TestFlight
============================

Takes the official Nuvio iOS build (the unsigned IPA the Nuvio team publishes
for AltStore/SideStore), signs it with YOUR Apple Developer account and uploads
it to TestFlight. Installing from TestFlight does not need Developer Mode.

Run on a Mac:   python3 nuvio_testflight.py

Needs: an App Store Connect API key (.p8, Admin access). Nothing to install:
only Python 3 + tools that ship with macOS (curl, openssl, security, codesign).
Uploading uses Xcode's altool if Xcode is installed, otherwise Apple's
Transporter app.

Re-run it any time to pull the newest Nuvio release and push it to TestFlight.

Options:
  --ipa PATH        use a local IPA instead of downloading the latest release
  --skip-upload     stop after producing the signed IPA
  --bundle-id ID    bundle ID to use on first run (default com.elbarkatawy.nuvio)
"""

import argparse
import base64
import glob
import hashlib
import json
import os
import plistlib
import re
import secrets
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state")
# Set by the GitHub workflow when no stored certificate was supplied: make a certificate for this
# build only and revoke it at the end, so certificates never pile up toward Apple's limit.
EPHEMERAL_CERT = os.environ.get("NUVIO_EPHEMERAL_CERT") == "1"
EPHEMERAL_CREATED = []
CONFIG_PATH = os.path.join(STATE, "config.json")
LOG_PATH = os.path.join(STATE, "last-run.log")

SOURCE_URL = "https://raw.githubusercontent.com/NuvioMedia/NuvioMobile/cmp-rewrite/store.json"
API = os.environ.get("NUVIO_ASC_API", "https://api.appstoreconnect.apple.com")
WWDR_URL = "https://www.apple.com/certificateauthority/AppleWWDRCAG3.cer"
ASC_APPS_URL = "https://appstoreconnect.apple.com/apps"
TRANSPORTER_STORE_URL = "https://apps.apple.com/us/app/transporter/id1450874784?mt=12"
TRANSPORTER_CLI = "/Applications/Transporter.app/Contents/itms/bin/iTMSTransporter"

DEFAULT_BUNDLE_ID = "com.elbarkatawy.nuvio"
WIDGET_SUFFIX = ".DownloadsWidgetExtension"
SHARE_SUFFIX = ".ShareExtension"
GROUP_NAME = "Me"
OPENSSL = "/usr/bin/openssl" if os.path.exists("/usr/bin/openssl") else "openssl"


# --------------------------------------------------------------------------- output

class Tee(object):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
            st.flush()

    def flush(self):
        for st in self.streams:
            st.flush()


def say(msg=""):
    print(msg, flush=True)


def step(msg):
    say("")
    say("==> " + msg)


def die(msg):
    say("")
    say("STOPPED: " + msg)
    say("(Full log: %s)" % LOG_PATH)
    sys.exit(1)


def run(cmd, input_bytes=None, check=True, quiet=False):
    p = subprocess.run(cmd, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        err = (p.stderr or b"").decode(errors="replace").strip()
        out = (p.stdout or b"").decode(errors="replace").strip()
        die("command failed: %s\n%s\n%s" % (" ".join(cmd[:3]) + " ...", out[-2000:], err[-2000:]))
    if not quiet and p.returncode != 0:
        say((p.stderr or b"").decode(errors="replace").strip()[-1500:])
    return p


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


# --------------------------------------------------------------------------- config

def load_config(args):
    os.makedirs(STATE, exist_ok=True)
    os.chmod(STATE, 0o700)
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)

    if not cfg.get("key_id") or not os.path.exists(cfg.get("p8_path", "")):
        step("First-run setup: App Store Connect API key")
        candidates = []
        for d in (HERE, os.path.expanduser("~/Downloads"), os.path.expanduser("~/Desktop"),
                  os.path.expanduser("~/Documents")):
            candidates += sorted(glob.glob(os.path.join(d, "AuthKey_*.p8")), key=os.path.getmtime, reverse=True)
        p8 = None
        if candidates:
            say("Found API key file: " + candidates[0])
            if ask("Use it? [Y/n] ").lower() not in ("n", "no"):
                p8 = candidates[0]
        while not p8:
            p8 = ask("Drag your AuthKey_XXXXXXXXXX.p8 file into this window, then press Return: ")
            p8 = os.path.expanduser(p8.strip().strip("'\"").replace("\\ ", " "))
            if not os.path.isfile(p8):
                say("  Can't find that file, try again.")
                p8 = None
        m = re.search(r"AuthKey_([A-Z0-9]{10})\.p8$", os.path.basename(p8))
        key_id = m.group(1) if m else ""
        while not re.fullmatch(r"[A-Z0-9]{10}", key_id):
            key_id = ask("Key ID (10 characters, shown next to the key in App Store Connect): ").upper()
        issuer = ""
        while not re.fullmatch(r"[0-9a-fA-F-]{36}", issuer):
            issuer = ask("Issuer ID (the long ID at the top of the API Keys page): ")
        dest = os.path.join(STATE, "AuthKey_%s.p8" % key_id)
        shutil.copyfile(p8, dest)
        os.chmod(dest, 0o600)
        cfg.update({"key_id": key_id, "issuer_id": issuer.lower(), "p8_path": dest})

    if not cfg.get("bundle_id"):
        cfg["bundle_id"] = args.bundle_id or DEFAULT_BUNDLE_ID
    save_config(cfg)
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)


# --------------------------------------------------------------------------- API

def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def der_to_raw_sig(der):
    """ECDSA DER signature -> raw r||s (64 bytes) as JWT ES256 wants."""
    if der[0] != 0x30:
        raise ValueError("bad DER signature")
    i = 2
    if der[1] & 0x80:
        i = 2 + (der[1] & 0x7F)

    def read_int(j):
        if der[j] != 0x02:
            raise ValueError("bad DER integer")
        ln = der[j + 1]
        return der[j + 2:j + 2 + ln], j + 2 + ln

    r, i = read_int(i)
    s, i = read_int(i)
    return r.lstrip(b"\0").rjust(32, b"\0") + s.lstrip(b"\0").rjust(32, b"\0")


class ApiError(Exception):
    def __init__(self, status, body):
        self.status = status
        self.body = body
        detail = body
        try:
            errs = json.loads(body).get("errors", [])
            detail = "; ".join("%s: %s" % (e.get("title", ""), e.get("detail", "")) for e in errs) or body
        except Exception:
            pass
        self.detail = detail
        Exception.__init__(self, "HTTP %s - %s" % (status, detail[:800]))


class Asc(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self._tok = None
        self._tok_time = 0

    def token(self):
        if self._tok and time.time() - self._tok_time < 15 * 60:
            return self._tok
        now = int(time.time())
        header = {"alg": "ES256", "kid": self.cfg["key_id"], "typ": "JWT"}
        payload = {"iss": self.cfg["issuer_id"], "iat": now, "exp": now + 19 * 60, "aud": "appstoreconnect-v1"}
        signing_input = (b64u(json.dumps(header, separators=(",", ":")).encode()) + "." +
                         b64u(json.dumps(payload, separators=(",", ":")).encode()))
        p = run([OPENSSL, "dgst", "-sha256", "-sign", self.cfg["p8_path"]], input_bytes=signing_input.encode())
        self._tok = signing_input + "." + b64u(der_to_raw_sig(p.stdout))
        self._tok_time = time.time()
        return self._tok

    def call(self, method, path, body=None, params=None):
        url = API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        cmd = ["curl", "-sS", "-X", method, url, "--max-time", "300", "-w", "\n%{http_code}",
               "-H", "Authorization: Bearer " + self.token(), "-H", "Content-Type: application/json"]
        data = None
        if body is not None:
            cmd += ["--data-binary", "@-"]
            data = json.dumps(body).encode()
        p = None
        for attempt in range(3):
            p = subprocess.run(cmd, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if p.returncode == 0:
                break
            time.sleep(3)
        if p.returncode != 0:
            die("network error talking to App Store Connect: " + p.stderr.decode(errors="replace"))
        text, _, code = p.stdout.decode(errors="replace").rpartition("\n")
        code = int(code or 0)
        if code >= 400 or code == 0:
            raise ApiError(code, text)
        return json.loads(text) if text.strip() else {}

    def get(self, path, **params):
        return self.call("GET", path, params=params or None)

    def post(self, path, body):
        return self.call("POST", path, body=body)

    def delete(self, path):
        return self.call("DELETE", path)


# --------------------------------------------------------------------------- steps

def check_key(asc):
    step("Checking your App Store Connect API key")
    try:
        asc.get("/v1/apps", limit="1")
    except ApiError as e:
        if e.status == 401:
            die("Apple rejected the API key (401). Check the Key ID / Issuer ID, or delete "
                "%s and run again to re-enter them." % CONFIG_PATH)
        raise
    say("Key works.")


def ensure_bundle_id(asc, identifier, name):
    res = asc.get("/v1/bundleIds", **{"filter[identifier]": identifier, "limit": "200"})
    for b in res.get("data", []):
        if b["attributes"]["identifier"] == identifier:
            say("Bundle ID exists: " + identifier)
            return b["id"]
    try:
        res = asc.post("/v1/bundleIds", {"data": {"type": "bundleIds", "attributes": {
            "identifier": identifier, "name": name, "platform": "IOS"}}})
    except ApiError as e:
        die("couldn't register bundle ID %s (%s).\nIf it's taken by someone else, edit \"bundle_id\" in %s "
            "to something unique and run again." % (identifier, e.detail, CONFIG_PATH))
    say("Registered bundle ID: " + identifier)
    return res["data"]["id"]


def find_app(asc, bundle_id):
    res = asc.get("/v1/apps", **{"filter[bundleId]": bundle_id})
    for a in res.get("data", []):
        if a["attributes"]["bundleId"] == bundle_id:
            return a
    return None


def ensure_app(asc, bundle_id):
    step("Looking for the app record in App Store Connect")
    app = find_app(asc, bundle_id)
    tries = 0
    while not app:
        tries += 1
        if tries > 6:
            die("still no app record for %s." % bundle_id)
        say("")
        say("One manual step (Apple doesn't allow this via API). In App Store Connect:")
        say("  Apps -> '+' -> New App")
        say("    Platform:  iOS")
        say("    Name:      anything not already taken on the App Store, e.g. 'Nuvio Mo Personal'")
        say("    Language:  English (U.S.)")
        say("    Bundle ID: pick  %s  from the list" % bundle_id)
        say("    SKU:       nuvio-personal")
        say("    User Access: Full Access -> Create")
        subprocess.run(["open", ASC_APPS_URL], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ask("Press Return here once you've clicked Create... ")
        app = find_app(asc, bundle_id)
        if not app:
            say("Not visible yet (can take a minute).")
    say("App record: %s (Apple ID %s)" % (app["attributes"].get("name"), app["id"]))
    return app


def sha1_hex(b):
    return hashlib.sha1(b).hexdigest().upper()


def login_keychain_identities():
    p = run(["security", "find-identity", "-v", "-p", "codesigning"], check=False, quiet=True)
    return set(re.findall(r"\b([0-9A-F]{40})\b", p.stdout.decode(errors="replace")))


def ensure_certificate(asc):
    """Returns dict(cert_id, sha1, key, der) for an Apple Distribution certificate we can sign with.
    If key is None the identity lives in the login keychain instead of our own files."""
    step("Distribution certificate")
    meta_path = os.path.join(STATE, "dist.json")
    key_path = os.path.join(STATE, "dist.key")
    der_path = os.path.join(STATE, "dist.cer")
    if EPHEMERAL_CERT:
        for path in (meta_path, key_path, der_path):
            if os.path.exists(path):
                os.remove(path)
    if os.path.exists(meta_path) and os.path.exists(key_path) and os.path.exists(der_path):
        with open(meta_path) as f:
            meta = json.load(f)
        try:
            c = asc.get("/v1/certificates/" + meta["cert_id"])
            exp = c["data"]["attributes"].get("expirationDate", "")
            if exp and exp[:10] > time.strftime("%Y-%m-%d", time.gmtime(time.time() + 86400)):
                say("Reusing the certificate created on a previous run (expires %s)." % exp[:10])
                with open(der_path, "rb") as f:
                    meta["der"] = f.read()
                meta["key"] = key_path
                return meta
        except ApiError as e:
            if e.status not in (404, 409):
                raise
        say("Previous certificate is gone or expiring; making a new one.")

    # New key + CSR
    tmp_key = key_path + ".new"
    csr_path = os.path.join(STATE, "dist.csr")
    run([OPENSSL, "req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout", tmp_key, "-out", csr_path,
         "-subj", "/CN=Nuvio TestFlight Signing/C=US"])
    os.chmod(tmp_key, 0o600)
    with open(csr_path) as f:
        csr = f.read()
    created = None
    for ctype in ("DISTRIBUTION", "IOS_DISTRIBUTION"):
        try:
            created = asc.post("/v1/certificates", {"data": {"type": "certificates", "attributes": {
                "certificateType": ctype, "csrContent": csr}}})
            break
        except ApiError as e:
            last_err = e
    if created:
        der = base64.b64decode(created["data"]["attributes"]["certificateContent"])
        os.replace(tmp_key, key_path)
        with open(der_path, "wb") as f:
            f.write(der)
        meta = {"cert_id": created["data"]["id"], "sha1": sha1_hex(der)}
        with open(meta_path, "w") as f:
            json.dump(meta, f)
        meta.update({"der": der, "key": key_path})
        say("Created a new Apple Distribution certificate (%s)." % created["data"]["attributes"].get("name", ""))
        if EPHEMERAL_CERT:
            EPHEMERAL_CREATED.append(meta["cert_id"])
        return meta

    os.remove(tmp_key)
    if EPHEMERAL_CERT:
        die("Apple wouldn't issue a distribution certificate for this build: %s\n"
            "Your account is probably at its limit of distribution certificates. Add the NUVIO_SIGNING "
            "secret (see FORK.md) so builds reuse your Mac's certificate." % last_err.detail[:300])
    # Probably at the certificate limit. Use an existing one whose private key is in the login keychain.
    say("Apple wouldn't issue another distribution certificate: " + last_err.detail[:300])
    have = login_keychain_identities()
    res = asc.get("/v1/certificates", **{"filter[certificateType]": "DISTRIBUTION,IOS_DISTRIBUTION", "limit": "200"})
    for c in res.get("data", []):
        der = base64.b64decode(c["attributes"]["certificateContent"])
        if sha1_hex(der) in have:
            say("Using your existing certificate from the login keychain: %s" % c["attributes"].get("name"))
            say("(macOS may ask to let codesign use it: click 'Always Allow'.)")
            return {"cert_id": c["id"], "sha1": sha1_hex(der), "der": der, "key": None}
    die("your account already has the maximum number of distribution certificates and none of their "
        "private keys are on this Mac.\nRevoke one you don't need at "
        "https://developer.apple.com/account/resources/certificates/list and run this again.")


class SigningKeychain(object):
    """Temporary keychain so codesign never pops up password prompts."""

    def __init__(self, cert):
        self.cert = cert
        self.path = os.path.join(tempfile.gettempdir(), "nuvio-signing-%d.keychain-db" % os.getpid())
        self.pw = secrets.token_hex(16)
        self.old_list = None

    def __enter__(self):
        if self.cert["key"] is None:
            return self
        work = tempfile.mkdtemp(prefix="nuvio-kc-")
        pem = os.path.join(work, "c.pem")
        p12 = os.path.join(work, "c.p12")
        p12pw = secrets.token_hex(12)
        with open(pem, "w") as f:
            f.write("-----BEGIN CERTIFICATE-----\n")
            b = base64.b64encode(self.cert["der"]).decode()
            f.write("\n".join(b[i:i + 64] for i in range(0, len(b), 64)))
            f.write("\n-----END CERTIFICATE-----\n")
        # -legacy keeps macOS `security import` happy if a Homebrew OpenSSL 3 is first on PATH
        p = run([OPENSSL, "pkcs12", "-export", "-legacy", "-inkey", self.cert["key"], "-in", pem, "-out", p12,
                 "-passout", "pass:" + p12pw], check=False, quiet=True)
        if p.returncode != 0:
            run([OPENSSL, "pkcs12", "-export", "-inkey", self.cert["key"], "-in", pem, "-out", p12,
                 "-passout", "pass:" + p12pw])
        run(["security", "delete-keychain", self.path], check=False, quiet=True)
        run(["security", "create-keychain", "-p", self.pw, self.path])
        run(["security", "set-keychain-settings", "-lut", "7200", self.path])
        run(["security", "unlock-keychain", "-p", self.pw, self.path])
        run(["security", "import", p12, "-k", self.path, "-P", p12pw, "-T", "/usr/bin/codesign", "-T",
             "/usr/bin/security"])
        wwdr = os.path.join(work, "wwdr.cer")
        if run(["curl", "-sSfL", "-o", wwdr, WWDR_URL], check=False, quiet=True).returncode == 0:
            run(["security", "import", wwdr, "-k", self.path], check=False, quiet=True)
        run(["security", "set-key-partition-list", "-S", "apple-tool:,apple:,codesign:", "-s", "-k", self.pw,
             self.path], check=False, quiet=True)
        out = run(["security", "list-keychains", "-d", "user"], check=False, quiet=True).stdout.decode()
        self.old_list = [l.strip().strip('"') for l in out.splitlines() if l.strip()]
        run(["security", "list-keychains", "-d", "user", "-s", self.path] + self.old_list)
        shutil.rmtree(work, ignore_errors=True)
        return self

    def __exit__(self, *exc):
        if self.cert["key"] is None:
            return False
        if self.old_list is not None:
            run(["security", "list-keychains", "-d", "user", "-s"] + self.old_list, check=False, quiet=True)
        run(["security", "delete-keychain", self.path], check=False, quiet=True)
        return False

    def codesign_args(self):
        args = ["codesign", "--force", "--sign", self.cert["sha1"], "--timestamp=none"]
        if self.cert["key"] is not None:
            args += ["--keychain", self.path]
        return args


def make_profile(asc, name, bundle_res_id, cert_id, out_path):
    res = asc.get("/v1/profiles", **{"filter[name]": name, "limit": "200"})
    for p in res.get("data", []):
        if p["attributes"].get("name") == name:
            try:
                asc.delete("/v1/profiles/" + p["id"])
            except ApiError:
                pass
    res = asc.post("/v1/profiles", {"data": {
        "type": "profiles",
        "attributes": {"name": name, "profileType": "IOS_APP_STORE"},
        "relationships": {
            "bundleId": {"data": {"type": "bundleIds", "id": bundle_res_id}},
            "certificates": {"data": [{"type": "certificates", "id": cert_id}]},
        }}})
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(res["data"]["attributes"]["profileContent"]))
    say("Provisioning profile ready: " + name)
    return out_path


def entitlements_from_profile(profile_path, bundle_id, out_path):
    p = run(["security", "cms", "-D", "-i", profile_path])
    prof = plistlib.loads(p.stdout)
    ents = dict(prof["Entitlements"])
    team = prof["TeamIdentifier"][0]
    if "keychain-access-groups" in ents:
        ents["keychain-access-groups"] = ["%s.%s" % (team, bundle_id)]
    ents["get-task-allow"] = False
    with open(out_path, "wb") as f:
        plistlib.dump(ents, f)
    return team


def latest_release():
    step("Finding the latest Nuvio iOS release")
    p = run(["curl", "-sSfL", "--max-time", "60", SOURCE_URL])
    src = json.loads(p.stdout)
    app = [a for a in src["apps"] if a.get("bundleIdentifier") == "com.nuvio.media"] or src["apps"]
    v = app[0]["versions"][0]
    say("Latest: Nuvio %s (build %s, released %s)" % (v["version"], v["buildVersion"], v.get("date", "?")[:10]))
    return v


def get_ipa(args):
    if args.ipa:
        return os.path.abspath(os.path.expanduser(args.ipa)), None
    v = latest_release()
    dl = os.path.join(STATE, "downloads")
    os.makedirs(dl, exist_ok=True)
    dest = os.path.join(dl, os.path.basename(urllib.parse.urlparse(v["downloadURL"]).path))
    want = (v.get("sha256") or "").lower()

    def ok(path):
        if not os.path.exists(path):
            return False
        if not want:
            return True
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest() == want

    if not ok(dest):
        say("Downloading %s (%.0f MB)..." % (os.path.basename(dest), v.get("size", 0) / 1e6))
        run(["curl", "-fL", "--progress-bar", "-o", dest, v["downloadURL"]])
        if not ok(dest):
            die("downloaded IPA doesn't match the checksum the Nuvio team published.")
        say("Checksum verified.")
    else:
        say("Already downloaded and verified.")
    return dest, v


def encode_version(v):
    parts = [int(x) for x in (str(v).split(".") + ["0", "0"])[:3]]
    return (parts[0] << 16) | (parts[1] << 8) | parts[2]


def lower_macho_minos(path, target):
    """Lower the minimum iOS version stamped inside a Mach-O binary (thin or fat) to `target`.
    The bundled MPVKit libraries are stamped 100.0, which App Store Connect rejects (ITMS-90208).
    Returns True if the file was changed."""
    with open(path, "rb") as f:
        d = bytearray(f.read())
    if len(d) < 32:
        return False
    tgt = encode_version(target)
    magic = struct.unpack(">I", d[:4])[0]
    if magic == 0xCAFEBABE:
        n = struct.unpack(">I", d[4:8])[0]
        offs = [struct.unpack(">IIIII", d[8 + i * 20:28 + i * 20])[2] for i in range(n)]
    elif magic == 0xCAFEBABF:
        n = struct.unpack(">I", d[4:8])[0]
        offs = [struct.unpack(">IIQQII", d[8 + i * 32:40 + i * 32])[2] for i in range(n)]
    else:
        offs = [0]
    changed = False
    for o in offs:
        m = struct.unpack("<I", d[o:o + 4])[0]
        if m == 0xFEEDFACF:
            p = o + 32
        elif m == 0xFEEDFACE:
            p = o + 28
        else:
            continue
        ncmds = struct.unpack("<I", d[o + 16:o + 20])[0]
        for _ in range(ncmds):
            cmd, size = struct.unpack("<II", d[p:p + 8])
            field = p + 12 if cmd == 0x32 else (p + 8 if cmd == 0x25 else None)  # LC_BUILD_VERSION / LC_VERSION_MIN_IPHONEOS
            if field is not None and struct.unpack("<I", d[field:field + 4])[0] > tgt:
                d[field:field + 4] = struct.pack("<I", tgt)
                changed = True
            p += size
    if changed:
        with open(path, "wb") as f:
            f.write(d)
    return changed


def read_plist(path):
    with open(path, "rb") as f:
        raw = f.read()
    return plistlib.loads(raw), (plistlib.FMT_BINARY if raw.startswith(b"bplist") else plistlib.FMT_XML)


def write_plist(path, data, fmt):
    with open(path, "wb") as f:
        plistlib.dump(data, f, fmt=fmt)


PRIVACY_APP = {
    "NSPrivacyTracking": False,
    "NSPrivacyTrackingDomains": [],
    "NSPrivacyCollectedDataTypes": [],
    "NSPrivacyAccessedAPITypes": [
        {"NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryUserDefaults",
         "NSPrivacyAccessedAPITypeReasons": ["CA92.1"]},
        {"NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryFileTimestamp",
         "NSPrivacyAccessedAPITypeReasons": ["C617.1"]},
        {"NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategorySystemBootTime",
         "NSPrivacyAccessedAPITypeReasons": ["35F9.1"]},
        {"NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryDiskSpace",
         "NSPrivacyAccessedAPITypeReasons": ["E174.1"]},
    ],
}
PRIVACY_LIB = {"NSPrivacyTracking": False, "NSPrivacyTrackingDomains": [],
               "NSPrivacyCollectedDataTypes": [], "NSPrivacyAccessedAPITypes": []}


def prepare_bundle(ipa, work, bundle_id, build_version):
    """Unpack the IPA and patch it so App Store Connect accepts it."""
    step("Preparing the app bundle")
    run(["ditto", "-x", "-k", ipa, work])
    apps = glob.glob(os.path.join(work, "Payload", "*.app"))
    if len(apps) != 1:
        die("unexpected IPA layout")
    app = apps[0]

    for junk in glob.glob(os.path.join(work, "__MACOSX")) + glob.glob(os.path.join(app, "**", ".DS_Store"),
                                                                    recursive=True):
        shutil.rmtree(junk, ignore_errors=True) if os.path.isdir(junk) else os.remove(junk)
    for dp, dn, fn in os.walk(app):
        for d in list(dn):
            if d == "_CodeSignature":
                shutil.rmtree(os.path.join(dp, d))
                dn.remove(d)
        for f in fn:
            if f == "embedded.mobileprovision":
                os.remove(os.path.join(dp, f))

    info_path = os.path.join(app, "Info.plist")
    info, fmt = read_plist(info_path)
    short = info["CFBundleShortVersionString"]
    min_os = info.get("MinimumOSVersion", "16.1")
    info["CFBundleIdentifier"] = bundle_id
    info["CFBundleVersion"] = build_version
    # Nuvio only uses standard HTTPS/TLS encryption (exempt), so TestFlight won't stop to ask.
    info["ITSAppUsesNonExemptEncryption"] = False
    write_plist(info_path, info, fmt)
    say("App: %s  version %s (%s)" % (bundle_id, short, build_version))

    for ext in glob.glob(os.path.join(app, "PlugIns", "*.appex")):
        p = os.path.join(ext, "Info.plist")
        d, f2 = read_plist(p)
        old = d["CFBundleIdentifier"]
        d["CFBundleIdentifier"] = bundle_id + "." + old.split(".")[-1]
        d["CFBundleVersion"] = build_version
        d["CFBundleShortVersionString"] = short
        write_plist(p, d, f2)
        say("Extension: " + d["CFBundleIdentifier"])

    fixed = 0
    for fw in glob.glob(os.path.join(app, "Frameworks", "*.framework")):
        p = os.path.join(fw, "Info.plist")
        if not os.path.exists(p):
            continue
        d, f2 = read_plist(p)
        try:
            too_high = float(str(d.get("MinimumOSVersion", "0")).split(".")[0]) > float(min_os.split(".")[0])
        except ValueError:
            too_high = True
        if too_high or "MinimumOSVersion" not in d:
            d["MinimumOSVersion"] = min_os
            write_plist(p, d, f2)
            fixed += 1
        exe = os.path.join(fw, d.get("CFBundleExecutable", os.path.basename(fw)[:-len(".framework")]))
        if os.path.exists(exe) and lower_macho_minos(exe, min_os):
            fixed += 0 if too_high else 1
        name = os.path.basename(fw).lower()
        if name in ("libssl.framework", "libcrypto.framework") and not os.path.exists(
                os.path.join(fw, "PrivacyInfo.xcprivacy")):
            with open(os.path.join(fw, "PrivacyInfo.xcprivacy"), "wb") as f:
                plistlib.dump(PRIVACY_LIB, f)
    if fixed:
        say("Fixed MinimumOSVersion on %d bundled frameworks (they said 100.0, Apple rejects that)." % fixed)
    if not os.path.exists(os.path.join(app, "PrivacyInfo.xcprivacy")):
        with open(os.path.join(app, "PrivacyInfo.xcprivacy"), "wb") as f:
            plistlib.dump(PRIVACY_APP, f)
    return app, short


def sign_bundle(app, kc, app_profile, app_ents, ext_profiles):
    step("Signing")
    base = kc.codesign_args()
    nested = sorted(glob.glob(os.path.join(app, "Frameworks", "*.framework")) +
                    glob.glob(os.path.join(app, "Frameworks", "*.dylib")))
    for item in nested:
        run(base + [item])
    say("Signed %d frameworks." % len(nested))
    for ext, (prof, ents) in sorted(ext_profiles.items()):
        shutil.copyfile(prof, os.path.join(ext, "embedded.mobileprovision"))
        run(base + ["--entitlements", ents, "--generate-entitlement-der", ext])
        say("Signed " + os.path.basename(ext))
    shutil.copyfile(app_profile, os.path.join(app, "embedded.mobileprovision"))
    run(base + ["--entitlements", app_ents, "--generate-entitlement-der", app])
    run(["codesign", "--verify", "--deep", "--strict", app])
    say("Signed and verified " + os.path.basename(app))


def package(work, out_ipa):
    if os.path.exists(out_ipa):
        os.remove(out_ipa)
    p = subprocess.run(["zip", "-qry", "-X", out_ipa, "Payload"], cwd=work)
    if p.returncode != 0:
        die("zip failed")
    say("Signed IPA: " + out_ipa)


def pick_build_number(asc, app_id, short, upstream):
    try:
        res = asc.get("/v1/builds", **{"filter[app]": app_id, "filter[preReleaseVersion.version]": short,
                                       "limit": "200"})
        used = set(b["attributes"]["version"] for b in res.get("data", []))
    except ApiError:
        used = set()
    cand, n = str(upstream), 0
    while cand in used:
        n += 1
        cand = "%s.%d" % (upstream, n)
    return cand


DUPLICATE_BUILD = re.compile(
    r"(?i)redundant binary|already been used|already uploaded a build|"
    r"higher (version )?than (that of )?the previously uploaded|\b(90061|90186|90189)\b")


def next_build_number(build):
    parts = str(build).split(".")
    if len(parts) == 1 or not parts[-1].isdigit():
        return "%s.1" % build
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def upload(cfg, ipa, app_id, bundle_id, build, short):
    step("Uploading to App Store Connect (a few minutes)")
    keydir = os.path.expanduser("~/.appstoreconnect/private_keys")
    os.makedirs(keydir, exist_ok=True)
    keycopy = os.path.join(keydir, "AuthKey_%s.p8" % cfg["key_id"])
    if not os.path.exists(keycopy):
        shutil.copyfile(cfg["p8_path"], keycopy)
        os.chmod(keycopy, 0o600)
    auth = ["--apiKey", cfg["key_id"], "--apiIssuer", cfg["issuer_id"]]

    has_altool = subprocess.run(["xcrun", "--find", "altool"], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).returncode == 0
    attempts = []
    if has_altool:
        attempts.append(["xcrun", "altool", "--upload-package", ipa, "--type", "ios", "--apple-id", app_id,
                         "--bundle-id", bundle_id, "--bundle-version", build,
                         "--bundle-short-version-string", short] + auth)
        attempts.append(["xcrun", "altool", "--upload-app", "-f", ipa, "-t", "ios"] + auth)
    if os.path.exists(TRANSPORTER_CLI):
        attempts.append([TRANSPORTER_CLI, "-m", "upload", "-assetFile", ipa, "-apiKey", cfg["key_id"],
                         "-apiIssuer", cfg["issuer_id"], "-v", "informational"])
    for cmd in attempts:
        say("Trying: " + " ".join(cmd[:3]) + " ...")
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = p.stdout.decode(errors="replace")
        say(out.strip()[-3000:])
        # altool prints stray "ERROR: ... Failed to create URL for 'CDUploaderStateInfoResumeFilePath'"
        # lines even on a good upload, so its own success banner decides, not the word "error".
        succeeded = re.search(r"UPLOAD SUCCEEDED|No errors uploading", out) is not None
        if p.returncode == 0 and (succeeded or not re.search(r"(?i)\berror\b.*(fail|invalid|ITMS-)", out)):
            say("Upload accepted.")
            return True
        if DUPLICATE_BUILD.search(out):
            return "duplicate"
        if re.search(r"ITMS-|Validation failed|Invalid Bundle|iris-code|\(9\d{4}\)", out):
            # A real validation problem, not a tool problem: other tools would hit the same wall.
            die("Apple rejected the build. The ITMS error above says why.")
    say("")
    say("Couldn't upload automatically (Xcode not installed?). Do it by hand, takes a minute:")
    say("  1. Get Apple's free 'Transporter' app from the Mac App Store (opening it now).")
    say("  2. Sign in, drag this file into it, click Deliver:")
    say("       " + ipa)
    if os.path.exists("/Applications/Transporter.app"):
        subprocess.run(["open", "-a", "Transporter", ipa])
    else:
        subprocess.run(["open", TRANSPORTER_STORE_URL])
    subprocess.run(["open", "-R", ipa])
    ans = ask("Press Return once Transporter says 'Delivered' (or type q to quit)... ")
    return ans.lower() != "q"


def ensure_tester_group(asc, app_id):
    step("TestFlight: making sure you're an internal tester")
    try:
        res = asc.get("/v1/betaGroups", **{"filter[app]": app_id, "limit": "200"})
        group = None
        for g in res.get("data", []):
            a = g["attributes"]
            if a.get("isInternalGroup") and a.get("hasAccessToAllBuilds"):
                group = g
                break
        if not group:
            group = asc.post("/v1/betaGroups", {"data": {
                "type": "betaGroups",
                "attributes": {"name": GROUP_NAME, "isInternalGroup": True, "hasAccessToAllBuilds": True},
                "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}}})["data"]
            say("Created internal tester group '%s' (gets every build automatically)." % GROUP_NAME)
        gid = group["id"]

        users = asc.get("/v1/users", limit="200").get("data", [])
        me = ([u for u in users if "ACCOUNT_HOLDER" in u["attributes"].get("roles", [])] or users)[0]
        email = me["attributes"]["username"]
        try:
            asc.post("/v1/betaTesters", {"data": {
                "type": "betaTesters",
                "attributes": {"email": email, "firstName": me["attributes"].get("firstName", ""),
                               "lastName": me["attributes"].get("lastName", "")},
                "relationships": {"betaGroups": {"data": [{"type": "betaGroups", "id": gid}]}}}})
        except ApiError as e:
            if e.status != 409:
                raise
            t = asc.get("/v1/betaTesters", **{"filter[email]": email}).get("data", [])
            if t:
                try:
                    asc.post("/v1/betaGroups/%s/relationships/betaTesters" % gid,
                             {"data": [{"type": "betaTesters", "id": t[0]["id"]}]})
                except ApiError as e2:
                    if e2.status != 409:
                        raise
        say("Tester: %s is in group '%s'." % (email, group["attributes"]["name"]))
        return email
    except (ApiError, KeyError, IndexError) as e:
        say("Couldn't set up testers automatically (%s)." % e)
        say("Do it by hand: App Store Connect -> your app -> TestFlight -> Internal Testing -> '+',")
        say("name it 'Me', tick 'Enable automatic distribution', add yourself.")
        return None


def wait_for_processing(asc, app_id, short, build):
    step("Waiting for Apple to process the build (usually 5-30 min; Ctrl-C is safe, TestFlight will still email you)")
    deadline = time.time() + 60 * 60
    last = None
    while time.time() < deadline:
        try:
            res = asc.get("/v1/builds", **{"filter[app]": app_id, "filter[version]": build,
                                           "filter[preReleaseVersion.version]": short})
            data = res.get("data", [])
        except ApiError as e:
            data = []
            say("  (status check failed: %s)" % e)
        state = data[0]["attributes"].get("processingState") if data else "NOT_VISIBLE_YET"
        if state != last:
            say("  %s  %s" % (time.strftime("%H:%M"), state))
            last = state
        if state == "VALID":
            return True
        if state in ("INVALID", "FAILED"):
            die("Apple marked the build %s. Check your email from App Store Connect for the reason." % state)
        time.sleep(float(os.environ.get("NUVIO_POLL_SECONDS", "30")))
    say("Still processing after an hour. It'll show up in TestFlight when Apple finishes.")
    return False


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ipa")
    ap.add_argument("--skip-upload", action="store_true")
    ap.add_argument("--bundle-id")
    ap.add_argument("--build-number", help="force a build number instead of choosing one")
    args = ap.parse_args()

    os.makedirs(STATE, exist_ok=True)
    log = open(LOG_PATH, "w")
    sys.stdout = Tee(sys.__stdout__, log)

    if sys.platform != "darwin" and not os.environ.get("NUVIO_ALLOW_NON_MAC"):
        die("run this on your Mac.")
    for tool in ("curl", "codesign", "security", "ditto", "zip"):
        if not shutil.which(tool):
            die("missing '%s' (are you on macOS?)" % tool)

    say("Nuvio -> TestFlight")
    cfg = load_config(args)
    asc = Asc(cfg)
    check_key(asc)

    bundle_id = cfg["bundle_id"]
    widget_id = bundle_id + WIDGET_SUFFIX
    share_id = bundle_id + SHARE_SUFFIX
    step("Bundle IDs")
    app_bid = ensure_bundle_id(asc, bundle_id, "Nuvio Personal")
    widget_bid = ensure_bundle_id(asc, widget_id, "Nuvio Downloads Widget")
    share_bid = ensure_bundle_id(asc, share_id, "Nuvio Share Extension")
    app = ensure_app(asc, bundle_id)
    app_id = app["id"]

    cert = ensure_certificate(asc)

    step("Provisioning profiles")
    prof_dir = os.path.join(STATE, "profiles")
    os.makedirs(prof_dir, exist_ok=True)
    app_prof = make_profile(asc, "Nuvio TestFlight App", app_bid, cert["cert_id"],
                            os.path.join(prof_dir, "app.mobileprovision"))
    widget_prof = make_profile(asc, "Nuvio TestFlight Widget", widget_bid, cert["cert_id"],
                               os.path.join(prof_dir, "widget.mobileprovision"))
    share_prof = make_profile(asc, "Nuvio TestFlight Share", share_bid, cert["cert_id"],
                              os.path.join(prof_dir, "share.mobileprovision"))
    app_ents = os.path.join(prof_dir, "app.entitlements")
    widget_ents = os.path.join(prof_dir, "widget.entitlements")
    share_ents = os.path.join(prof_dir, "share.entitlements")
    team = entitlements_from_profile(app_prof, bundle_id, app_ents)
    entitlements_from_profile(widget_prof, widget_id, widget_ents)
    entitlements_from_profile(share_prof, share_id, share_ents)
    say("Team ID: " + team)

    ipa, release = get_ipa(args)
    # Peek at the version to choose a build number that hasn't been used yet.
    probe = tempfile.mkdtemp(prefix="nuvio-probe-")
    run(["ditto", "-x", "-k", ipa, probe])
    pinfo, _ = read_plist(glob.glob(os.path.join(probe, "Payload", "*.app", "Info.plist"))[0])
    shutil.rmtree(probe, ignore_errors=True)
    short = pinfo["CFBundleShortVersionString"]
    build = args.build_number or pick_build_number(asc, app_id, short, pinfo["CFBundleVersion"])

    def sign_and_package(build_number):
        work = tempfile.mkdtemp(prefix="nuvio-build-")
        try:
            app_path, _ = prepare_bundle(ipa, work, bundle_id, build_number)
            ext_profiles = {}
            for ext in glob.glob(os.path.join(app_path, "PlugIns", "*.appex")):
                if os.path.basename(ext) == "DownloadsWidgetExtension.appex":
                    ext_profiles[ext] = (widget_prof, widget_ents)
                elif os.path.basename(ext) == "ShareExtension.appex":
                    ext_profiles[ext] = (share_prof, share_ents)
                else:
                    die("unexpected extension %s; this script only knows the downloads widget and the share extension." % ext)
            with SigningKeychain(cert) as kc:
                sign_bundle(app_path, kc, app_prof, app_ents, ext_profiles)
            out_dir = os.path.join(HERE, "output")
            os.makedirs(out_dir, exist_ok=True)
            signed = os.path.join(out_dir, "Nuvio-%s-%s-signed.ipa" % (short, build_number))
            package(work, signed)
            return signed
        finally:
            shutil.rmtree(work, ignore_errors=True)

    out_ipa = sign_and_package(build)

    if args.skip_upload:
        say("\nDone (--skip-upload).")
        return

    tester = ensure_tester_group(asc, app_id)
    result = upload(cfg, out_ipa, app_id, bundle_id, build, short)
    retries = 0
    while result == "duplicate":
        # Apple remembers the build number of an upload it later rejected, even though that
        # build never shows up in the builds list. Bump the number, re-sign and try again.
        retries += 1
        if retries > 5:
            die("Apple keeps saying the build number is already used (last tried %s)." % build)
        build = next_build_number(build)
        say("")
        say("Apple already has a build with that number. Re-signing as build %s and uploading again." % build)
        out_ipa = sign_and_package(build)
        result = upload(cfg, out_ipa, app_id, bundle_id, build, short)
    if not result:
        die("upload not finished.")
    if os.environ.get("NUVIO_NO_WAIT") == "1":
        say("Uploaded build %s. Apple processes it in the next 5-30 minutes; TestFlight shows it then." % build)
        return
    done = wait_for_processing(asc, app_id, short, build)

    say("")
    say("=" * 60)
    say("All set%s. On your iPhone:" % ("" if done else " (Apple is still processing)"))
    say("  1. Install 'TestFlight' from the App Store.")
    say("  2. Open the TestFlight invite email%s and tap 'View in TestFlight'"
        % ((" sent to " + tester) if tester else ""))
    say("     (or just open TestFlight, signed in with that Apple ID).")
    say("  3. Tap Install on Nuvio. No Developer Mode needed.")
    say("Builds last 90 days. Run this script again for a new Nuvio release or to renew.")
    say("=" * 60)


def revoke_ephemeral_certificates():
    if not EPHEMERAL_CREATED:
        return
    try:
        asc = Asc(load_config(argparse.Namespace(bundle_id=None)))
        for cert_id in EPHEMERAL_CREATED:
            asc.delete("/v1/certificates/" + cert_id)
            say("Revoked this build's temporary distribution certificate (uploaded builds are unaffected).")
    except Exception as e:  # never hide the real result of the run
        say("Couldn't revoke the temporary certificate %s: %s" % (EPHEMERAL_CREATED, e))


if __name__ == "__main__":
    try:
        main()
    except ApiError as e:
        die("App Store Connect said: %s" % e)
    except KeyboardInterrupt:
        say("\nStopped.")
        sys.exit(130)
    finally:
        revoke_ephemeral_certificates()
