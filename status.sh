#!/usr/bin/env bash
# status.sh — one-glance dashboard for the Tripwire agents.
#
#   ./status.sh            show status once
#   ./status.sh --watch    refresh every 10 min; pops a Mac notification (with sound)
#                          only when something needs you
#
# Leave `./status.sh --watch` running in its own Terminal tab.

cd "$(dirname "$0")" || exit 1
INTERVAL=600
STATE_FILE=".status_last_alert"

needs_human() {
  # Lines under "## NEEDS HUMAN" (until the next "## "), minus the template hint line.
  # Only bullet items count as requests; italic notes like "_(... done ...)_" are ignored.
  awk '/^## NEEDS HUMAN/{f=1;next} /^## /{f=0} f' "$1" 2>/dev/null \
    | grep -E '^[[:space:]]*[-*] '
}

limit_wait() {
  # $1 = lane. If the latest session failed because of a usage limit, print when it resets.
  local log="logs/$1.log" last
  last=$(grep -vE '^\[(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ' "$log" 2>/dev/null \
         | grep -iE 'usage limit|session limit|rate limit|try again at|resets' | tail -1)
  # Only if the most recent exit was a failure (a limit hit), not an older message.
  grep 'exited code=' "$log" 2>/dev/null | tail -1 | grep -q 'code=0' && return
  [ -n "$last" ] || return
  echo "$last" | grep -oiE '(try again at|resets) [0-9: ]*[ap]m' | tail -1
}

lane_health() {
  # $1 = lane name. Prints a problem description, or nothing if healthy.
  local log="logs/$1.log"
  [ -f "$log" ] || { echo "$1: no log file yet"; return; }
  pgrep -f "run_agent.sh $1" >/dev/null || { echo "$1: watchdog NOT running (tab closed?)"; return; }
  # Count fast failures among the last 3 session exits.
  local fast
  fast=$(grep 'exited code=' "$log" | tail -3 | grep -v 'code=0' | grep -cE 'after ([0-9]|[0-9][0-9]|1[01][0-9])s')
  if [ "$fast" -ge 3 ] && [ -z "$(limit_wait "$1")" ]; then
    local err
    err=$(grep -vE '^\[' "$log" | grep -iE 'error|invalid|expired|auth|limit|login' | tail -1 | cut -c1-120)
    echo "$1: failing repeatedly (${err:-check logs/$1.log})"
  fi
}

show() {
  clear
  echo "================ TRIPWIRE STATUS — $(date '+%a %I:%M %p') ================"
  echo

  # Processes
  echo "PROCESSES"
  for lane in lead evals; do
    if pgrep -f "run_agent.sh $lane" >/dev/null; then w="running"; else w="STOPPED"; fi
    echo "  watchdog $lane: $w"
  done
  pgrep -f "claude -p" >/dev/null && echo "  Claude Code: working now" || echo "  Claude Code: idle / waiting"
  pgrep -f "codex exec" >/dev/null && echo "  Codex:       working now" || echo "  Codex:       idle / waiting"
  pgrep caffeinate >/dev/null && echo "  caffeinate:  on" || echo "  caffeinate:  OFF (Mac may sleep!)"
  for lane in lead evals; do
    lw=$(limit_wait "$lane"); [ -n "$lw" ] && echo "  $lane: paused for usage limit — $lw (normal, resumes automatically)"
  done
  echo

  # Last watchdog events
  for lane in lead evals; do
    echo "LAST EVENTS ($lane)"
    grep -E '^\[(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ' "logs/$lane.log" 2>/dev/null | tail -3 | sed 's/^/  /'
    echo
  done

  # Commits
  git fetch --quiet origin 2>/dev/null
  echo "COMMITS IN LAST HOUR: $(git log --all --since='1 hour ago' --oneline 2>/dev/null | wc -l | tr -d ' ')"
  git log --all --oneline -8 --format='  %h %ar  %s' 2>/dev/null
  echo

  # Needs human (main's HANDOFF.md is the source of truth; the evals lane merges into it)
  local nh
  nh=$(needs_human HANDOFF.md)
  echo "NEEDS HUMAN"
  if [ -n "$nh" ]; then echo "$nh" | sed 's/^/  /'; else echo "  (nothing)"; fi
  echo

  # Problems → notification
  local problems=""
  for lane in lead evals; do
    p=$(lane_health "$lane"); [ -n "$p" ] && problems="$problems$p; "
  done
  pgrep caffeinate >/dev/null || problems="${problems}caffeinate is off; "
  [ -n "$nh" ] && problems="${problems}agents need you (see NEEDS HUMAN); "

  if [ -n "$problems" ]; then
    echo "⚠️  ATTENTION: $problems"
    if [ "$WATCH" = 1 ]; then
      sig=$(printf '%s' "$problems$nh" | cksum | cut -d' ' -f1)
      if [ "$sig" != "$(cat "$STATE_FILE" 2>/dev/null)" ]; then
        echo "$sig" > "$STATE_FILE"
        msg=$(printf '%s' "$problems" | tr '"' "'" | cut -c1-200)
        osascript -e "display notification \"$msg\" with title \"Tripwire needs you\" sound name \"Glass\"" 2>/dev/null
      fi
    fi
  else
    echo "✅ All good — nothing needs you."
    rm -f "$STATE_FILE"
  fi
  [ "$WATCH" = 1 ] && echo && echo "(refreshing every $((INTERVAL/60)) min — Ctrl+C to stop)"
}

WATCH=0
[ "${1:-}" = "--watch" ] && WATCH=1
if [ "$WATCH" = 1 ]; then
  while true; do show; sleep "$INTERVAL"; done
else
  show
fi
