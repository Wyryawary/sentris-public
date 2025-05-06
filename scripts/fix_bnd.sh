#!/usr/bin/env bash
# file: scripts/fix_bnd.sh | purpose: revive frozen 'bnd' tmux window by killing and recreating it
set -euo pipefail

# Determine current tmux session
SESSION=$(tmux display-message -p '#S' 2>/dev/null || true)
if [[ -z "$SESSION" ]]; then
  echo "Error: Not inside a tmux session. Please run this from within tmux." >&2
  exit 1
fi

echo "Reviving 'bnd' window in session '$SESSION'..."
# Use window name 'bnd' so we don't rely on numeric index
TARGET_WINDOW_NAME="bnd"
# If a 'bnd' window exists, respawn SSH there, otherwise create it
if tmux list-windows -t "$SESSION" -F '#{window_name}' | grep -qx "$TARGET_WINDOW_NAME"; then
  echo "Respawning SSH in existing '$TARGET_WINDOW_NAME' window..."
  tmux respawn-window -k -t "$SESSION:$TARGET_WINDOW_NAME" "ssh sentrisbackendvm"
else
  echo "Creating new window '$TARGET_WINDOW_NAME' and SSH..."
  tmux new-window -t "$SESSION" -n "$TARGET_WINDOW_NAME" "ssh sentrisbackendvm"
fi
# Prevent tmux from automatic renaming on SSH sessions
tmux set-window-option -t "$SESSION:$TARGET_WINDOW_NAME" automatic-rename off
# Switch to the 'bnd' window
tmux select-window -t "$SESSION:$TARGET_WINDOW_NAME"
echo "Window '$TARGET_WINDOW_NAME' is ready."