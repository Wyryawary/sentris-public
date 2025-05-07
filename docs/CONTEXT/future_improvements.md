<!-- file: docs/CONTEXT/future_improvements.md | purpose: Document long-term environment and secret management improvements -->

# Future Improvements for Environment & Secret Management

Below are production-grade approaches for managing environment variables and secrets, beyond using a `.env` file:

## 1. Export Variables in Shell Profile
- Add `export VAR=VALUE` lines in `~/.profile`, `~/.bashrc`, or `/etc/profile.d/` scripts.
- Pros: no separate secret file; variables loaded on login or shell start.
- Cons: less portable; requires editing user or system profiles and reloading sessions.

## 2. Define Environment in systemd Service Unit
- Create a service file at `/etc/systemd/system/sentris-backend.service` with `Environment=` entries.
- Example:
  ```
  [Service]
  Environment="DATABASE_URL=..."
  Environment="DKIM_PRIVATE_KEY_PATH=/home/ubuntu/sentris-monorepo/backend/dkim_private.pem"
  ```
- Pros: secrets managed by systemd; easy restarts, logs, and security.
- Cons: requires writing and maintaining system service definitions.

## 3. Use a Centralized Secrets Manager
- Integrate with AWS Secrets Manager, HashiCorp Vault, or similar.
- Pros: centralized, auditable, and encrypted secret storage; rotation policies.
- Cons: additional infrastructure and complexity.

Use one of these methods to remove the `.env` file in a future, more secure deployment.