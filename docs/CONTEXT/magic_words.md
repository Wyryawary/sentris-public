<!-- file: docs/CONTEXT/magic_words.md | purpose: Detailed natural-language command triggers -->
# Natural-Language Command Triggers

The assistant recognizes the following exact user messages (case-insensitive) as "magic words" to run scripts. When triggered, it emits a `functions.shell` call and returns the command output.

## randomSave

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/shared/random_save.sh"], "timeout": 120000 } }
```

## randomLoad

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/shared/random_load.sh"], "timeout": 120000 } }
```

## cloudSave

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/shared/ci_save.sh"], "timeout": 120000 } }
```
  
## runSentris

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/run_sentris.sh"], "timeout": 120000 } }
```
**Note:** This will send the Flutter run commands to the tmux window named `snt` in the `sentris` session, so you can view logs there.


## publicSave

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/shared/publish_public.sh"], "timeout": 120000 } }
```

## restartBackend

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/restart_backend.sh"], "timeout": 120000 } }
```
**Note:** This will send Ctrl+C to the `bnd` tmux window in the `sentris` session and issue a `sudo systemctl restart sentris-backend` on the VM.
  
## purgeUser

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/purge_user.sh"], "timeout": 120000 } }
```
This script will prompt for an email address and then purge that user and all related data on the backend VM.
   
## pushInfo

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/push_info.sh"], "timeout": 120000 } }
```
This reads `docs/current_info_text.txt` and replaces the contents of `game_data.info_text` on the backend VM, then restarts the service.