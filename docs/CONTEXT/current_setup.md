<!-- file: current_setup.md  | purpose: env‑reference -->

# Hardware & Software
* **Local dev:** Win 11 laptop, WSL 2 (Ubuntu 22.04.5 LTS) terminal using tmux sessions for Codex CLI integration, VS Code.
* **VPS:** Win Server 2022; IIS hosts `ssentris.com` & `api.ssentris.com` (SSL on :3001; other unrelated public URL are hosted from this VPS).
* **VM:** Linux based; Freshly created, have to set up backend (Fast API and Database) here.
* **Database:** Postgres managed via pgAdmin 4 migrating to psql.
* **Mail:** Self‑hosted MailEnable + DKIM.
* **Paths:** see repo layout in `repo_details.md`.
