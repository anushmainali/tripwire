#!/usr/bin/env bash
# Run the live Tripwire iMessage poller and restart it if it crashes.
# Usage (repo root): scripts/run_tripwire.sh      Stop: Ctrl-C (twice if it is mid-restart)
# Only ONE poller may run at a time; this script refuses to start a second one.
set -u
cd "$(dirname "$0")/.."
mkdir -p logs
if pgrep -f "python -m src.main$" >/dev/null; then
  echo "A Tripwire poller is already running (pid $(pgrep -f 'python -m src.main$')). Not starting another." >&2
  exit 1
fi
trap 'echo "stopping"; kill "${child:-0}" 2>/dev/null; exit 0' INT TERM
while true; do
  echo "[$(date)] starting Tripwire poller" | tee -a logs/tripwire.log
  .venv/bin/python -m src.main 2>&1 | tee -a logs/tripwire.log &
  child=$!
  wait "$child"
  echo "[$(date)] poller exited ($?); restarting in 5s" | tee -a logs/tripwire.log
  sleep 5
done
