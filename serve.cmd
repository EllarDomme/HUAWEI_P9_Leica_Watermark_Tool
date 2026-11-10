@echo off
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  echo 本地服务已启动：http://localhost:8765
  echo 手机同一 Wi-Fi 下可访问：http://本机IP:8765
  start "" http://localhost:8765
  python -m http.server 8765
) else (
  echo 没找到 Python，直接打开本地文件。
  start "" "index.html"
)
