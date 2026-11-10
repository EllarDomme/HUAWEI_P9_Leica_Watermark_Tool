@echo off
setlocal
cd /d "%~dp0.."
title EXIF Watermark - local server

set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"

if not defined PY (
  python -c "import sys;print(sys.version_info[0])" >"%TEMP%\_pyv.txt" 2>nul
  set /p PYV=<"%TEMP%\_pyv.txt"
  if "%PYV%"=="3" set "PY=python"
  del "%TEMP%\_pyv.txt" >nul 2>nul
)

if not defined PY (
  echo [!] Python not found. Opening index.html directly...
  echo     Phone access needs Python 3.
  start "" "index.html"
  pause
  exit /b 1
)

set "LANIP="
powershell -NoProfile -Command "$c = Get-NetIPConfiguration; foreach ($i in $c) { if ($i.IPv4DefaultGateway -ne $null -and $i.IPv4Address -ne $null) { $i.IPv4Address.IPAddress; break } }" > "%TEMP%\_lanip.txt" 2>nul
if exist "%TEMP%\_lanip.txt" set /p LANIP=<"%TEMP%\_lanip.txt"
del "%TEMP%\_lanip.txt" >nul 2>nul
if not defined LANIP set "LANIP=YOUR-PC-IP"

echo ==========================================================
echo   EXIF Watermark - local server
echo.
echo   On this PC :  http://localhost:8765
echo   On phone   :  http://%LANIP%:8765
echo.
echo   Phone must be on the SAME Wi-Fi. Ctrl+C to stop.
echo ==========================================================
echo.

start "" http://localhost:8765
%PY% -m http.server 8765 --bind 0.0.0.0
pause