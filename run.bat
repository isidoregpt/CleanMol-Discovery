@echo off
setlocal

echo.
echo ============================================================
echo    KEVIN - Multi-Model Chemistry Dataset Builder
echo    Starting Application...
echo ============================================================
echo.

:: Store the root directory
set ROOT_DIR=%cd%

:: Check if installation has been done
if not exist "%ROOT_DIR%\kevin\backend\.venv" (
    echo ERROR: Backend not installed. Please run install.bat first.
    pause
    exit /b 1
)
if not exist "%ROOT_DIR%\kevin\frontend\node_modules" (
    echo ERROR: Frontend not installed. Please run install.bat first.
    pause
    exit /b 1
)

:: Kill any existing processes on our ports
echo Checking for existing processes on ports 8787 and 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8787" ^| findstr "LISTENING"') do (
    echo Killing process on port 8787 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo Killing process on port 3000 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

:: Start backend server in a new window
echo.
echo Starting backend server on http://localhost:8787 ...
start "Kevin Backend" cmd /k "cd /d "%ROOT_DIR%\kevin\backend" && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 127.0.0.1 --port 8787"

:: Wait for backend to initialize
echo Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

:: Start frontend server in a new window
echo Starting frontend server on http://localhost:3000 ...
start "Kevin Frontend" cmd /k "cd /d "%ROOT_DIR%\kevin\frontend" && npm run dev"

:: Wait for frontend to initialize
echo Waiting for frontend to initialize...
timeout /t 5 /nobreak >nul

:: Open browser
echo.
echo Opening browser...
start http://localhost:3000

echo.
echo ============================================================
echo    KEVIN IS RUNNING
echo ============================================================
echo.
echo    Backend:  http://localhost:8787
echo    Frontend: http://localhost:3000 (opens automatically)
echo.
echo    Two terminal windows have opened:
echo    - "Kevin Backend" - Python FastAPI server
echo    - "Kevin Frontend" - Next.js development server
echo.
echo    To stop the application:
echo    Close both terminal windows, or press Ctrl+C in each.
echo.
echo    Default folders:
echo    - Input:  %USERPROFILE%\Kevin\input
echo    - Output: %USERPROFILE%\Kevin\output
echo.
echo ============================================================
echo.
echo You can close this window. The servers will continue running.
echo.
pause
