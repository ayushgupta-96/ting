@echo off
cd /d "%~dp0..\backend"
if not exist "logs" mkdir "logs"

:loop
echo [%date% %time%] Starting Cloudflare Tunnel for port 8001... >> logs\tunnel.log
cloudflared tunnel --url http://127.0.0.1:8001 --logfile logs\tunnel.log
echo [%date% %time%] Tunnel disconnected. Reconnecting in 3 seconds... >> logs\tunnel.log
timeout /t 3 /nobreak >nul
goto loop
