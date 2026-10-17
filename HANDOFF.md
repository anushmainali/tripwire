# HANDOFF.md

> Keep this file short and current. Update after every commit. It is the only memory a restarted session has.

## NEEDS HUMAN
_(Things only the human can do: logins, keys, phone tests. Agents: add items here and keep working around them.)_
_(Human phone test done 2:15 PM Sat — no action needed from the human right now.)_

## HUMAN TEST RESULTS — Lead: fix these next (priority over other polish)
Live iMessage test 2:14–2:15 PM Sat, demo PostalPlus text sent from PHOTON_TEST_SENDER:
- ✅ Poller received the message; "Investigating" + verdict reply arrived on the phone. Core flow works.
- ❌ **Screenshot link opened a blank white page on the phone.** Log: `src.detonation.sandbox: no page.html from sandbox:
  SandboxFileSystemError`, then `attachment send failed (ApiError); falling back to link`.
  1. Debug the SandboxFileSystemError (files written/read from the wrong sandbox path? read before Playwright finished?).
  2. Make the capture robust: wait for load/networkidle (bounded), then **validate the PNG** (non-trivial byte size and
     not a single solid colour) before using it. If invalid, retry once; if still invalid, send NO link — describe the
     page in text instead ("The link opens a page asking for your card number").
  3. Check the hosted link on a phone-sized viewport: serve the PNG with `Content-Type: image/png` (and/or an HTML page
     with an `<img>`), confirm it renders. Add a test for the link path.
- ❌ **Image attachment send fails on the Photon shared line (ApiError)** even though upload works. Log the ApiError
  status/body (no secrets), re-check Photon beta docs for how to reference an uploaded attachment in sendMessage; if
  truly unsupported on shared lines, keep the hosted link as the primary path and say so in README.
- After fixing, add a new NEEDS HUMAN item asking for one more phone test.
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
- **Done (docs):** README (sponsor sections), DEMO.md (script + exact messages), SUBMISSION.md (results TBD from evals).
  85 s budget enforced; Droid skipped for chit-chat; Photon attachment upload verified live (multipart/related).
- **Done (hardening):** most-suspicious URL detonated; "still checking" msg after 35 s; per-sender rate limit (12/10 min);
  `why` lists Droid analyses + scripts; screenshot forwarding (Photon attachment → vision via gateway `/v1/messages`);
  live prompt-injection red team 8/8 (`python -m scripts.redteam` → docs/REDTEAM.md); wrapper-escape neutralized.
- **Done:** context re-check verified live (scam → suspicious with context note, no blind flip); offline e2e test of
  `run_live`; community intel memory (`src/investigator/intel.py`, data/intel.db, live only via `intel=True`).
- **Note for Evals:** after full-v1 started (94b43a4) Lead landed: Droid model default → claude-haiku-5-5 (faster),
  payment-ask fix (no FP on "paid you"), Hi-Mum pattern, context note. A later run would measure the current system.
- **Next 3 steps:**
  1. Optional: Chalk feature-engine mirror of intel (no feature deployment exists in env yet — risky).
  2. When evals full-v1 lands: merge, fill SUBMISSION.md Results + README numbers.
  3. Polish (warm sandbox?), then moonshot only if all green.
- **Known bugs:** Gateway rejects `temperature` on Anthropic chat route — don't pass it. Photon attachment send on
  shared line: upload verified, send untested until a phone test (falls back to hosted link).

## Status: Evals (Codex, `evals`)
- **Done:** Chalk gateway + baseline (`src/llm.py`); 120 frozen labeled cases (`evals/fixtures/`, 60 safe / 50 scam / 10 suspicious), provenance + licenses + metric policy in `evals/DATASET.md`; resumable bounded-process runner; remote Chalk task + eight SQL scorers; report/chart/raw CSV generators. 54 offline tests pass; ruff clean.
- **Real execution:** `evals/runs/dev-checks-v2`: 8 separate development cases, both systems 8/8, no errors. Chalk run `70688701-9271-407c-8e15-79f4ff336f64` SUCCEEDED, 16 rows, every remote score verified. `evals/RESULTS.md`, `results.csv`, `results_chart.png` clearly say DEVELOPMENT ONLY. One full benchmark run now in progress (limit 3). v1 retains diagnosed gateway temperature rejection; fixed in `abc3cb2`.
- **Done (workflow):** `982246d` adds `evals/README.md` and reports confirmed Droid success/script coverage separately from verdict accuracy. `4a04ca6` adds inert script-artifact capture + AST review hints (never executes scripts). All 8 Droid dev sessions successful; 4 cases wrote scripts, captured with no AST network/dynamic-execution flags. Remote Chalk run `8ac9bf90-1609-45f7-be00-c173d4a8e6aa` SUCCEEDED and verified (16 rows).
- **In progress:** Merged real sandbox/demo (`e7b8e14`). Evals detonation smoke on the controlled PostalPlus page succeeded (3.69 s, card field detected, screenshot). Preparing one 120-case full Droid comparison with concurrency 2 and exactly 3 sandbox cases (IDs frozen in DATASET.md), to satisfy full-system evaluation. Full-v1 started at commit `94b43a4`; **1 of 3 full-run slots used**. Resume exact command from README; do not merge/edit inference code until finished. This is deliberately full Droid on all cases rather than calling a checks-only ablation the full system.
- **Next 3 steps:**
  1. Full-v1 is running with workers=2 and three preselected sandbox IDs. Monitor and checkpoint; keep inference code unchanged.
  2. Checkpoint outputs, audit script artifacts and score saved predictions with Chalk.
  3. Review evidence and replace provisional report/chart with full-run results, retaining errors and unknown costs.
- **Integration notes for Lead:** Shared `src.llm.complete()` returns Completion or sanitized GatewayError; no temperature parameter (translated Chalk route rejects it). Investigator currently uses its own gateway. RDAP no-record path treats HTTP errors as successful yellow evidence; distinguish failures. **Dev evidence review:** dev-7 fake-check overpayment wrongly tagged rental and given rental advice; dev-5/dev-7 findings truncated mid-word; 3/10 evidence items add external/unobserved claims beyond checks. Full review in `evals/runs/dev-checks-v2/evidence_review.json` (6 supported / 3 partial / 1 unsupported; strict grounding, unblinded author review).
- **New dependencies for Lead to install:** `matplotlib==3.10.8` installed in shared venv, pinned in `evals/requirements.txt`; please add to root requirements if desired (outside Evals ownership).
- **Known bugs/limits:** Full Droid and detonation available; full benchmark pending. Complete investigator billing not exposed; cost is unknown, not zero. Historical public URL labels may be stale. Never fetch dataset URLs locally.
- **How to run:** `../HackHarvard/.venv/bin/python -m pytest tests evals -q`; `python -m evals.run --mode checks --out evals/runs/<new-dev-run>`; `python evals/chalk_score.py <run-dir>`; `MPLCONFIGDIR=/tmp/tripwire-matplotlib python -m evals.report <run-dir>`. Use shared venv Python for all commands. Full command after integration: `python -m evals.run --full-run --mode full --out evals/runs/full-v1`.

## How to run
- Activate: `source .venv/bin/activate`
- App (live iMessage): `.venv/bin/python -m src.main` · local REPL: `.venv/bin/python -m src.main --cli`
- Tests: `.venv/bin/python -m pytest -q` (runs tests/ and evals/, offline)
- Evals: _(fill in)_

## Decisions log
- Tripwire, Python, Fintech & Cybersecurity track; sponsors Factory + Chalk + Photon.
