#!/usr/bin/env bash
# scripts/publish_public.sh: Sync entire repo excluding sensitive files to the public branch.
set -euo pipefail

# Configuration
PUBLIC_WT="../public-worktree"
EXCLUDE_FILE="public_excludes.txt"
REMOTE="public"
BRANCH="public"

# Ensure remote exists
if ! git remote get-url "$REMOTE" &>/dev/null; then
  echo "Error: Git remote '$REMOTE' not found."
  exit 1
fi

# Update public worktree to latest remote state
pushd "$PUBLIC_WT" >/dev/null
git fetch "$REMOTE" "$BRANCH"
git reset --hard "$REMOTE/$BRANCH"
git clean -fdx
popd >/dev/null

# Sync files (excluding sensitive ones)
rsync -av --delete --exclude-from="$EXCLUDE_FILE" . "$PUBLIC_WT"/

# Commit & push if changes exist
pushd "$PUBLIC_WT" >/dev/null
git add -A
if ! git diff --cached --quiet; then
  git commit -m "chore: update public snapshot @ $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  git push "$REMOTE" "$BRANCH"
else
  echo "No changes to publish."
fi
popd >/dev/null