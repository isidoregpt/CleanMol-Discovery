@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo    KEVIN - Multi-Model Chemistry Dataset Builder
echo    Full Installation Script for Windows
echo ============================================================
echo.

:: Check for Python
echo [1/8] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

:: Check for Node.js
echo.
echo [2/8] Checking for Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH.
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=1" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
echo Found Node.js %NODE_VERSION%

:: Check for npm
echo.
echo [3/8] Checking for npm...
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm is not installed or not in PATH.
    echo npm should come with Node.js installation.
    pause
    exit /b 1
)
for /f "tokens=1" %%i in ('npm --version 2^>^&1') do set NPM_VERSION=%%i
echo Found npm %NPM_VERSION%

:: Store the root directory
set ROOT_DIR=%cd%

:: Create backend virtual environment
echo.
echo [4/8] Creating Python virtual environment for backend...
cd "%ROOT_DIR%\kevin\backend"
if exist .venv (
    echo Virtual environment already exists, removing old one...
    rmdir /s /q .venv
)
python -m venv .venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)
echo Virtual environment created successfully.

:: Activate virtual environment and install Python dependencies
echo.
echo [5/8] Installing Python dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)
echo Python dependencies installed successfully.
call deactivate

:: Install frontend dependencies
echo.
echo [6/8] Installing Node.js dependencies for frontend...
cd "%ROOT_DIR%\kevin\frontend"
if exist node_modules (
    echo node_modules already exists, removing old one...
    rmdir /s /q node_modules
)
call npm install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Node.js dependencies.
    pause
    exit /b 1
)
echo Node.js dependencies installed successfully.

:: Create data directories
echo.
echo [7/8] Creating default data directories...
if not exist "%USERPROFILE%\Kevin\input" mkdir "%USERPROFILE%\Kevin\input"
if not exist "%USERPROFILE%\Kevin\output" mkdir "%USERPROFILE%\Kevin\output"
echo Created directories:
echo   - %USERPROFILE%\Kevin\input  (place your PDFs here)
echo   - %USERPROFILE%\Kevin\output (dataset will be saved here)

:: Return to root
cd "%ROOT_DIR%"

:: Final summary
echo.
echo [8/8] Installation complete!
echo.
echo ============================================================
echo    INSTALLATION SUCCESSFUL
echo ============================================================
echo.
echo Next steps:
echo.
echo   1. Run the application:
echo      Double-click "run.bat" or run it from command prompt
echo.
echo   2. Open your browser to:
echo      http://localhost:3000
echo.
echo   3. Enter your API keys:
echo      - Anthropic (required): Get from https://console.anthropic.com/
echo      - OpenAI (for audit): Get from https://platform.openai.com/
echo      - Google (for gaps): Get from https://makersuite.google.com/
echo.
echo   4. Set your folders:
echo      - Input:  %USERPROFILE%\Kevin\input
echo      - Output: %USERPROFILE%\Kevin\output
echo.
echo   5. Place PDF files in the input folder and click "Run Pipeline"
echo.
echo ============================================================
echo.
pause
