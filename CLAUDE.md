# Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:

   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```

5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
- THE USER WANTS GUIDANCE ON THE SYNTAX, CORE LOGIC AND BEST PRACTICES, DO NOT IMPLEMENT ANY CODE UNLESS THE USER SPECIFICALLY ASKS FOR IT.

## Build & Test

```bash
uv sync
docker compose up -d postgres
uv run alembic upgrade head
AWS_PROFILE=sandbox-admin uv run uvicorn convfinqa.main:create_app --factory --reload
uv run pytest -q tests/
```

Full walkthrough (AWS login, env file, cURL verification, CLI REPL) lives in [docs/how-to-run-the-app.md](./docs/how-to-run-the-app.md).

## Architecture Overview

[Hexagonal](./docs/hexagonal.md)

## Testing locally

Run `aws-login` followed by `switch-aws-env sandbox-admin` before you are able
to test in AWS. Verify with `AWS_PROFILE=sandbox-admin aws sts get-caller-identity`
