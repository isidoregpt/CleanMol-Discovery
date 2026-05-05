@echo off
setlocal
echo.
echo ============================================================
echo    CleanMol Discovery - Stopping All Servers
echo ============================================================
echo.

:: Kill backend (uvicorn on port 8787)
echo Stopping backend server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8787" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo Killed process on port 8787 (PID: %%a)
)

:: Kill frontend (node on ports 3000-3024)
echo Stopping frontend server...
for /l %%p in (3000,1,3024) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%%p" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
        echo Killed process on port %%p (PID: %%a)
    )
)

:: Also try to kill any remaining node processes from our app.
taskkill /F /IM "node.exe" /FI "WINDOWTITLE eq CleanMol Frontend" >nul 2>&1

echo.
echo All CleanMol servers have been stopped.
echo.
pause
