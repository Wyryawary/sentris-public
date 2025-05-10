#!/usr/bin/env bash
# <!-- file: scripts/random_save.sh | purpose: manual random save | scope: ci -->

set -euo pipefail

# Description message (default for randomSave trigger)
msg=${1:-"randomSave manual snapshot"}

# Stage all changes
git add -A

# Create an empty commit or record changes
git commit --allow-empty -m "$msg"

# Obtain the new commit hash and timestamp
commit_hash=$(git rev-parse HEAD)
timestamp=$(date --iso-8601=seconds)

# Record pointer for randomLoad
echo "$commit_hash" > .last_randomsave

# Record save in docs/saves.log
timestamp_human=$(date '+%Y-%m-%d @ %H:%M')
echo "$timestamp_human - rand_save" >> docs/CONTEXT/saves.log

echo "Random save completed: commit $commit_hash"