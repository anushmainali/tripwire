# Agent instructions

Shared rules for every coding agent on this repo (Claude Code reads this via `CLAUDE.md`; Codex reads it directly). Several agents may be working at once, each in its own git worktree.

## Project

HackHarvard 2026 project using Factory Droid (`droid-sdk`), Photon (`photonhq-api`, iMessage) and Chalk (`chalkpy`, `chalkcompute`, Model Gateway). The app idea is still open; don't build features nobody asked for.

- `src/` — app code. `src/config.py` loads and validates `.env`; use it instead of reading `os.environ` directly.
- `smoke_tests/` — one standalone check per sponsor. Don't change them unless asked.
- `evals/`, `scripts/` — evaluations and helper scripts.
- `data/` — local data, gitignored.

## Commands

Always run from the worktree root with the project virtualenv:

```bash
.venv/bin/python -m src.main              # app entry point
.venv/bin/python -m src.config            # which settings are present (never values)
.venv/bin/python -m smoke_tests.<name>    # e.g. test_droid, test_chalk, test_chalk_gateway
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

Add new dependencies to `requirements.txt` (pinned) in the same change that needs them.

## Secrets

- Never print, log, commit or paste the values in `.env`. Refer to variables by name.
- `.env` is gitignored; new variables go in `.env.example` with an empty value.
- Don't create, rotate or revoke credentials unless the user asks.

## Working alongside other agents

- Stay inside the files or folders your task names. If you need to change something outside them (shared code, `requirements.txt`, `src/config.py`), keep the change small and say so in your summary.
- Commit to your own branch only. Never push to or rewrite `main`, and never force-push.
- Shared external resources — only one agent at a time may:
  - run a Photon listener (two listeners would both answer the same message),
  - deploy to Chalk or run Chalk evaluations against the shared environment,
  - bind a given local port (use the port your task gives you).
- Before finishing: ruff passes, the smoke tests you touched still pass, and your summary lists the files you changed.

## Code style

Python 3.11+, ruff (config in `pyproject.toml`), line length 120. Match the surrounding code; keep comments short and only where the code isn't obvious.
