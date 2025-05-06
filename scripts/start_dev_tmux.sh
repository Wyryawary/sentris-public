#!/usr/bin/env bash
# file: scripts/start_dev_tmux.sh | purpose: tmux dev session | scope: ci | updated: 2025-04-26
set -euo pipefail
# Session name
SESSION="sentris"

# If session exists, attach and exit
tmux has-session -t $SESSION &>/dev/null && { tmux attach -t $SESSION; exit; }

# Load AI key from backend/.env for new sessions
ENV_FILE="$PWD/backend/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: $ENV_FILE not found. Please create it with OPENAI_API_KEY=sk-..."
  exit 1
fi
set -o allexport
# shellcheck disable=SC1091
source "$ENV_FILE"
set +o allexport
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Error: OPENAI_API_KEY not set in $ENV_FILE"
  exit 1
fi

# Window 0: tmp (general-purpose terminal)
tmux new-session -d -s $SESSION -n tmp
tmux send-keys    -t $SESSION:tmp "cd $PWD && clear" C-m
tmux set-window-option -t $SESSION:tmp automatic-rename off

# Window 1: cdx (Codex CLI)
tmux new-window   -t $SESSION -n cdx
tmux send-keys    -t $SESSION:cdx "cd $PWD && clear; export OPENAI_API_KEY='${OPENAI_API_KEY}'; echo 'Codex CLI ➤'; codex" C-m
tmux set-window-option -t $SESSION:cdx automatic-rename off

# Window 2: cmd (command shell in repo root)
tmux new-window   -t $SESSION -n cmd
tmux send-keys    -t $SESSION:cmd "cd $PWD && clear" C-m
tmux set-window-option -t $SESSION:cmd automatic-rename off

# Window 3: snt (sentris_frontend)
tmux new-window   -t $SESSION -n snt
tmux send-keys    -t $SESSION:snt "cd $PWD/sentris_frontend && clear; echo 'Sentris Frontend (snt) ➤'; flutter pub get" C-m
tmux set-window-option -t $SESSION:snt automatic-rename off

# Window 4: bnd (backend VM)
tmux new-window   -t $SESSION -n bnd
tmux send-keys    -t $SESSION:bnd "ssh sentrisbackendvm" C-m
# Prevent tmux from renaming the bnd window based on SSH remote title
tmux set-window-option -t $SESSION:bnd automatic-rename off

# Window 5: enp (senpire_frontend)
tmux new-window   -t $SESSION -n enp
tmux send-keys    -t $SESSION:enp "cd $PWD/senpire_frontend && clear; echo 'Senpire Frontend (enp) ➤'" C-m
tmux set-window-option -t $SESSION:enp automatic-rename off

# Start in tmp window
tmux select-window -t $SESSION:tmp

# Attach session
tmux attach -t $SESSION
