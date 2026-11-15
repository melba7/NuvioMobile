#!/usr/bin/env python3
"""Nightly check: has Nuvio published a newer iOS release than fork/UPSTREAM_TAG, and do our
patches still apply to it? Writes tag=, newer=, applies= and log= to $GITHUB_OUTPUT."""

import os
import subprocess
import sys
import tempfile
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nuvio_testflight as tf  # noqa: E402
import build_from_source as bfs  # noqa: E402


def out(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    line = "%s<<__EOF__\n%s\n__EOF__\n" % (key, value)
    if path:
        with open(path, "a") as f:
            f.write(line)
    print(line, end="")


def main():
    forced = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else ""
    release = tf.latest_release()
    tag = forced or urllib.parse.urlparse(release["downloadURL"]).path.split("/")[-2]
    current = bfs.SOURCE_TAG
    out("tag", tag)
    out("current", current)
    out("newer", "true" if tag != current else "false")
    if tag == current:
        out("applies", "true")
        out("log", "")
        return
    work = tempfile.mkdtemp(prefix="nuvio-upstream-")
    src = os.path.join(work, "src")
    p = subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", tag, bfs.REPO, src],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        out("applies", "false")
        out("log", "couldn't clone %s:\n%s" % (tag, p.stdout.decode(errors="replace")[-3000:]))
        return
    log = []
    for patch in bfs.PATCHES:
        p = subprocess.run(["git", "-C", src, "apply", "--whitespace=nowarn", patch],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if p.returncode != 0:
            log.append("%s does not apply to %s:\n%s" % (os.path.basename(patch), tag,
                                                          p.stdout.decode(errors="replace")[-3000:]))
            break
    if not log:
        p = subprocess.run(["grep", "-rln", "CCCryptorGCMEncrypt(\\|CCCryptorGCMDecrypt(\\|CCCryptorGCMFinal(",
                            "--include=*.kt", "--include=*.h", "--include=*.def", src],
                           stdout=subprocess.PIPE)
        hits = [h for h in p.stdout.decode().split() if not h.endswith("PluginAesGcm.kt")]
        if hits:
            log.append("%s calls Apple's private AES-GCM functions in new places:\n%s" % (tag, "\n".join(hits)))
    out("applies", "false" if log else "true")
    out("log", "\n\n".join(log))


if __name__ == "__main__":
    main()
