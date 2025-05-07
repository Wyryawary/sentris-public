#!/usr/bin/env bash
# <!-- file: scripts/ci_save.sh | purpose: CI cloud save snapshot | scope: ci -->

set -euo pipefail

# Description message (default for cloudSave trigger)
msg=${1:-"ci: cloud save snapshot"}

# Stage all changes
git add -A

# Commit code changes (allow empty commits)
git commit --allow-empty -m "$msg"

# Push commits to remote with force to ensure override of origin/main
git push --force

# Append entry to local codex actions log
timestamp=$(date --iso-8601=seconds)
echo "$timestamp  👉 codex_actions.log: ci_save snapshot - \"$msg\"" >> codex_actions.log

echo "CI save completed: commit $(git rev-parse HEAD)"