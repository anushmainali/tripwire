#!/usr/bin/env bash
# run_agent.sh — keeps a coding agent working until the deadline, restarting it
# whenever a session ends (finished a chunk, crashed, or hit a usage limit).
#
# Usage (from the repo root, HackHarvard/):
#   ./run_agent.sh lead     # Claude Code, works in this folder on `main`
#   ./run_agent.sh evals    # Codex, works in ../hh-evals on branch `evals`
#
# Stop early:  touch .agent_stop   (in the repo root)
# Logs:        logs/<lane>.log

set -u
LANE="${1:-}"
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
STOP_FILE="$REPO_ROOT/.agent_stop"
mkdir -p "$REPO_ROOT/logs"
LOG="$REPO_ROOT/logs/${LANE}.log"

# Deadline: agents stop starting new sessions at 7:30 AM ET Sunday Oct 18, 2026.
DEADLINE_LOCAL="2026-10-18 07:30"
if date -j >/dev/null 2>&1; then   # macOS
  DEADLINE=$(date -j -f "%Y-%m-%d %H:%M" "$DEADLINE_LOCAL" +%s)
else                                # GNU/Linux
  DEADLINE=$(date -d "$DEADLINE_LOCAL" +%s)
fi

LEAD_PROMPT='You are the LEAD agent for Tripwire (HackHarvard 2026). Read AGENTS.md, SPEC.md and HANDOFF.md first, then `git pull` and run the tests.
The human has granted you FULL autonomy and full access. Do not ask questions or wait for approval; make reasonable decisions. The human will not check in until the morning.
Continue from "Next steps" in HANDOFF.md and build toward the Definition of Done in AGENTS.md, following the timeline and the checkpoint protocol exactly: small steps, test, commit, push, update HANDOFF.md after every step. You may be cut off at any moment; you will be restarted automatically and must be able to resume from the repo alone.
Merge origin/evals into main whenever it has new commits and tests pass.
If something needs the human (login, key, phone test), add it under NEEDS HUMAN in HANDOFF.md, mock around it, and keep working on other items.
Keep working until the session ends. Never stop just because a step is finished; pick the next one.'

EVALS_PROMPT='You are the EVALS agent for Tripwire (HackHarvard 2026). Read AGENTS.md, SPEC.md and HANDOFF.md first, then `git fetch && git merge origin/main` and run the tests.
The human has granted you FULL autonomy and full access. Do not ask questions or wait for approval; make reasonable decisions. The human will not check in until the morning.
You own data/, evals/, src/llm.py and scripts/datasets/ only. Build the Chalk Model Gateway client and baseline_classify(), the labeled eval dataset, and the eval harness comparing the baseline vs investigate() (stub investigate() until the Lead version exists on main), then run Chalk Evaluations and produce evals/RESULTS.md and evals/results_chart.png, per SPEC.md section 4.
Follow the checkpoint protocol exactly: small steps, test, commit, push to the `evals` branch, update your section of HANDOFF.md after every step. You may be cut off at any moment; you will be restarted automatically.
Keep working until the session ends. Never stop just because a step is finished; pick the next one.'

case "$LANE" in
  lead)
    WORKDIR="$REPO_ROOT"
    # Unset ANTHROPIC_API_KEY so Claude Code uses your logged-in Claude plan, not a stale API key.
    run() { env -u ANTHROPIC_API_KEY claude -p "$LEAD_PROMPT" --dangerously-skip-permissions; }
    ;;
  evals)
    WORKDIR="$(cd "$REPO_ROOT/.." && pwd)/hh-evals"
    run() { codex exec --dangerously-bypass-approvals-and-sandbox "$EVALS_PROMPT"; }
    ;;
  *)
    echo "Usage: $0 lead|evals"; exit 1 ;;
esac

echo "[$(date)] starting lane=$LANE workdir=$WORKDIR" | tee -a "$LOG"

# The evals worktree is created by the lead agent; wait for it.
while [ ! -f "$WORKDIR/AGENTS.md" ]; do
  echo "[$(date)] waiting for $WORKDIR to exist (lead creates it)..." | tee -a "$LOG"
  sleep 120
  [ -f "$STOP_FILE" ] && exit 0
done

RUN=0
while true; do
  NOW=$(date +%s)
  if [ "$NOW" -ge "$DEADLINE" ]; then
    echo "[$(date)] deadline reached, stopping." | tee -a "$LOG"; break
  fi
  if [ -f "$STOP_FILE" ]; then
    echo "[$(date)] stop file found, stopping." | tee -a "$LOG"; break
  fi

  RUN=$((RUN+1))
  echo "[$(date)] ===== session $RUN =====" | tee -a "$LOG"
  START=$(date +%s)
  ( cd "$WORKDIR" && run ) >> "$LOG" 2>&1
  CODE=$?
  DUR=$(( $(date +%s) - START ))
  echo "[$(date)] session $RUN exited code=$CODE after ${DUR}s" | tee -a "$LOG"

  # Short or failed sessions usually mean a usage limit / outage: back off longer.
  if [ "$CODE" -ne 0 ] || [ "$DUR" -lt 120 ]; then
    echo "[$(date)] likely usage limit or error; sleeping 10 min before retry" | tee -a "$LOG"
    sleep 600
  else
    sleep 30
  fi
done
