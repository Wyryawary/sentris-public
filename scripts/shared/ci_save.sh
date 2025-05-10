#!/usr/bin/env bash
# <!-- file: scripts/ci_save.sh | purpose: CI cloud save snapshot | scope: ci -->

set -euo pipefail

# Description message (default for cloudSave trigger)
# Save name (optional): a human-readable label for this cloud save
name=${1:-}
# Commit message: include name if provided, else default snapshot
if [ -n "$name" ]; then
  msg="ci_save snapshot: $name"
else
  msg="ci_save snapshot"
fi

# Stage all changes
git add -A

# Commit code changes (allow empty commits)
git commit --allow-empty -m "$msg"

# Push commits to remote with force to ensure override of origin/main
git push --force

# Create (or update) a tag for this save if a name was provided
if [ -n "$name" ]; then
  # slugify the name to form a safe tag
  slug=$(echo "$name" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -e 's/[^a-z0-9 ]//g' -e 's/[[:space:]]\+/-/g' -e 's/[-]\+/-/g' -e 's/^-//;s/-$//')
  tag="save/$slug"
  git tag -f "$tag"
  git push origin "$tag" --force
fi
# Record save in docs/saves.log
timestamp=$(date '+%Y-%m-%d @ %H:%M')
echo "$timestamp - ci_save: \"$name\"" >> docs/CONTEXT/saves.log

echo "CI save completed: commit $(git rev-parse HEAD)"