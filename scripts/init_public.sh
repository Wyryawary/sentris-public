#!/usr/bin/env bash
# scripts/init_public.sh - prepare and push initial public branch with only whitelisted files
set -euo pipefail

# Bootstrap SSH for push from any pane
eval "$(ssh-agent -s)" >/dev/null
ssh-add ~/.ssh/laptop.key >/dev/null 2>&1 || true

# Determine paths
SRC_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC_WT="$SRC_ROOT/../public-worktree"
INCLUDE_FILE="$SRC_ROOT/public_includes.txt"

# Pre-flight checks
if [[ ! -d "$PUBLIC_WT" ]]; then
  echo "Error: public worktree not found at $PUBLIC_WT" >&2
  exit 1
fi
if [[ ! -f "$INCLUDE_FILE" ]]; then
  echo "Error: include list not found at $INCLUDE_FILE" >&2
  exit 1
fi

echo "==> Recreating public branch as orphan in $PUBLIC_WT"
pushd "$PUBLIC_WT" >/dev/null
# Create a clean orphan branch to remove history
git checkout --orphan temp-public
git reset --hard
popd >/dev/null

echo "==> Cleaning public worktree at $PUBLIC_WT"
pushd "$PUBLIC_WT" >/dev/null
git rm -rf . || true
git clean -fdx
popd >/dev/null

echo "==> Syncing only files listed in public_includes.txt"
rsync -av --files-from="$INCLUDE_FILE" "$SRC_ROOT/" "$PUBLIC_WT"/

echo "==> Committing changes in public branch"
pushd "$PUBLIC_WT" >/dev/null
git add -A
# Commit only if there are staged changes
if ! git diff --cached --quiet; then
  git commit -m "chore: initial public snapshot"
else
  echo "No changes to commit in public branch"
fi

echo "==> Renaming orphan branch to 'public' and force-pushing"
pushd "$PUBLIC_WT" >/dev/null
git branch -M public
# Force push to overwrite existing public branch history
git push -f public public
popd >/dev/null
popd >/dev/null

echo "Public branch is now live with only whitelisted files."