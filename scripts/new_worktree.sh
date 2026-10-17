#!/usr/bin/env bash
# Create a git worktree for one agent: ../hackharvard-<name> on branch feat/<name>,
# with .env and .venv linked back to the main checkout.
#
# Usage: scripts/new_worktree.sh <name> [base-branch]   (base defaults to main)
# Then:  cd ../hackharvard-<name> && claude    (or: codex)
set -euo pipefail

name="${1:?usage: scripts/new_worktree.sh <name> [base-branch]}"
base="${2:-main}"
[[ "$name" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "name must be lowercase letters, digits and dashes" >&2; exit 1; }

# The main checkout is the first entry in `git worktree list`, wherever this is run from.
main_root="$(git worktree list --porcelain | awk 'NR==1 {print $2}')"
dir="$(dirname "$main_root")/hackharvard-$name"
branch="feat/$name"

if [[ -e "$dir" ]]; then
  echo "$dir already exists" >&2
  exit 1
fi

if git -C "$main_root" show-ref --verify --quiet "refs/heads/$branch"; then
  git -C "$main_root" worktree add "$dir" "$branch"
else
  git -C "$main_root" worktree add -b "$branch" "$dir" "$base"
fi

# .env and .venv are gitignored, so link them from the main checkout.
for f in .env .venv; do
  if [[ -e "$main_root/$f" ]]; then
    ln -s "$main_root/$f" "$dir/$f"
  else
    echo "warning: $main_root/$f not found; $f not linked" >&2
  fi
done

echo
echo "Worktree ready: $dir (branch $branch)"
echo "Start an agent:  cd \"$dir\" && claude    # or: codex"
