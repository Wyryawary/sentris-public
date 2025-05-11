#!/usr/bin/env bash
# <!-- file: scripts/random_load.sh | purpose: manual random load | scope: ci -->

set -euo pipefail

# Ensure a pointer file exists
if [ ! -f docs/.last_randomsave ]; then
  echo "Error: docs/.last_randomsave not found. Please run scripts/random_save.sh first." >&2
  exit 1
fi

# Read the snapshot commit hash
commit=$(cat docs/.last_randomsave)
echo "Restoring repository to random save commit $commit"

# Hard reset to that snapshot
git reset --hard "$commit"
# Record load in docs/saves.log
timestamp_human=$(date '+%Y-%m-%d @ %H:%M')
echo "$timestamp_human - rand_load" >> docs/CONTEXT/saves.log
echo "Random load completed: HEAD is now at $commit"