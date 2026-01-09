@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo    KEVIN - Multi-Model Chemistry Dataset Builder
echo    Full Installation Script for Windows
echo ============================================================
echo.

:: Store the root directory FIRST
set ROOT_DIR=%cd%

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
python --version
echo.

:: Check for Node.js
echo [2/8] Checking for Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH.
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo.

:: Check for npm (simplified - just check it exists, don't capture version)
echo [3/8] Checking for npm...
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm is not installed or not in PATH.
    echo npm should come with Node.js installation.
    pause
    exit /b 1
)
echo npm found.
echo.

:: Create backend virtual environment
echo [4/8] Creating Python virtual environment for backend...
cd /d "%ROOT_DIR%\kevin\backend"
if %errorlevel% neq 0 (
    echo ERROR: Cannot find kevin\backend folder.
    echo Make sure you're running this from the repository root.
    pause
    exit /b 1
)
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
echo.

:: Activate virtual environment and install Python dependencies
echo [5/8] Installing Python dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)
echo Python dependencies installed successfully.
call deactivate
echo.

:: Install frontend dependencies
echo [6/8] Installing Node.js dependencies for frontend...
cd /d "%ROOT_DIR%\kevin\frontend"
if %errorlevel% neq 0 (
    echo ERROR: Cannot find kevin\frontend folder.
    pause
    exit /b 1
)
if exist node_modules (
    echo node_modules already exists, removing old one...
    rmdir /s /q node_modules
)
echo Running npm install (this may take a minute)...
call npm install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Node.js dependencies.
    pause
    exit /b 1
)
echo Node.js dependencies installed successfully.
echo.

:: Create data directories
echo [7/8] Creating default data directories...
if not exist "%USERPROFILE%\Kevin\input" mkdir "%USERPROFILE%\Kevin\input"
if not exist "%USERPROFILE%\Kevin\output" mkdir "%USERPROFILE%\Kevin\output"
echo Created directories:
echo   - %USERPROFILE%\Kevin\input  (place your PDFs here)
echo   - %USERPROFILE%\Kevin\output (dataset will be saved here)
echo.

:: Return to root
cd /d "%ROOT_DIR%"

:: Final summary
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
