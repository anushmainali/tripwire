# HANDOFF.md

> Keep this file short and current. Update after every commit. It is the only memory a restarted session has.

## NEEDS HUMAN
_(Things only the human can do: logins, keys, phone tests. Agents: add items here and keep working around them.)_
- **Phone test**: start `.venv/bin/python -m src.main` (only ONE poller!) and text a scam message (see DEMO.md once written)
  to PHOTON_AGENT_HANDLE from PHOTON_TEST_SENDER. Photon's shared line only accepts messages from the assigned sender.
- Image attachments over iMessage are untested on the shared line; code tries upload+send and falls back to a hosted link.
- Demo site redeploy if needed: `.venv/bin/python -m demo_site.deploy` (Chalk ScalingGroup, ~1 replica, tiny cost).

## Status: Lead (Claude Code, `main`)
- **Done:** contracts; investigator (extract → link/RDAP/script/payment checks → **Droid** step → **Chalk sandbox
  detonation** → evidence-only verdict via Chalk Model Gateway `anthropic/claude-sonnet-5-5`, deterministic
  floor/fallback); Photon poller + SQLite state + router (help / why / context / new case); screenshot as iMessage
  attachment w/ hosted-link fallback; demo site on Chalk ScalingGroup `tripwire-demo` (fictional PostalPlus trap at
  `<url>/track`, URL in `data/demo_site_url.txt`). Full live run on demo text: scam/high, ~54 s.
- **For Evals lane:** `investigate(msg)` = full pipeline (Droid ~50 s + sandbox, costs quota).
  `from src.investigator.orchestrator import investigate; investigate(msg, steps=())` = checks + LLM verdict only
  (~3 s); `steps=("detonation",)` adds the sandbox only. Suggest: full pipeline on ≤ 40 cases, checks+LLM on all.
- **Next 3 steps:**
  1. README (sponsor sections), DEMO.md, SUBMISSION.md drafts.
  2. Robustness: 90 s hard cap with progress message, prompt-injection tests, image-only messages, rate limits.
  3. Warm sandbox to cut detonation latency; "why" shows Droid analyses.
- **Known bugs:** Gateway rejects `temperature` on Anthropic chat route — don't pass it. Photon attachment send on
  shared line untested (falls back to hosted link).

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
