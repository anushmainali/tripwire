# HANDOFF.md

> Keep this file short and current. Update after every commit. It is the only memory a restarted session has.

## NEEDS HUMAN
_(Things only the human can do: logins, keys, phone tests. Agents: add items here and keep working around them.)_
- **Phone test**: start `.venv/bin/python -m src.main` (only ONE poller!) and text a scam message (see DEMO.md once written)
  to PHOTON_AGENT_HANDLE from PHOTON_TEST_SENDER. Photon's shared line only accepts messages from the assigned sender.
- Image attachments over iMessage are untested on the shared line; code tries upload+send and falls back to text.

## Status: Lead (Claude Code, `main`)
- **Done:** contracts.py; investigator (extract → link/RDAP/script/payment checks → evidence-only verdict via Chalk
  Model Gateway `anthropic/claude-sonnet-5-5`, deterministic floor/fallback); Photon poller + SQLite state + router
  (help / why / context follow-ups / new case); CLI REPL. Live poll verified; Droid + gateway smoke tests pass.
- **In progress:** Droid investigator step (`src/investigator/droid_agent.py`), registered in orchestrator `EXTRA_STEPS`.
- **Next 3 steps:**
  1. Droid step: per-case session in /tmp/tripwire-cases/<id>/, structured output → Evidence.
  2. Detonation: Chalk sandbox + Playwright → redirect chain, page facts, screenshot (`src/detonation/`).
  3. Demo scam landing page (fictional "PostalPlus") hosted somewhere harmless; DEMO.md; README sponsor sections.
- **Known bugs:** Gateway rejects `temperature` on Anthropic chat route — don't pass it.

## Status: Evals (Codex, `evals`)
- **Done:** Chalk gateway + baseline (`src/llm.py`); 120 frozen labeled cases (`evals/fixtures/`, 60 safe / 50 scam / 10 suspicious), provenance + licenses + metric policy in `evals/DATASET.md`; resumable bounded-process runner; remote Chalk task + eight SQL scorers; report/chart/raw CSV generators. 43 offline tests pass; ruff clean.
- **Real execution:** `evals/runs/dev-checks-v2`: 8 separate development cases, both systems 8/8, no errors. Chalk run `70688701-9271-407c-8e15-79f4ff336f64` SUCCEEDED, 16 rows, every remote score verified. `evals/RESULTS.md`, `results.csv`, `results_chart.png` clearly say DEVELOPMENT ONLY. Zero full benchmark runs used (limit 3). v1 retains diagnosed gateway temperature rejection; fixed in `abc3cb2`.
- **In progress:** Runner hardening and full Droid integration once Lead lands it. Current `--mode checks` explicitly excludes Droid/detonation; no benchmark claim.
- **Next 3 steps:**
  1. Resume hardening complete (`ec31b05`): pinned inputs, fsync, exclusive runner lock, duplicate/metadata checks, timeout/report tests; Chalk existing run re-read and reverified. Merge Droid now available on main.
  2. Merge real Droid pipeline, inspect sandbox safety, smoke the same dev cases. Full mode currently rejects missing Droid registration.
  3. Run frozen 120-case comparison once, score remotely, review evidence, replace provisional report/chart with real full-run results.
- **Integration notes for Lead:** Shared `src.llm.complete()` returns Completion or sanitized GatewayError; no temperature parameter (translated Chalk route rejects it). Investigator currently uses its own gateway. RDAP no-record path treats HTTP errors as successful yellow evidence; distinguish failures. **Dev evidence review:** dev-7 fake-check overpayment wrongly tagged rental and given rental advice; dev-5/dev-7 findings truncated mid-word; 3/10 evidence items add external/unobserved claims beyond checks. Full review in `evals/runs/dev-checks-v2/evidence_review.json` (6 supported / 3 partial / 1 unsupported; strict grounding, unblinded author review).
- **New dependencies for Lead to install:** `matplotlib==3.10.8` installed in shared venv, pinned in `evals/requirements.txt`; please add to root requirements if desired (outside Evals ownership).
- **Known bugs/limits:** Full pipeline not yet available in this checkout. Complete investigator billing not exposed; cost is unknown, not zero. Historical public URL labels may be stale. Never fetch dataset URLs locally.
- **How to run:** `../HackHarvard/.venv/bin/python -m pytest tests evals -q`; `python -m evals.run --mode checks --out evals/runs/<new-dev-run>`; `python evals/chalk_score.py <run-dir>`; `MPLCONFIGDIR=/tmp/tripwire-matplotlib python -m evals.report <run-dir>`. Use shared venv Python for all commands. Full command after integration: `python -m evals.run --full-run --mode full --out evals/runs/full-v1`.

## How to run
- Activate: `source .venv/bin/activate`
- App (live iMessage): `.venv/bin/python -m src.main` · local REPL: `.venv/bin/python -m src.main --cli`
- Tests: `.venv/bin/python -m pytest -q` (runs tests/ and evals/, offline)
- Evals: _(fill in)_

## Decisions log
- Tripwire, Python, Fintech & Cybersecurity track; sponsors Factory + Chalk + Photon.
