# HANDOFF.md

> Keep this file short and current. Update after every commit. It is the only memory a restarted session has.

## NEEDS HUMAN
_(Things only the human can do: logins, keys, phone tests. Agents: add items here and keep working around them.)_
- **Phone re-test requested (screenshot fix, 5 PM Sat):** text the PostalPlus demo message again; the screenshot link/attachment should now show the card form (not blank). Check `tmux`/log for `attachment send failed (... status= body=)` and tell Lead.

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
  1. **DONE 5 PM (awaiting phone re-test): blank-screenshot fix (PNG/JPEG validity check + one retry + no blank link; ApiError body now logged)**; orig note: fix the blank-screenshot bug in "HUMAN TEST RESULTS" at the top of this file**
     (SandboxFileSystemError, validate PNG before sending, hosted link must render on a phone, no blank links).
     The screenshot is the demo's "wow" moment. Then add a NEEDS HUMAN item asking for one phone re-test.
  2. When evals full-v1 lands (Codex resumes ~18:52): merge, fill SUBMISSION.md Results + README numbers.
  3. Polish (warm sandbox?), then moonshot only if all green.
- **Known bugs:** Gateway rejects `temperature` on Anthropic chat route — don't pass it. Photon attachment send on
  shared line: upload verified, send untested until a phone test (falls back to hosted link).

## Status: Evals (Codex, `evals`)
- **Done:** gateway + strict single-call baseline; frozen 120 cases (60 safe / 50 scam / 10 suspicious), provenance/licenses; bounded resumable runner; Chalk replay task + eight remote SQL scorers; report/chart/CSV with paired outcomes, uncertainty and explicit sandbox coverage. **85 offline tests pass**, ruff clean.
- **Active:** `evals/runs/full-v2`, started 16:46 ET from `f754dc8`, workers=2, sandbox IDs `url-69188`, `url-154131`, `synthetic-039`. **Slot 2 of 3 used**. Do not merge or edit inference code while running. Resume exact README command if interrupted; code hash is pinned. Full-v1 stopped at 10/240 predictions and remains preserved (slot 1); do not resume it against current code.
- **Latest checkpoint:** `1c866b0` adds offline screenshot audit and runtime model/package identifiers. Full-v2 continues beyond 106/240 rows. Report now lists exact failure types and recorded model identifiers. All three sandbox cases finished: DNS blank, Cuttly 404, FedEx access-denied (HTTP 200); no live phishing form captured. Baseline has several incomplete responses even with 128-token cap; retain them as failures. Separate reserved-domain dev diagnostic returns a normal stop/6-token label. New tests cover rejecting incomplete labels and sanitizing provider errors; no inference-code changes.
- **Evidence review done:** deterministic first case per source/label stratum (7 cases), all 32 claims: 21 fully grounded, 10 partial, 1 unsupported. Saved `evidence_review.json`. Issues for Lead: unsupported .ru cheap/common assertion; invented lack-of-prize-entry context; unverified external claims; static HTML checks overstated.
- **Screenshot issue for Lead:** `url-154131` DNS failure still returned a uniform blank image. `url-69188` returned a real 404 page, not live phishing. Saved images + `screenshot_audit.json` preserve reproduction. Do not equate paths with successful captures.
- **Development:** `dev-current-v2` both systems 8/8, no errors, 3 successful Droid sessions (5 production fast-path skips), no saved scripts. Prior verified remote runs: checks `70688701-9271-407c-8e15-79f4ff336f64`; Droid `8ac9bf90-1609-45f7-be00-c173d4a8e6aa`. Public report still DEVELOPMENT ONLY until full-v2 finishes.
- **Next 3 steps:** (1) monitor/checkpoint full-v2 without changing inference; (2) finish artifact/screenshot audits and score all saved predictions in Chalk; (3) replace provisional report/chart/CSV, check visuals, push results for Lead to merge.
- **Known limits:** full-run results pending; historical URL labels stale; only 3 sandbox cases; complete billing unknown (never zero). Evidence review is unblinded author review, not independent validation. No new full run needed; reserve final slot.
- **Dependencies:** `matplotlib==3.10.8` installed/pinned in `evals/requirements.txt`; Lead may add to root requirements. Runtime identifiers in `full-v2/runtime_info.json` (baseline Haiku, verdict Sonnet, Droid Haiku).
- **How to run:** shared interpreter `../HackHarvard/.venv/bin/python`; `-m pytest tests evals -q --basetemp=/tmp/tripwire-pytest`; workflow/resume command in `evals/README.md`. Score `python evals/chalk_score.py evals/runs/full-v2`; report `MPLCONFIGDIR=/tmp/tripwire-matplotlib python -m evals.report evals/runs/full-v2`. Never run Photon from Evals.

## How to run
- Activate: `source .venv/bin/activate`
- App (live iMessage): `.venv/bin/python -m src.main` · local REPL: `.venv/bin/python -m src.main --cli`
- Tests: `.venv/bin/python -m pytest -q` (runs tests/ and evals/, offline)
- Evals: _(fill in)_

## Decisions log
- Tripwire, Python, Fintech & Cybersecurity track; sponsors Factory + Chalk + Photon.
