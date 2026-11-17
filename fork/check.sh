#!/usr/bin/env bash
# Fast check: (a) all fork patches apply in order to a clean upstream checkout,
# (b) unit tests for deep links and clipfinder run in the work tree.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TREE="${NUVIO_WORK:-$HERE/../../nuvio-work}"
LOG="$(mktemp)"
CLEAN=""
CLEAN_PARENT=""
cleanup() {
  [ -n "$CLEAN" ] && git -C "$TREE" worktree remove --force "$CLEAN" >/dev/null 2>&1 || true
  [ -n "$CLEAN_PARENT" ] && rm -rf "$CLEAN_PARENT"
  rm -f "$LOG"
}
trap cleanup EXIT
fail() { echo "FAIL: $1"; [ -s "$LOG" ] && tail -n 40 "$LOG"; exit 1; }

"$HERE/dev-tree.sh" >"$LOG" 2>&1 || fail "could not make the work tree"

# (a) clean checkout = the commit just before the baseline commit (upstream tag, no patches)
CLEAN_PARENT="$(mktemp -d)"
CLEAN="$CLEAN_PARENT/clean"
git -C "$TREE" worktree add -q --detach "$CLEAN" fork-baseline^ >"$LOG" 2>&1 || fail "could not check out upstream"
# the patch list lives in PATCHES in build_from_source.py
PATCH_NAMES=()
while IFS= read -r line; do PATCH_NAMES+=("$line"); done < <(python3 -B -c 'import os, sys; sys.path.insert(0, sys.argv[1]); import build_from_source as b; print("\n".join(os.path.basename(p) for p in b.PATCHES))' "$HERE")
[ "${#PATCH_NAMES[@]}" -ge 1 ] || fail "could not read PATCHES from build_from_source.py"
for p in "${PATCH_NAMES[@]}"; do
  git -C "$CLEAN" apply --whitespace=nowarn "$HERE/$p" >"$LOG" 2>&1 || fail "$p does not apply"
done

# The tests run on the work tree. Locally it may hold changes not yet saved to the patch:
# compare both trees (same files, same content) and warn if they differ.
if [ -z "${CI:-}" ]; then
  tree_id() { GIT_INDEX_FILE="$CLEAN_PARENT/idx-$2" git -C "$1" add -A >/dev/null 2>&1 && GIT_INDEX_FILE="$CLEAN_PARENT/idx-$2" git -C "$1" write-tree; }
  if [ "$(tree_id "$TREE" work)" != "$(tree_id "$CLEAN" saved)" ]; then
    echo "WARNING: the work tree has changes that are not saved yet; the tests below use them, but the saved patch lacks them. Run fork/dev-tree.sh save." >&2
  fi
fi

# (b) tests: Android host test task (the only JVM test target); -x filters keep it small
TESTS=(--tests 'com.nuvio.app.core.deeplink.*' --tests 'com.nuvio.app.features.downloads.core.*')
if [ -d "$TREE/composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder" ]; then
  TESTS+=(--tests 'com.nuvio.app.features.clipfinder.*')
fi
cd "$TREE"
[ -f local.properties ] || touch local.properties
if ! ./gradlew --console=plain --no-daemon :composeApp:testAndroidHostTest "${TESTS[@]}" >"$LOG" 2>&1; then
  grep -v "^> Task .*\(UP-TO-DATE\|NO-SOURCE\)$" "$LOG" | grep -E -A12 "FAILED|^e: |What went wrong" | head -n 60 || true
  python3 - "$TREE/composeApp/build/test-results" <<'PY' || true
import glob, sys
import xml.etree.ElementTree as ET
for f in glob.glob(sys.argv[1] + "/**/*.xml", recursive=True):
    for tc in ET.parse(f).getroot().iter("testcase"):
        for bad in list(tc.findall("failure")) + list(tc.findall("error")):
            print("FAILED %s.%s: %s" % (tc.get("classname"), tc.get("name"), (bad.get("message") or "")[:300]))
PY
  tail -n 15 "$LOG"
  echo "CHECK FAILED: patches apply, tests did not pass"
  exit 1
fi
echo "CHECK OK: ${#PATCH_NAMES[@]} patches apply in order; tests passed (:composeApp:testAndroidHostTest)"
