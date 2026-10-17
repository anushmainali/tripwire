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
- App (live iMessage): `.venv/bin/python -m src.main` · local REPL: `.venv/bin/python -m src.main --cli`
- Tests: `.venv/bin/python -m pytest -q` (runs tests/ and evals/, offline)
- Evals: _(fill in)_

## Decisions log
- Tripwire, Python, Fintech & Cybersecurity track; sponsors Factory + Chalk + Photon.
