#!/usr/bin/env bash
# <!-- file: scripts/ci_save.sh | purpose: CI cloud save snapshot | scope: ci -->

set -euo pipefail

# Save name (optional): a human-readable label for this cloud save
name=${1:-}

# Commit message: include name if provided, else default snapshot
if [ -n "$name" ]; then
  msg="ci_save snapshot: $name"
else
  msg="ci_save snapshot"
fi

# If a save name is provided, prepare slug and backup information
if [ -n "$name" ]; then
  slug=$(echo "$name" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -e 's/[^a-z0-9 ]//g' -e 's/[[:space:]]\+/-/g' -e 's/[-]\+/-/g' -e 's/^-//;s/-$//')
  old_head=$(git rev-parse HEAD)
  backup_timestamp=$(date '+%Y%m%d_%H%M%S')
  backup_tag="${backup_timestamp}_${slug}"
  git tag "$backup_tag" "$old_head"
  git push origin "$backup_tag"
fi

# Stage all changes
git add -A

# Create a new root commit (no parent) capturing this state
tree=$(git write-tree)
new_head=$(git commit-tree $tree -m "$msg")

# Update the current branch to point to the new root commit
default_branch=$(git rev-parse --abbrev-ref HEAD)
git update-ref refs/heads/"$default_branch" "$new_head"

# Force-push the rewritten branch
git push origin "$default_branch" --force

# Create or update the persistent save tag if a name was provided
if [ -n "$name" ]; then
  save_tag="save/$slug"
  git tag -f "$save_tag" "$new_head"
  git push origin "$save_tag" --force
fi

# Record save in docs/CONTEXT/saves.log
timestamp=$(date '+%Y-%m-%d @ %H:%M')
echo "$timestamp - ci_save: \"$name\"" >> docs/CONTEXT/saves.log

echo "CI save completed: commit $(git rev-parse HEAD)"
