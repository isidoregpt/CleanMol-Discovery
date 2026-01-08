@echo off
echo.
echo ============================================================
echo    KEVIN - Stopping All Servers
echo ============================================================
echo.

:: Kill backend (uvicorn on port 8787)
echo Stopping backend server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8787" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo Killed process on port 8787 (PID: %%a)
)

:: Kill frontend (node on port 3000)
echo Stopping frontend server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo Killed process on port 3000 (PID: %%a)
)

:: Also try to kill any remaining node processes from our app
taskkill /F /IM "node.exe" /FI "WINDOWTITLE eq Kevin Frontend" >nul 2>&1

echo.
echo All Kevin servers have been stopped.
echo.
pause
