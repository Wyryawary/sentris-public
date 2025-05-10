<!-- file: docs/CONTEXT/Shared/magic_words.md | purpose: Detailed magic-word triggers and actions -->
# Magic Word Triggers

Use messages starting with the prefix "magicWord:" (case-insensitive) to invoke scripts. After the prefix, specify one of the available commands below. The assistant will emit a `functions.shell` call for the matching command and return its output.


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

Invoke (optionally with a human-readable save name):
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/shared/ci_save.sh \"<save name>\""], "timeout": 120000 } }
```
## cloudLoad

Invoke (with the target save name):
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/shared/cloud_load.sh \"<save name>\""], "timeout": 120000 } }
```
This will reset your working tree to the named cloud save (tag) matching `<save name>`.


## publicSave

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/shared/publish_public.sh"], "timeout": 120000 } }
```


## runSentris

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/run_sentris.sh"], "timeout": 120000 } }
```
This will send the Flutter run commands to the tmux window named `snt` in the `sentris` session, so we can view logs there.


## restartBackend

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/restart_backend.sh"], "timeout": 120000 } }
```
This will send Ctrl+C to the `bnd` tmux window in the `sentris` session and issue a `sudo systemctl restart sentris-backend` on the VM.


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