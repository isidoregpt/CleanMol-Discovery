#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_FOLDER="cleanmol"
BACKEND_DIR="$ROOT_DIR/$APP_FOLDER/backend"
FRONTEND_DIR="$ROOT_DIR/$APP_FOLDER/frontend"

echo
echo "============================================================"
echo "   CleanMol Discovery - Mac Installation"
echo "   Apple Silicon / M-Series supported"
echo "============================================================"
echo

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: install-mac.command is for macOS."
  echo "On Windows, use install-windows.bat."
  exit 1
fi

ARCH="$(uname -m)"
if [[ "$ARCH" == "arm64" ]]; then
  echo "[Mac] Apple Silicon detected: $ARCH"
else
  echo "[Mac] Intel Mac detected: $ARCH"
  echo "[Mac] This script is optimized for M-Series Macs but should also work on Intel Macs."
fi
echo

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "ERROR: Python 3.10+ is required."
  echo "Install it from https://www.python.org/downloads/macos/ or with Homebrew: brew install python"
  exit 1
fi

echo "[1/8] Checking Python..."
"$PYTHON_BIN" --version
"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("ERROR: CleanMol requires Python 3.10+.")
PY
echo

echo "[2/8] Checking Node.js..."
if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: Node.js 20.9+ is required."
  echo "Install it from https://nodejs.org/ or with Homebrew: brew install node"
  exit 1
fi
node --version
node -e "const v=process.versions.node.split('.').map(Number); process.exit((v[0] > 20 || (v[0] === 20 && v[1] >= 9)) ? 0 : 1)"
if [[ $? -ne 0 ]]; then
  echo "ERROR: CleanMol requires Node.js 20.9+ because the frontend uses Next.js 16."
  exit 1
fi
echo

echo "[3/8] Checking npm..."
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is required and should come with Node.js."
  exit 1
fi
npm --version
echo

echo "[4/8] Creating Python virtual environment..."
cd "$BACKEND_DIR"
if [[ -d ".venv" ]]; then
  echo "Removing old backend virtual environment..."
  rm -rf .venv
fi
"$PYTHON_BIN" -m venv .venv
echo

echo "[5/8] Installing Python dependencies..."
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
deactivate
echo

echo "[6/8] Installing frontend dependencies..."
cd "$FRONTEND_DIR"
if [[ -d "node_modules" ]]; then
  echo "Removing old frontend node_modules..."
  rm -rf node_modules
fi
npm install
echo

echo "[7/8] Creating default data folders..."
mkdir -p "$HOME/CleanMol/input"
mkdir -p "$HOME/CleanMol/output"
echo "Input:  $HOME/CleanMol/input"
echo "Output: $HOME/CleanMol/output"
echo

echo "[8/8] Installation complete."
echo
echo "============================================================"
echo "   INSTALLATION SUCCESSFUL"
echo "============================================================"
echo
echo "Next steps:"
echo "  1. Run:  ./run-mac.command"
echo "  2. Open: http://localhost:3000"
echo "  3. Add API keys in the app."
echo "  4. Use these folders if you want defaults:"
echo "     Input:  $HOME/CleanMol/input"
echo "     Output: $HOME/CleanMol/output"
echo
echo "If macOS says this file is not executable, run:"
echo "  chmod +x install-mac.command run-mac.command stop-mac.command"
echo
