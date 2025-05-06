<!-- file: repo_details.md | purpose: file-catalog -->

# Repo Details (v1)

## sentris_frontend/       <!-- Flutter web game -->
- lib/
  - main.dart              – app entry + overlay               (≈1800 loc)
  - config.dart            – API endpoints & design constants
  - game.dart              – gameplay loop & UI
  - menu.dart              – main menu UI
  - play.dart              – pre-game UI
  - over.dart              – post-game UI
  - sett.dart              – player settings UI
  - rank.dart              – top rankings UI (async fetch and themed display of global high scores)
  - high.dart              – highscore tables UI
  - info.dart              – game info, tutorials
  - logi.dart              – user login UI
  - acct.dart              – user account UI
- fonts/                   – custom typefaces declared in pubspec.yaml
- pubspec.yaml             – Flutter manifest (dependencies, assets, fonts)


## backend/                <!-- FastAPI -->
- main.py                  – FastAPI app + middleware         (≈150 loc)
- ai.py                    – GPT endpoints (get fresh sentence, first filler, fill block, final filler, fix sentence,
                             validate sentence, understand topics)
- db.py                    – asyncpg helpers + REST routes
- .env                     – environment variables for FastAPI (OPENAI_API_KEY, DB URL, DKIM key path)
- requirements.txt         – python dependencies

## senpire_frontend/       <!-- Admin companion -->
- lib/
  - main.dart              – PIN screen + dashboard stub
  - mana.dart              – admin UI
  - moni.dart              – monitoring UI
  - toke.dart              – token summary
- pubspec.yaml             – Flutter manifest (dependencies)


## scripts/
- ci_save.sh               – CI cloud save snapshot (stages, commits, pushes to remote, logs action)
- random_save.sh           – local save snapshot (stages, commits locally, logs pointer)
- random_load.sh           – local load (hard resets to last random snapshot)
- start_dev_tmux.sh        – launch tmux session for Codex CLI under WSL (Ubuntu 22.04.5 LTS)
- run_sentris.sh           – stars a test session in the 'snt' tmux window
 
## docs/CONTEXT/           <!-- Context documentation files -->
- current_goal.md           – Sprint goal: outlines current development objectives and milestones for Codex CLI integration.
- current_setup.md          – Environment reference: hardware and software setup for local development and VPS deployment.
- gameplay_mechanics.md     – Design outline: details gameplay mechanics (block limits, scoring, bonus-round logic).
- glossary.md               – Glossary: defines key project terms (e.g., block).
- magic_words.md            – Lists natural-language command triggers recognized by the Codex CLI.
- repo_details.md           – File catalog: this document describing repository structure and key files.
