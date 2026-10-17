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
- **17:35 Sat:** merged final evals (full-v3-baseline-headroom); SUBMISSION Results filled (tie 71.7%; Tripwire 0 scam→safe vs 2, precision 88.9 vs 81.0). Remaining: README results sentence check, phone re-test, polish.
- **17:05 Sat:** merged origin/evals (88 tests pass). Evals full-v2 run is in progress (pid running, 2 of 3 full slots used). When `evals/runs/full-v2/metrics.json` + RESULTS.md are final, fill SUBMISSION.md/README numbers.
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
- **DONE:** gateway + strict single-call baseline; frozen 120-case dataset with provenance/licenses; resumable bounded runner; real Chalk evaluation; `evals/RESULTS.md`, `results.csv`, `results_chart.png`; evidence/script/screenshot audits. **87 tests pass**, ruff clean. Chart visually checked.
- **FINAL RESULTS FOR LEAD:** corrected baseline **71.7% accuracy**, Tripwire **71.7%**; strict FPR **0/60 both**; warning FPR **16.7% vs 20.0%**; scam precision **81.0% vs 88.9%**, recall **68% vs 64%**; median latency **1.31 s vs 21.87 s** (baseline vs Tripwire). Costs unknown. **Do not claim an accuracy win.** Ready-to-use interpretation: `evals/INTERPRETATION.md`.
- **Real Chalk scoring verified:** run `9e278dce-1ee1-426c-aeb8-5961e73a284c`, evaluation `cmvcw1ytn05a501y5sd6ed1ge`, SUCCEEDED; all 240 outputs/eight scorer values match local calculations, zero row errors. Receipts and raw rows in `evals/runs/full-v3-baseline-headroom/`.
- **Correction provenance:** full-v2 completed 240 predictions at investigator commit `f754dc8`, but baseline cap 128 caused 27 incomplete responses. Final v3 repeats all baseline calls at cap 1024, same model/prompt/labels, and reuses exact unchanged Tripwire records guarded by source/input hashes. Both systems have zero inference errors in final comparison. Original v2/report preserved; explicitly disclose correction, do not pitch its 59.2% truncated baseline. **All 3 run slots consumed; no more full runs.**
- **Runtime proof:** 76 successful Droid sessions, 12 preserved scripts; all five urllib.parse audit flags inspected as offline-only. Three sandbox cases: DNS blank, Cuttly 404, FedEx access denied (HTTP 200). No live phishing form captured. Images + review in `full-v2/`; current report cites reused artifacts.
- **Evidence quality:** 21/32 sampled claims fully grounded, 10 partial, 1 unsupported (7 fixed source/label strata cases; unblinded author review). Issues for Lead: .ru cheap/common assertion unsupported; invented lack-of-prize-entry context; general claims presented as observations; static HTML claims overstated. DNS failure still returned a blank image in frozen code; Lead owns production fix.
- **Next 3 steps:** (1) Lead merges `origin/evals`; (2) Lead updates README/SUBMISSION/DEMO with honest tied-accuracy result and tradeoffs; (3) separate development-only hardening if needed, no benchmark retuning or new full runs.
- **How to reproduce artifacts:** `MPLCONFIGDIR=/tmp/tripwire-matplotlib ../HackHarvard/.venv/bin/python -m evals.report evals/runs/full-v3-baseline-headroom`; tests `../HackHarvard/.venv/bin/python -m pytest tests evals -q --basetemp=/tmp/tripwire-pytest`. Scoring command in `evals/README.md` resumes verified receipt without rerunning inference. Never run Photon from Evals.
- **Dependencies/limits:** matplotlib==3.10.8 pinned in `evals/requirements.txt`, installed shared venv. Source labels historical; convenience sample not representative; only 3 detonations; full billing unavailable. Baseline Haiku, verdict Sonnet, Droid Haiku — system comparison, not tools-only causal attribution.

## How to run
- Activate: `source .venv/bin/activate`
- App (live iMessage): `.venv/bin/python -m src.main` · local REPL: `.venv/bin/python -m src.main --cli`
- Tests: `.venv/bin/python -m pytest -q` (runs tests/ and evals/, offline)
- Evals: _(fill in)_

## Decisions log
- Tripwire, Python, Fintech & Cybersecurity track; sponsors Factory + Chalk + Photon.
