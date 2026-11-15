#!/usr/bin/env bash
# Fast check: (a) all fork patches apply in order to a clean upstream checkout,
# (b) unit tests for deep links and clipfinder run in the work tree.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TREE="${NUVIO_WORK:-$HERE/../../nuvio-work}"
LOG="$(mktemp)"
CLEAN=""
cleanup() { [ -n "$CLEAN" ] && git -C "$TREE" worktree remove --force "$CLEAN" >/dev/null 2>&1 || true; rm -f "$LOG"; }
trap cleanup EXIT
fail() { echo "FAIL: $1"; [ -s "$LOG" ] && tail -n 40 "$LOG"; exit 1; }

"$HERE/dev-tree.sh" >"$LOG" 2>&1 || fail "could not make the work tree"

# (a) clean checkout = the commit just before the baseline commit (upstream tag, no patches)
CLEAN="$(mktemp -d)/clean"
git -C "$TREE" worktree add -q --detach "$CLEAN" fork-baseline^ >"$LOG" 2>&1 || fail "could not check out upstream"
for p in nuvio-public-gcm nuvio-downloads nuvio-downloads-2 nuvio-share-resume; do
  git -C "$CLEAN" apply --whitespace=nowarn "$HERE/$p.patch" >"$LOG" 2>&1 || fail "$p.patch does not apply"
done

# (b) tests: Android host test task (the only JVM test target); -x filters keep it small
TESTS=(--tests 'com.nuvio.app.core.deeplink.*')
if [ -d "$TREE/composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder" ]; then
  TESTS+=(--tests 'com.nuvio.app.features.clipfinder.*')
fi
cd "$TREE"
[ -f local.properties ] || touch local.properties
if ! ./gradlew --console=plain --no-daemon :composeApp:testAndroidHostTest "${TESTS[@]}" >"$LOG" 2>&1; then
  grep -E "FAILED|^e: |Exception|What went wrong|Could not|^> " "$LOG" | head -n 40 || true
  echo "CHECK FAILED: patches apply, tests did not pass"
  exit 1
fi
echo "CHECK OK: 4 patches apply in order; tests passed (:composeApp:testAndroidHostTest)"
