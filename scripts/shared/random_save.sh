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

# Record pointer and log entry
echo "$commit_hash" > .last_randomsave
echo "$timestamp  👉 codex_actions.log: randomSave snapshot - \"$msg\"" >> codex_actions.log

echo "Random save completed: commit $commit_hash"