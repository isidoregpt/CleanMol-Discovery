@echo off
setlocal

echo CleanMol Advanced Discovery Pack (optional)
echo.
echo This installs optional advanced packages into a separate environment:
echo   cleanmol\backend\.venv_advanced
echo.
echo Public preview note: Chemprop support is scaffolded but not active CleanMol scoring yet.
echo CleanMol Core rankings still use RDKit Morgan fingerprint baseline and heuristic triage scoring.
echo.
echo If this setup fails, CleanMol Core is still available.
echo Candidate rankings will use RDKit Morgan fingerprint baseline and heuristic triage scoring unless another model is configured.
echo.

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..\..
pushd "%REPO_ROOT%"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11, then run this again.
  popd
  exit /b 1
)

if not exist "cleanmol\backend\.venv_advanced" (
  python -m venv "cleanmol\backend\.venv_advanced"
  if errorlevel 1 goto failed
)

call "cleanmol\backend\.venv_advanced\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto failed

python -m pip install "chemprop>=2"
if errorlevel 1 goto failed

echo.
echo Advanced Discovery Pack package setup completed.
echo Chemprop is available only for manual/future integration work in this preview.
echo REINVENT 4 still requires separate expert configuration and a config file.
echo FairChem/UMA is an expert/manual integration and is not installed by this script.
popd
exit /b 0

:failed
echo.
echo Advanced Discovery Pack setup did not complete.
echo.
echo CleanMol Core is still available.
echo Candidate rankings will use RDKit Morgan fingerprint baseline and heuristic triage scoring unless another model is configured.
popd
exit /b 1
