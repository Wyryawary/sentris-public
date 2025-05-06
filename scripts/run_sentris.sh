#!/usr/bin/env bash
# file: scripts/run_sentris.sh | purpose: run Sentris Flutter frontend | scope: ci | updated: 2025-04-29

set -euo pipefail

# Session name (must match start_dev_tmux.sh)
SESSION="sentris"

# Paths
PROJECT_ROOT="$PWD"
FRONTEND_DIR="$PROJECT_ROOT/sentris_frontend"

# Ensure tmux session exists
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Error: tmux session '$SESSION' not found. Start it with scripts/start_dev_tmux.sh"
  exit 1
fi

# Create or reuse window 2 (snt)
if ! tmux list-windows -t "$SESSION" | grep -q '^2:'; then
  tmux new-window -t "$SESSION" -n snt
fi

# Send flutter run command to snt window
tmux send-keys -t "$SESSION:snt" "cd \"$FRONTEND_DIR\" && clear; echo 'Sentris Frontend (snt) ➤'; flutter run -d chrome" C-m

# Switch focus to snt window
tmux select-window -t "$SESSION:snt"
