#!/usr/bin/env python3
"""Fails in seconds, before the hour-long build, if the App Store Connect secrets are wrong.
Prints which one looks wrong without printing any secret value."""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nuvio_testflight as tf  # noqa: E402


def main():
    kid = os.environ.get("ASC_KEY_ID", "")
    iss = os.environ.get("ASC_ISSUER_ID", "")
    p8 = os.environ.get("ASC_KEY_P8", "")
    problems = []
    if not re.fullmatch(r"[A-Z0-9]{10}", kid.strip()):
        problems.append("ASC_KEY_ID should be exactly 10 letters/digits (like 2X9R4HXF34). Yours has %d characters%s."
                        % (len(kid.strip()), " and contains spaces, quotes or lower-case letters"
                           if re.search(r"[^A-Z0-9]", kid.strip()) else ""))
    if not re.fullmatch(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", iss.strip()):
        problems.append("ASC_ISSUER_ID should look like 69a6de7f-1234-47e3-e053-5b8c7c11a4d1 (36 characters, no "
                        "quotes). Yours has %d characters%s." % (len(iss.strip()), " and starts or ends with a quote"
                                                                  if iss.strip()[:1] in "\"'" or iss.strip()[-1:] in "\"'" else ""))
    if "BEGIN PRIVATE KEY" not in p8 or "END PRIVATE KEY" not in p8:
        problems.append("ASC_KEY_P8 should be the whole text of the AuthKey_XXXXXXXXXX.p8 file, starting with "
                        "-----BEGIN PRIVATE KEY----- and ending with -----END PRIVATE KEY-----. Yours has %d "
                        "characters and %s." % (len(p8), "is missing those lines"))
    if problems:
        for p in problems:
            print("::error title=App Store Connect secret looks wrong::" + p)
        sys.exit(1)
    cfg = tf.load_config(type("A", (), {"bundle_id": None})())
    asc = tf.Asc(cfg)
    try:
        asc.get("/v1/apps", limit="1")
    except tf.ApiError as e:
        if e.status == 401:
            print("::error title=Apple rejected the API key (401)::The three secrets have the right shape but do not "
                  "belong together. Usual causes: ASC_KEY_ID is not the ID of the key whose .p8 file is in ASC_KEY_P8 "
                  "(the ID is in the file name AuthKey_<ID>.p8), ASC_ISSUER_ID was mistyped, or the key was revoked "
                  "in App Store Connect (Users and Access, Integrations).")
            sys.exit(1)
        if e.status == 403:
            print("::error title=API key lacks access (403)::The key works but is not allowed to do this. It needs "
                  "the Admin role, and any new Apple agreement must be accepted at developer.apple.com/account.")
            sys.exit(1)
        raise
    print("App Store Connect key accepted.")


if __name__ == "__main__":
    main()
