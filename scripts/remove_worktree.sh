#!/usr/bin/env bash
# Remove an agent worktree made by new_worktree.sh. Deletes its branch only if it is
# already merged into main; otherwise the branch is kept.
#
# Usage: scripts/remove_worktree.sh <name>
set -euo pipefail

name="${1:?usage: scripts/remove_worktree.sh <name>}"
main_root="$(git worktree list --porcelain | awk 'NR==1 {print $2}')"
dir="$(dirname "$main_root")/hackharvard-$name"
branch="feat/$name"

# Fails (and keeps everything) if the worktree has uncommitted changes.
git -C "$main_root" worktree remove "$dir"

if git -C "$main_root" branch --merged main --format='%(refname:short)' | grep -qx "$branch"; then
  git -C "$main_root" branch -d "$branch"
else
  echo "Kept branch $branch (not merged into main)."
fi
