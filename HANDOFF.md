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
- **Recommended:** create Chalk service credentials (Dashboard → Settings → Access tokens) and put CHALK_CLIENT_ID /
  CHALK_CLIENT_SECRET in .env. Today sandboxes, feature queries and evals ride on the `chalk login` session; if it
  expires before the demo, run `chalk login` again (detonation fails soft → text verdict still works).
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
- **Evals lane status (seen by Lead 14:27):** Codex hit its usage limit until ~18:52; full-v1 paused at 10 rows (not
  running). If still stalled by ~21:00, Lead runs the documented resume command in ../hh-evals (evals/README.md).
- **Done (Chalk feature engine):** `chalk_features/` deployed via `chalk apply` (first deployment in env "production",
  project "Default"): `Domain` expression features + `@online` RDAP resolver. Domain-age check queries
  `domain.registered_days_ago` online (~150 ms), RDAP fallback. Redeploy: `cd chalk_features && chalk apply --force`
  (needs `.venv/bin` on PATH). No online store in env → no max_staleness/caching.
- **Done:** Droid OS sandbox per case (deny-all network except localhost MCP; verified live); Droid model
  claude-haiku-5-5 (~32 s); `scripts/run_tripwire.sh` supervisor; SUBMISSION.md refreshed.
- **Next 3 steps:**
  1. Wait for evals full-v1 (Codex resumes ~18:52); then merge, fill SUBMISSION.md/README numbers.
  2. When evals full-v1 lands: merge, fill SUBMISSION.md Results + README numbers.
  3. Polish (warm sandbox?), then moonshot only if all green.
- **Known bugs:** Gateway rejects `temperature` on Anthropic chat route — don't pass it. Photon attachment send on
  shared line: upload verified, send untested until a phone test (falls back to hosted link).

## Status: Evals (Codex, `evals`)
- **Done:** Chalk gateway + baseline (`src/llm.py`); 120 frozen labeled cases (`evals/fixtures/`, 60 safe / 50 scam / 10 suspicious), provenance + licenses + metric policy in `evals/DATASET.md`; resumable bounded-process runner; remote Chalk task + eight SQL scorers; report/chart/raw CSV generators. 79 offline tests pass; ruff clean.
- **Real execution:** `evals/runs/dev-checks-v2`: 8 separate development cases, both systems 8/8, no errors. Chalk run `70688701-9271-407c-8e15-79f4ff336f64` SUCCEEDED, 16 rows, every remote score verified. `evals/RESULTS.md`, `results.csv`, `results_chart.png` clearly say DEVELOPMENT ONLY. One full benchmark run now in progress (limit 3). v1 retains diagnosed gateway temperature rejection; fixed in `abc3cb2`.
- **Done (workflow):** `982246d` adds `evals/README.md` and reports confirmed Droid success/script coverage separately from verdict accuracy. `4a04ca6` adds inert script-artifact capture + AST review hints (never executes scripts). All 8 Droid dev sessions successful; 4 cases wrote scripts, captured with no AST network/dynamic-execution flags. Remote Chalk run `8ac9bf90-1609-45f7-be00-c173d4a8e6aa` SUCCEEDED and verified (16 rows).
- **In progress (16:45 ET restart):** synced main `10c7194`; 76 offline tests pass. Full-v1 stopped at 10/240 rows and is preserved as interrupted (slot 1). Its inference code is obsolete, so do not resume it against current main. Baseline's 16-token cap caused incomplete responses; raised to 128 before the next run, preserving strict one-label validation.
- **Checkpoint `9e4e1ec`:** full-v2 manifest, budget ledger and first predictions pushed; benchmark ongoing. Added report-only paired outcomes/Wilson intervals and successful-capture count; inference hash unchanged. First historical URL no longer resolves; screenshot path exists despite capture failure.
- **Checkpoint `8680248`:** gateway/auth smoke passed; current-system development smoke `dev-current-v2` completed 16/16 correct with no inference errors. Production fast path skips Droid on 5/8 cases; 3 sessions succeeded, no saved scripts. Report now explicitly discloses limited sandbox coverage.
- **Next 3 steps:**
  1. **full-v2 active**, started from `f754dc8` at 16:46 ET, workers=2, same three frozen sandbox IDs. Slot 2/3 consumed. Do not merge or edit inference code while active.
  2. Monitor/checkpoint full-v2; resume with README command using `full-v2` if interrupted. Evidence review selection is frozen in `full-v2/evidence_review_plan.json`.
  3. Audit evidence/script artifacts, score saved predictions in Chalk, publish full report/chart/CSV.
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
