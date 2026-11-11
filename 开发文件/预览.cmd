@echo off
cd /d "%~dp0.."
title P9 Watermark - dev preview

set "EDGE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=C:\Program Files\Microsoft\Edge\Application\msedge.exe"

echo Starting preview server ...
start "" /min py -3 "%~dp0dev_server.py"
timeout /t 2 >nul

echo Opening phone-sized window ...
start "" "%EDGE%" --app=http://127.0.0.1:8090/index.html --window-size=360,700 --window-position=80,40

echo.
echo   Edit index.html, then the window reloads itself.
echo   Close this window to stop the server.
pause >nul

for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8090 ^| findstr LISTENING') do taskkill /f /pid %%p >nul 2>nul

