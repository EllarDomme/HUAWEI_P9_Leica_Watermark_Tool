@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EXIF Watermark - local server

rem --- 优先用 py 启动器（Windows 自带，指向真正的 Python） ---
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"

rem --- 退而求其次：确认 python 真的是 Python 3（避开应用商店占位符） ---
if not defined PY (
  python -c "import sys;print(sys.version_info[0])" >"%TEMP%\_pyv.txt" 2>nul
  set /p PYV=<"%TEMP%\_pyv.txt"
  if "%PYV%"=="3" set "PY=python"
  del "%TEMP%\_pyv.txt" >nul 2>nul
)

if not defined PY (
  echo [!] Python not found. Opening index.html directly...
  echo     Phone access needs Python; install it or copy index.html to the phone.
  start "" "index.html"
  pause
  exit /b 1
)

echo ==========================================================
echo   EXIF Watermark - local server
echo.
echo   On this PC :  http://localhost:8765
echo   On phone   :  http://YOUR-PC-IP:8765
echo.
echo   Find YOUR-PC-IP by running:  ipconfig
echo   (use the IPv4 under the Wi-Fi adapter, e.g. 192.168.x.x)
echo.
echo   Phone must be on the SAME Wi-Fi. Ctrl+C to stop.
echo ==========================================================
echo.

start "" http://localhost:8765
%PY% -m http.server 8765 --bind 0.0.0.0
pause
