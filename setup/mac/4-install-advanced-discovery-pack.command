#!/bin/zsh
set -u

echo "CleanMol Advanced Discovery Pack (optional)"
echo
echo "This installs optional advanced packages into a separate environment:"
echo "  cleanmol/backend/.venv_advanced"
echo
echo "Public preview note: Chemprop support is scaffolded but not active CleanMol scoring yet."
echo "CleanMol Core rankings still use RDKit Morgan fingerprint baseline and heuristic triage scoring."
echo
echo "If this setup fails, CleanMol Core is still available."
echo "Candidate rankings will use RDKit Morgan fingerprint baseline and heuristic triage scoring unless another model is configured."
echo

exit_failed() {
  echo
  echo "Advanced Discovery Pack setup did not complete."
  echo
  echo "CleanMol Core is still available."
  echo "Candidate rankings will use RDKit Morgan fingerprint baseline and heuristic triage scoring unless another model is configured."
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3.11, then run this again."
  exit 1
fi

if [ ! -d "cleanmol/backend/.venv_advanced" ]; then
  python3 -m venv "cleanmol/backend/.venv_advanced" || exit_failed
fi

source "cleanmol/backend/.venv_advanced/bin/activate"
python -m pip install --upgrade pip || exit_failed
python -m pip install "chemprop>=2" || exit_failed

echo
echo "Advanced Discovery Pack package setup completed."
echo "Chemprop is available only for manual/future integration work in this preview."
echo "REINVENT 4 still requires separate expert configuration and a config file."
echo "FairChem/UMA is an expert/manual integration and is not installed by this script."
exit 0
