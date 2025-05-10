#!/usr/bin/env bash
# <!-- file: scripts/push_info.sh | purpose: Push docs/current_info_text.txt into the info_text DB table -->
set -euo pipefail

# Source file path
FILE="docs/current_info_text.txt"
if [ ! -f "$FILE" ]; then
  echo "Error: $FILE not found." >&2
  exit 1
fi

echo "Pushing info text from $FILE to backend..."

# Pipe SQL commands including the file content into psql via SSH
ssh sentrisbackendvm "sudo -u postgres psql sentris_db" <<EOF
BEGIN;
TRUNCATE game_data.info_text;
INSERT INTO game_data.info_text (text) VALUES (
\$info\$
$(cat "$FILE")
\$info\$
);
COMMIT;
EOF

echo "Restarting backend service..."
ssh sentrisbackendvm "sudo systemctl restart sentris-backend && sudo systemctl status sentris-backend --no-pager -n 5"

echo "Info text updated and backend restarted."