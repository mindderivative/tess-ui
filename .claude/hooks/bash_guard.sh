#!/bin/sh
# PreToolUse (Bash): block a force push, a push of tags and a push to main (other pushes are allowed, AGENTS.md); before a `git commit`, check the staged Python files (pyflakes level, so old findings elsewhere do not block).
cd "$CLAUDE_PROJECT_DIR" || exit 0
cmd=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')
push=$(printf '%s' "$cmd" | grep -Eo '(^|[;&|[:space:]])git[[:space:]]+(-[^[:space:]]+[[:space:]]+)*push([[:space:]][^;&|]*)?$|git[[:space:]]+(-[^[:space:]]+[[:space:]]+)*push[[:space:]][^;&|]*' | head -1)
if [ -n "$push" ]; then
  # Push is allowed (AGENTS.md) except force, tags and main.
  if printf '%s' "$push" | grep -Eq '(^|[[:space:]])(-[a-zA-Z]*f[a-zA-Z]*|--force[^[:space:]]*|--mirror|--delete|--tags|--follow-tags|--tag|\+[^[:space:]]+|[^[:space:]]*refs/tags/[^[:space:]]*|(HEAD:)?(refs/heads/)?main)([[:space:]]|$)'; then
    echo "Blocked: a force push, a push of tags or a push to main needs the maintainer (AGENTS.md)." >&2
    exit 2
  fi
fi
if printf '%s' "$cmd" | grep -Eq '(^|[;&|[:space:]])git[[:space:]]+commit([[:space:]]|$)'; then
  ruff=.venv/bin/ruff; [ -x "$ruff" ] || ruff=$(command -v ruff)
  staged=$(git diff --cached --name-only --diff-filter=ACM -- '*.py')
  if [ -n "$ruff" ] && [ -n "$staged" ]; then
    out=$(printf '%s\n' "$staged" | xargs "$ruff" check --isolated --select E9,F --quiet 2>&1) || { printf 'ruff found problems in staged files:\n%s\n' "$out" >&2; exit 2; }
  fi
fi
exit 0
