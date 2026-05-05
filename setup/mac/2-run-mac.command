#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_FOLDER="cleanmol"
BACKEND_DIR="$ROOT_DIR/$APP_FOLDER/backend"
FRONTEND_DIR="$ROOT_DIR/$APP_FOLDER/frontend"
RUNTIME_DIR="$ROOT_DIR/.cleanmol-runtime"
PID_FILE="$RUNTIME_DIR/pids"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"

echo
echo "============================================================"
echo "   CleanMol Discovery - Starting On Mac"
echo "============================================================"
echo

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: 2-run-mac.command is for macOS."
  echo "On Windows, use the files in setup/windows."
  exit 1
fi

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "ERROR: Backend is not installed. Run ./1-install-mac.command first."
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "ERROR: Frontend is not installed. Run ./1-install-mac.command first."
  exit 1
fi

mkdir -p "$RUNTIME_DIR"

if [[ -f "$SCRIPT_DIR/3-end-mac.command" ]]; then
  "$SCRIPT_DIR/3-end-mac.command" --quiet || true
fi

find_free_port() {
  local start="$1"
  local end="$2"
  local port
  for port in $(seq "$start" "$end"); do
    if ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "$port"
      return 0
    fi
  done
  return 1
}

FRONTEND_PORT="$(find_free_port 3000 3024)" || {
  echo "ERROR: No available frontend port found from 3000 to 3024."
  exit 1
}

echo "Starting backend on http://localhost:8787 ..."
cd "$BACKEND_DIR"
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8787 > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
deactivate

echo "Waiting for backend..."
sleep 3

echo "Starting frontend on http://localhost:$FRONTEND_PORT ..."
cd "$FRONTEND_DIR"
CLEANMOL_FRONTEND_PORT="$FRONTEND_PORT" npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

cat > "$PID_FILE" <<EOF
BACKEND_PID=$BACKEND_PID
FRONTEND_PID=$FRONTEND_PID
FRONTEND_PORT=$FRONTEND_PORT
EOF

sleep 4

echo
echo "============================================================"
echo "   CleanMol Discovery IS RUNNING"
echo "============================================================"
echo
echo "Backend:  http://localhost:8787"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo
echo "Logs:"
echo "  Backend:  $BACKEND_LOG"
echo "  Frontend: $FRONTEND_LOG"
echo
echo "To stop CleanMol:"
echo "  ./3-end-mac.command"
echo

open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 || true
