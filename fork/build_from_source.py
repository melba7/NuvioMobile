#!/usr/bin/env python3
"""
Build Nuvio from source with one fix, then send it to TestFlight.

Apple rejects the official Nuvio build (ITMS-90338) because its plugin encryption code calls
CommonCrypto's private AES-GCM functions. nuvio-public-gcm.patch replaces that code with an
AES-GCM built only on public APIs (tested against NIST vectors and Java's AES-GCM).

Run on your Mac:   python3 ~/Downloads/Nuvio-TestFlight/build_from_source.py

What it does:
  1. checks Xcode, Java 17+ and the Android SDK (Nuvio's build tool configures Android too)
  2. downloads the source of the latest Nuvio release and applies the patch
  3. copies the account-server address and its public client key from the official build
     (the Nuvio team adds these only to their own builds; the app needs them to start)
  4. builds the app (first time: 30-60 min and a few GB of downloads)
  5. checks the result no longer contains the private functions
  6. hands the app to nuvio_testflight.py, which signs and uploads it
"""

import base64
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nuvio_testflight as tf  # noqa: E402

PATCH = os.path.join(HERE, "nuvio-public-gcm.patch")
DOWNLOADS_PATCH = os.path.join(HERE, "nuvio-downloads.patch")
SOURCE_TAG = "0.6.12-beta"  # the release both patches were written and tested against
_tag_file = os.path.join(HERE, "UPSTREAM_TAG")
if os.path.exists(_tag_file):  # the GitHub fork keeps the tested tag here; its nightly check moves it
    with open(_tag_file) as _f:
        SOURCE_TAG = _f.read().strip() or SOURCE_TAG
DOWNLOADS_PATCH_2 = os.path.join(HERE, "nuvio-downloads-2.patch")
DOWNLOADS_PATCH_3 = os.path.join(HERE, "nuvio-downloads-3.patch")
SHARE_RESUME_PATCH = os.path.join(HERE, "nuvio-share-resume.patch")  # Clip finder, applied last
PATCHES = (PATCH, DOWNLOADS_PATCH, DOWNLOADS_PATCH_2, DOWNLOADS_PATCH_3, SHARE_RESUME_PATCH)
REPO = "https://github.com/NuvioMedia/NuvioMobile.git"
BUILD_LOG = os.path.join(tf.STATE, "build.log")
PRIVATE_SYMBOLS = (b"CCCryptorGCMEncrypt", b"CCCryptorGCMDecrypt", b"CCCryptorGCMFinal", b"CCCryptorGCMAddAAD")


def say(msg=""):
    print(msg, flush=True)


def die(msg):
    say("")
    say("STOPPED: " + msg)
    say("(Build log: %s)" % BUILD_LOG)
    sys.exit(1)


def capture(cmd, **kw):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
        return p.returncode, p.stdout.decode(errors="replace")
    except OSError as e:
        return 127, str(e)


# ------------------------------------------------------------------ toolchain checks

def check_xcode():
    tf.step("Xcode")
    code, out = capture(["xcodebuild", "-version"])
    if code != 0:
        die("Xcode isn't set up for command-line builds:\n%s\nOpen Xcode once, then run:  "
            "sudo xcode-select -s /Applications/Xcode.app" % out.strip())
    say(out.strip().splitlines()[0])
    m = re.search(r"Xcode (\d+)", out)
    if m and int(m.group(1)) < 27:
        say("Note: Nuvio's own builds use Xcode 27.1. An older Xcode may fail to compile it; "
            "if so, update Xcode from the App Store and run this again.")


def java_version(home):
    java = os.path.join(home, "bin", "java")
    if not os.path.exists(java):
        return None
    _, out = capture([java, "-version"])
    m = re.search(r'version "(\d+)', out)
    return int(m.group(1)) if m else None


