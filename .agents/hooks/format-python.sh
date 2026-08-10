#!/usr/bin/env bash
# Format a single edited Python file with Black + isort. Always fail open.
set -u

exit_open() {
  exit 0
}

trap exit_open EXIT

input="$(cat || true)"
if [[ -z "${input}" ]]; then
  exit 0
fi

# Prefer python3 for JSON parse; never fail closed if parsing fails.
file_path="$(
  printf '%s' "${input}" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for key in ("file_path", "filePath", "path", "file"):
    value = data.get(key)
    if isinstance(value, str) and value:
        print(value)
        break
' 2>/dev/null || true
)"

if [[ -z "${file_path}" || "${file_path}" != *.py ]]; then
  exit 0
fi

if [[ ! -f "${file_path}" ]]; then
  exit 0
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${root}" || exit 0

run_fmt() {
  local tool="$1"
  shift
  if [[ -x "${root}/.venv/bin/python" ]]; then
    "${root}/.venv/bin/python" -m "${tool}" "$@" >/dev/null 2>&1 || true
  elif command -v uv >/dev/null 2>&1; then
    uv run "${tool}" "$@" >/dev/null 2>&1 || true
  else
    python3 -m "${tool}" "$@" >/dev/null 2>&1 || true
  fi
}

run_fmt black "${file_path}"
run_fmt isort "${file_path}"
exit 0
