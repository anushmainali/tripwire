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
- **Done:** Chalk gateway + baseline (`src/llm.py`); 120 frozen labeled cases (`evals/fixtures/`, 60 safe / 50 scam / 10 suspicious), provenance + licenses + metric policy in `evals/DATASET.md`; resumable bounded-process runner; remote Chalk task + eight SQL scorers; report/chart/raw CSV generators. 35 offline tests pass; ruff clean.
- **Real execution:** `evals/runs/dev-checks-v2`: 8 separate development cases, both systems 8/8, no errors. Chalk run `70688701-9271-407c-8e15-79f4ff336f64` SUCCEEDED, 16 rows, every remote score verified. `evals/RESULTS.md`, `results.csv`, `results_chart.png` clearly say DEVELOPMENT ONLY. Zero full benchmark runs used (limit 3). v1 retains diagnosed gateway temperature rejection; fixed in `abc3cb2`.
- **In progress:** Runner hardening and full Droid integration once Lead lands it. Current `--mode checks` explicitly excludes Droid/detonation; no benchmark claim.
- **Next 3 steps:**
  1. Make Chalk upload/resume and local inputs reproducible; test timeout/report validation.
  2. Merge real Droid pipeline, inspect sandbox safety, smoke the same dev cases. Full mode currently rejects missing Droid registration.
  3. Run frozen 120-case comparison once, score remotely, review evidence, replace provisional report/chart with real full-run results.
- **Integration notes for Lead:** Shared `src.llm.complete()` returns Completion or sanitized GatewayError; no temperature parameter (translated Chalk route rejects it). Investigator currently uses its own gateway. RDAP no-record path treats HTTP errors as successful yellow evidence; distinguish failures. **Dev evidence review:** dev-7 fake-check overpayment wrongly tagged rental and given rental advice; dev-5/dev-7 findings truncated mid-word; 3/10 evidence items add external/unobserved claims beyond checks. Full review in `evals/runs/dev-checks-v2/evidence_review.json` (6 supported / 3 partial / 1 unsupported; strict grounding, unblinded author review).
- **New dependencies for Lead to install:** `matplotlib==3.10.8` installed in shared venv, pinned in `evals/requirements.txt`; please add to root requirements if desired (outside Evals ownership).
- **Known bugs/limits:** Full pipeline not yet available in this checkout. Complete investigator billing not exposed; cost is unknown, not zero. Historical public URL labels may be stale. Never fetch dataset URLs locally.
- **How to run:** `../HackHarvard/.venv/bin/python -m pytest tests evals -q`; `python -m evals.run --mode checks --out evals/runs/<new-dev-run>`; `python evals/chalk_score.py <run-dir>`; `MPLCONFIGDIR=/tmp/tripwire-matplotlib python -m evals.report <run-dir>`. Use shared venv Python for all commands. Full command after integration: `python -m evals.run --full-run --mode full --out evals/runs/full-v1`.

## How to run
- Activate: `source .venv/bin/activate`
- App: _(fill in)_
- Tests: `pytest -q`
- Evals: _(fill in)_

## Decisions log
- Tripwire, Python, Fintech & Cybersecurity track; sponsors Factory + Chalk + Photon.
