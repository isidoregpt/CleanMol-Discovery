#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/.cleanmol-runtime"
PID_FILE="$RUNTIME_DIR/pids"
QUIET="${1:-}"

if [[ "$QUIET" != "--quiet" ]]; then
  echo
  echo "============================================================"
  echo "   CleanMol Discovery - Stopping Mac Servers"
  echo "============================================================"
  echo
fi

kill_pid() {
  local pid="${1:-}"
  local label="${2:-process}"
  if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    sleep 1
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
    [[ "$QUIET" == "--quiet" ]] || echo "Stopped $label (PID $pid)."
  fi
}

kill_cleanmol_port() {
  local port="$1"
  local pid command
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ "$command" == *"uvicorn"* || "$command" == *"next"* || "$command" == *"node"* || "$command" == *"npm"* ]]; then
      kill_pid "$pid" "CleanMol port $port"
    fi
  done < <(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
}

if [[ -f "$PID_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$PID_FILE"
  kill_pid "${BACKEND_PID:-}" "backend"
  kill_pid "${FRONTEND_PID:-}" "frontend"
  rm -f "$PID_FILE"
fi

kill_cleanmol_port 8787
for port in $(seq 3000 3024); do
  kill_cleanmol_port "$port"
done

[[ "$QUIET" == "--quiet" ]] || echo "CleanMol servers are stopped."