def find_java():
    tf.step("Java")
    candidates = []
    if os.environ.get("JAVA_HOME"):
        candidates.append(os.environ["JAVA_HOME"])
    for v in ("17", "21", "24", "25"):
        code, out = capture(["/usr/libexec/java_home", "-v", v])
        if code == 0:
            candidates.append(out.strip().splitlines()[-1])
    candidates += [
        "/Applications/Android Studio.app/Contents/jbr/Contents/Home",
        "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home",
        "/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home",
        "/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home",
        "/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home",
    ]
    for home in candidates:
        v = java_version(home)
        if v and 17 <= v <= 25:
            say("Using Java %d at %s" % (v, home))
            return home
    say("No Java 17-25 found. Nuvio's build tool needs one.")
    if shutil.which("brew"):
        if tf.ask("Install Java 17 (Temurin) with Homebrew now? [Y/n] ").lower() not in ("n", "no"):
            if subprocess.call(["brew", "install", "--cask", "temurin@17"]) == 0:
                code, out = capture(["/usr/libexec/java_home", "-v", "17"])
                if code == 0 and java_version(out.strip()):
                    return out.strip()
    die("install Java 17 from https://adoptium.net (pick macOS, aarch64, JDK 17, .pkg), then run this again.")


def find_android_sdk():
    for home in (os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"),
                 os.path.expanduser("~/Library/Android/sdk")):
        if home and os.path.isdir(os.path.join(home, "platforms")):
            say("Android SDK: " + home)
            return home
    say("No Android SDK found. The build may stop with 'SDK location not found'; if it does, install "
        "Android Studio (it sets up the SDK on first launch) and run this again.")
    return None


# ------------------------------------------------------------------ source + config

