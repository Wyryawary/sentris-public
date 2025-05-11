# Sentris Public Snapshot

Open-Source-safe subset of the Sentris (ssentris.com) repo. 


## Contents

* `.codex.md`  
  Workflows and tmux/Codex CLI integration guide. Understand and enter the creator-realm by reading this file.

* `docs/CONTEXT/magic_words.md`  
  Magic Word trigger definitions. Works like magic... For lazy people who do not care how things are done.
  
  Example uses:
  - magicWord: pushInfo
  - magicWord: cloudSave "stay-safe"

* `scripts/`  
  Scripts triggered by magic words:  
  - `ci_save.sh`: save codebase to CI/cloud (cloudSave)  
  - `cloud_load.sh`: restore codebase from CI/cloud (cloudLoad)  
  - `random_save.sh`: save a local snapshot (randomSave)  
  - `random_load.sh`: load a local snapshot (randomLoad)  
  - `publish_public.sh`: publish this curated public snapshot (publicSave)  
  - `push_info.sh`: update backend info text (pushInfo)

* `sentris_frontend/lib/info.dart`  
  Public-facing game information displayed when LEARN is selected from the Main Menu. The pushInfo magic word is updating the database with new content defined in the `current_info_text.txt` file. Edit file >> Say the Magic Word >> Done.

* `docs/current_info_text.txt`
  The actual content pushed to the database.

* `backend/ai.py`  
  FastAPI AI endpoints implementation using Python.


## Purpose
This repository demonstrates how the Sentris project:

1. Leverages **Codex CLI** to automate common development workflows.
2. Integrates with **OpenAI** models via a FastAPI backend.