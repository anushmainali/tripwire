# HANDOFF.md

> Keep this file short and current. Update after every commit. It is the only memory a restarted session has.

## NEEDS HUMAN
_(Things only the human can do: logins, keys, phone tests. Agents: add items here and keep working around them.)_

## Status: Lead (Claude Code, `main`)
- **Done:** —
- **In progress:** —
- **Next 3 steps:**
  1. Verify environment + smoke tests (Droid, Photon, Chalk). Fix setup if missing.
  2. Create `src/contracts.py` exactly per SPEC.md §3, commit, push.
  3. Create the evals worktree: `git worktree add ../hh-evals -b evals` (copy `.env` into it), push branch.
- **Known bugs:** —

## Status: Evals (Codex, `evals`)
- **Done:** `4a4ec4c`: bounded Chalk gateway client + `baseline_classify()`, detailed failure/token metadata; 15 offline tests pass. Gateway + Chalk auth smoke tests passed Oct 17 13:54 ET. Default cheap model `anthropic/claude-haiku-5-5` confirmed available.
- **In progress:** Reproducible labeled dataset and benchmark harness. Main investigator currently stub; no full benchmark spent yet.
- **Next 3 steps:**
  1. Build 100–150 labeled cases with source/license/rationale and synthetic markers; never equate spam with fraud automatically.
  2. Add resumable local baseline/investigator runner, metrics and report/chart generation.
  3. Upload predictions to Chalk Evaluations and run scorers; full comparison once real investigator lands.
- **New dependencies for Lead to install:** None.
- **Known bugs:** None in client. `complete(system, user, model=..., timeout=..., max_tokens=...)` returns Completion, raises sanitized GatewayError; baseline falls back conservatively. Tests in `evals/` to respect lane ownership.
- **How to run:** `../HackHarvard/.venv/bin/python -m pytest tests evals -q`; config via existing `.env`, never printed.

## How to run
- Activate: `source .venv/bin/activate`
- App: _(fill in)_
- Tests: `pytest -q`
- Evals: _(fill in)_

## Decisions log
- Tripwire, Python, Fintech & Cybersecurity track; sponsors Factory + Chalk + Photon.