def official_server_settings(official_ipa):
    """The account-server address, its public (anon) client key and the backup address, as built
    into the official app. Kotlin/Native stores string constants as UTF-16."""
    with zipfile.ZipFile(official_ipa) as z:
        info_name = [n for n in z.namelist() if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist", n)][0]
        exe = plistlib.loads(z.read(info_name))["CFBundleExecutable"]
        data = z.read(info_name.rsplit("/", 1)[0] + "/" + exe)
    found = [m.decode("utf-16-le") for m in re.findall(rb"(?:[\x20-\x7e]\x00){10,}", data)]
    for i, s in enumerate(found):
        if not (s.startswith("eyJ") and s.count(".") == 2):
            continue
        try:
            part = s.split(".")[1]
            claims = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        except Exception:
            continue
        if claims.get("role") != "anon" or claims.get("iss") != "supabase":
            continue
        url = found[i - 1] if i > 0 else ""
        fallback = found[i + 1] if i + 1 < len(found) and found[i + 1].startswith("https://") else ""
        if url.startswith("https://"):
            return url, s, fallback
    return None


def patches_fingerprint():
    """Short hash of the contents of all PATCHES, so a changed patch means a fresh download + patch."""
    h = hashlib.sha256()
    for patch in PATCHES:
        with open(patch, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:12]


def prepare_source(tag, official_ipa):
    tf.step("Nuvio source (%s)" % tag)
    src = os.path.join(HERE, "source", tag)
    marker = os.path.join(src, ".nuvio-patched-" + patches_fingerprint())
    if os.path.exists(marker):
        say("Already downloaded and patched: " + src)
    else:
        if os.path.exists(src):
            shutil.rmtree(src)
        os.makedirs(os.path.dirname(src), exist_ok=True)
        code, out = capture(["git", "clone", "--depth", "1", "--branch", tag, REPO, src])
        if code != 0:
            die("couldn't download the source:\n" + out[-1500:])
        for patch in PATCHES:
            code, out = capture(["git", "-C", src, "apply", "--whitespace=nowarn", patch])
            if code != 0:
                die("%s doesn't apply to this Nuvio release (their code changed):\n%s\n"
                    "Send me this message and I'll update the patch." % (os.path.basename(patch), out[-1500:]))
        open(marker, "w").close()
        say("Downloaded and patched.")

    settings = official_server_settings(official_ipa)
    if not settings:
        die("couldn't find the account-server settings in the official build.")
    url, key, fallback = settings
    with open(os.path.join(src, "local.properties"), "w") as f:
        f.write("NUVIO_SUPABASE_URL=%s\nNUVIO_SUPABASE_ANON_KEY=%s\nNUVIO_SUPABASE_FALLBACK_URL=%s\n"
                % (url, key, fallback))
    say("Account server (from the official app): %s%s" % (url, (" (backup %s)" % fallback) if fallback else ""))
    return src


# ------------------------------------------------------------------ build

def stream(cmd, cwd, env, log):
    log.write("\n$ %s\n" % " ".join(cmd))
    log.flush()
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    tail = []
    for raw in iter(p.stdout.readline, b""):
        line = raw.decode(errors="replace")
        log.write(line)
        tail.append(line)
        tail = tail[-60:]
        # Keep the terminal readable: show progress lines, not every compiler line.
        if re.search(r"(?i)^> Task |BUILD (SUCCEEDED|FAILED)|error:|warning: unable|Created |Downloading|"
                     r"Fetching|Resolve Package|CompileSwift|Ld |\*\* ", line):
            sys.stdout.write("  " + line[:160].rstrip() + "\n")
            sys.stdout.flush()
    return p.wait(), "".join(tail)


def build(src, java_home, android_home):
    tf.step("Building Nuvio (first time 30-60 min; it's fine to leave it)")
    _, mem = capture(["sysctl", "-n", "hw.memsize"])
    try:
        gb = int(mem.strip()) / 2 ** 30
    except ValueError:
        gb = 16
    heap = "4608M" if gb >= 15 else "3072M"
    env = os.environ.copy()
    env.update({
        "JAVA_HOME": java_home,
        "PATH": os.path.join(java_home, "bin") + os.pathsep + env.get("PATH", ""),
        "NUVIO_IOS_DISTRIBUTION": "full",
        "IOS_CONFIGURATION": "Release",
        "GRADLE_OPTS": "-Dfile.encoding=UTF-8",
        "KOTLIN_DAEMON_JVMARGS": "-Xmx2048M",
        "NUVIO_GRADLE_JVMARGS": "-Xmx%s -Dfile.encoding=UTF-8 -XX:MaxMetaspaceSize=768M" % heap,
        "NUVIO_KOTLIN_NATIVE_JVMARGS": "-Xmx%s" % heap,
    })
    if android_home:
        env["ANDROID_HOME"] = android_home
    with open(BUILD_LOG, "w") as log:
        for script in ("./scripts/prepare-ios-dependencies.sh", "./scripts/build-ios-ipa.sh"):
            say("Running " + script)
            code, tail = stream([script], src, env, log)
            if code != 0:
                say("".join(tail.splitlines(True)[-25:]))
                if "SDK location not found" in tail:
                    die("the build needs the Android SDK. Install Android Studio, open it once so it "
                        "sets up the SDK, then run this again.")
                die("the build failed (last lines above). Send me a screenshot, or the file %s" % BUILD_LOG)
    ipas = sorted(f for f in os.listdir(os.path.join(src, "build", "ios-ipa")) if f.endswith("-full-release.ipa"))
    if not ipas:
        die("the build finished but no IPA was produced.")
    return os.path.join(src, "build", "ios-ipa", ipas[-1])


def verify_no_private_gcm(ipa):
    tf.step("Checking the new build")
    with zipfile.ZipFile(ipa) as z:
        info_name = [n for n in z.namelist() if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist", n)][0]
        exe = plistlib.loads(z.read(info_name))["CFBundleExecutable"]
        data = z.read(info_name.rsplit("/", 1)[0] + "/" + exe)
    left = [s.decode() for s in PRIVATE_SYMBOLS if s in data]
    if left:
        die("the new build still references %s; not uploading it." % ", ".join(left))
    say("No private AES-GCM functions in the app. Good to upload.")


def main():
    os.makedirs(tf.STATE, exist_ok=True)
    if sys.platform != "darwin":
        die("run this on your Mac.")
    for patch in PATCHES:
        if not os.path.exists(patch):
            die("%s is missing; it should sit next to this script." % os.path.basename(patch))
    say("Nuvio: build from source -> TestFlight")
    check_xcode()
    java_home = find_java()
    android_home = find_android_sdk()

    release = tf.latest_release()
    tag = SOURCE_TAG

    class A(object):
        ipa = None
    official_ipa, _ = tf.get_ipa(A())  # official build: source of the server settings

    src = prepare_source(tag, official_ipa)
    ipa = build(src, java_home, android_home)
    verify_no_private_gcm(ipa)
    say("Built: " + ipa)

    if os.environ.get("NUVIO_BUILD_ONLY") == "1":
        say("")
        say("The app compiled and packaged correctly, but it was NOT uploaded: the App Store Connect")
        say("secrets were refused (see the 'Check the App Store Connect key' step). Fix the secret and")
        say("run the workflow again.")
        sys.exit(1)

    tf.step("Handing over to the TestFlight script")
    sys.exit(subprocess.call([sys.executable, os.path.join(HERE, "nuvio_testflight.py"), "--ipa", ipa]))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\nStopped.")
        sys.exit(130)
