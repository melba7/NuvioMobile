#!/usr/bin/env bash
# Work tree for Clip finder: upstream at fork/UPSTREAM_TAG + the older patches, committed as
# tag "fork-baseline". nuvio-share-resume.patch (if present) is applied on top, uncommitted.
#   fork/dev-tree.sh        make the work tree (skipped if it already exists)
#   fork/dev-tree.sh save   write the changes since the baseline to the last patch of PATCHES
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TREE="${NUVIO_WORK:-$HERE/../../nuvio-work}"
TAG="$(tr -d '[:space:]' < "$HERE/UPSTREAM_TAG")"
# The patch list lives in PATCHES in build_from_source.py (the last one is the Clip finder patch).
ALL_PATCHES=()
while IFS= read -r line; do ALL_PATCHES+=("$line"); done < <(python3 -B -c 'import os, sys; sys.path.insert(0, sys.argv[1]); import build_from_source as b; print("\n".join(os.path.basename(p)[:-len(".patch")] for p in b.PATCHES))' "$HERE")
[ "${#ALL_PATCHES[@]}" -ge 2 ] || { echo "could not read PATCHES from build_from_source.py" >&2; exit 1; }
OLD_PATCHES=("${ALL_PATCHES[@]:0:${#ALL_PATCHES[@]}-1}")
NEW_PATCH="$HERE/${ALL_PATCHES[${#ALL_PATCHES[@]}-1]}.patch"
git_t() { git -C "$TREE" -c user.name=fork -c user.email=fork@localhost "$@"; }

if [ "${1:-}" = "save" ]; then
  [ -d "$TREE/.git" ] || { echo "no work tree at $TREE; run fork/dev-tree.sh first" >&2; exit 1; }
  git_t add -A
  git_t diff --cached --binary --no-color fork-baseline > "$NEW_PATCH"
  git_t reset -q
  echo "saved $(wc -l < "$NEW_PATCH") lines to fork/nuvio-share-resume.patch"
  exit 0
fi

if [ -d "$TREE/.git" ] && [ "$(git_t describe --tags --exact-match fork-baseline 2>/dev/null || true)" = "fork-baseline" ] \
   && [ "$(git_t cat-file -t fork-baseline^{commit} 2>/dev/null)" = commit ] \
   && [ "$(git_t show -s --format=%s fork-baseline)" = "baseline: $TAG + patches" ]; then
  echo "work tree already at baseline for $TAG: $TREE"
  exit 0
fi
[ -e "$TREE" ] && { echo "$TREE exists but is not a $TAG baseline; move it away first" >&2; exit 1; }

# The folder did not exist before this point, so it is ours: if anything below fails, remove it
# so the next run starts clean instead of refusing a half-made tree.
undo_half_made() { [ "$?" -eq 0 ] || { rm -rf "$TREE"; echo "work tree failed half-way and was removed ($TREE); fix the error above and run fork/dev-tree.sh again" >&2; }; }
trap undo_half_made EXIT
git clone --depth 1 --branch "$TAG" https://github.com/NuvioMedia/NuvioMobile "$TREE"
for p in "${OLD_PATCHES[@]}"; do
  git -C "$TREE" apply --whitespace=nowarn "$HERE/$p.patch"
done
git_t add -A
git_t commit -q -m "baseline: $TAG + patches"
git_t tag fork-baseline
if [ -s "$NEW_PATCH" ]; then
  git -C "$TREE" apply --whitespace=nowarn "$NEW_PATCH"
fi
trap - EXIT
echo "work tree ready: $TREE"
