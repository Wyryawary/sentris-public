<!-- file: docs/CONTEXT/magic_words.md | purpose: Detailed natural-language command triggers -->
# Natural-Language Command Triggers

The assistant recognizes the following exact user messages (case-insensitive) as "magic words" to run scripts. When triggered, it emits a `functions.shell` call and returns the command output.

## randomSave

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/random_save.sh"], "timeout": 120000 } }
```

## randomLoad

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/random_load.sh"], "timeout": 120000 } }
```

## cloudSave

Invoke:
```json
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/ci_save.sh"], "timeout": 120000 } }
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
{ "name": "functions.shell", "arguments": { "command": ["bash", "-lc", "./scripts/init_public.sh"], "timeout": 120000 } }
```