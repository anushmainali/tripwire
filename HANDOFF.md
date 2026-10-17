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
- **Done:** —
- **In progress:** —
- **Next 3 steps:**
  1. Chalk Model Gateway client in `src/llm.py` + `baseline_classify()`.
  2. Dataset builders in `scripts/datasets/` → `data/eval_set.csv` (~150 labeled cases).
  3. Eval runner comparing baseline vs `investigate()` (stub until Lead's lands).
- **New dependencies for Lead to install:** —
- **Known bugs:** —

## How to run
- Activate: `source .venv/bin/activate`
- App: _(fill in)_
- Tests: `pytest -q`
- Evals: _(fill in)_

## Decisions log
- Tripwire, Python, Fintech & Cybersecurity track; sponsors Factory + Chalk + Photon.
