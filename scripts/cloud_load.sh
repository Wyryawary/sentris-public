#!/usr/bin/env bash
# <!-- file: scripts/shared/cloud_load.sh | purpose: load named cloud save | scope: ci -->

set -euo pipefail

# Require a save name argument
if [ $# -lt 1 ]; then
  echo "Usage: $0 <save name>"
  exit 1
fi

name=$1

# Slugify the save name for tag lookup
slug=$(echo "$name" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -e 's/[^a-z0-9 ]//g' -e 's/[[:space:]]\+/-/g' -e 's/[-]\+/-/g' -e 's/^-//;s/-$//')
tag="save/$slug"

# Fetch remote tags
git fetch --tags origin

# Verify the tag exists
if ! git rev-parse --verify --quiet "$tag"; then
  echo "Error: save \"$name\" (tag $tag) not found" >&2
  exit 1
fi

echo "Restoring repository to cloud save \"$name\" ($tag)"
git reset --hard "$tag"

# Record load in docs/saves.log
timestamp=$(date '+%Y-%m-%d @ %H:%M')
echo "$timestamp - ci_load: \"$name\"" >> docs/CONTEXT/saves.log

echo "Cloud load completed: HEAD is now at $tag"