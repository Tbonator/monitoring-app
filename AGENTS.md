# AGENTS.md

Instructions for AI coding agents working in this repository.

[CLAUDE.md](CLAUDE.md) is the authoritative source for project scope, the approved technology stack, security rules and working rules. Read it before making changes.

Key rules (summary only):

- Use PowerShell-compatible commands. The development environment is Windows with Docker Desktop.
- Never run `docker compose down -v`, and never delete volumes or databases without approval.
- Never commit `.env` or secrets.
- Do not modify the Funeral Back Office application without review and approval.
- Validate every change with `scripts/validate.ps1`.
- Update `TASKS.md`, `CHANGELOG.md` and `docs/decisions.md` as work progresses.
