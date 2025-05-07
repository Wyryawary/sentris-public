#!/usr/bin/env bash
# file: scripts/shared/publish_public.sh | purpose: Publish only whitelisted files to the public 'public' repo without a persistent worktree.
set -euo pipefail

# Determine paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INCLUDE_FILE="$REPO_ROOT/public_includes.txt"
REMOTE="public"
BRANCH="public"
TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
MSG="chore: update public snapshot @ $TIMESTAMP"

# Pre-flight checks
if [[ ! -f "$INCLUDE_FILE" ]]; then
  echo "Error: include list not found at $INCLUDE_FILE" >&2
  exit 1
fi
cd "$REPO_ROOT"

if ! git remote get-url "$REMOTE" &>/dev/null; then
  echo "Error: Git remote '$REMOTE' not found." >&2
  exit 1
fi
# Get the public remote URL and derive a clone URL (fallback to HTTPS if SSH fails)
PUBLIC_URL=$(git remote get-url "$REMOTE")
if [[ "$PUBLIC_URL" =~ ^git@([^:]+):(.*)$ ]]; then
  CLONE_URL="https://${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
else
  CLONE_URL="$PUBLIC_URL"
fi

## Create a temporary directory for the public snapshot
TMP=$(mktemp -d)

echo "Cloning public repo into $TMP"
# If the public branch exists remotely, clone it; otherwise clone default and create orphan branch
if git ls-remote --exit-code --heads "$CLONE_URL" "$BRANCH" &>/dev/null; then
  git clone --origin public --branch "$BRANCH" --single-branch "$CLONE_URL" "$TMP"
else
  git clone --origin public "$CLONE_URL" "$TMP"
  pushd "$TMP" >/dev/null
  git checkout --orphan "$BRANCH"
  # Remove all files except .git directory
  find . -mindepth 1 -not -path './.git*' -delete
  popd >/dev/null
fi

# Clean target branch contents
pushd "$TMP" >/dev/null
git checkout "$BRANCH"
# Delete everything except .git
find . -mindepth 1 -not -path './.git*' -delete
popd >/dev/null

# Sync only the whitelisted files
echo "Syncing files from include list"
rsync -av --files-from="$INCLUDE_FILE" --relative "$REPO_ROOT"/ "$TMP"/

## Commit & push changes if any
pushd "$TMP" >/dev/null
# Configure a committer identity for this temporary clone
git config user.name "sentris-public-bot"
git config user.email "snapshot@ssentris.com"
# Ensure 'public' remote uses the SSH URL for push (PUBLIC_URL)
  # Determine a push URL: reuse origin's embedded HTTPS credentials if available
  ORIGIN_URL=$(git -C "$REPO_ROOT" remote get-url origin)
  if [[ "$ORIGIN_URL" == https://* ]]; then
    ORIGIN_DIR=$(dirname "$ORIGIN_URL")
    PUBLIC_PUSH_URL="$ORIGIN_DIR/sentris-public.git"
  else
    PUBLIC_PUSH_URL="$PUBLIC_URL"
  fi
git add -A
if ! git diff --cached --quiet; then
  git commit -m "$MSG"
  echo "Pushing to $PUBLIC_PUSH_URL"
  git push --force "$PUBLIC_PUSH_URL" "$BRANCH"
  echo "Public branch '$BRANCH' updated on remote '$REMOTE'."
else
  echo "No changes to publish."
fi
popd >/dev/null

# Cleanup
rm -rf "$TMP"
echo "Public snapshot published successfully."