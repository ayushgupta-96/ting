@echo off
echo Stopping Toing Backend and Cloudflare Tunnel...
taskkill /F /IM cloudflared.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
echo Stopped successfully.
