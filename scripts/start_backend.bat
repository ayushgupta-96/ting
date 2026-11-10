@echo off
cd /d "%~dp0..\backend"
if not exist "logs" mkdir "logs"
echo [%date% %time%] Starting Toing FastAPI Backend on port 8001... >> logs\backend.log
"C:\Users\akg79\AppData\Local\Programs\Python\Python310\python.exe" run.py --port 8001 >> logs\backend.log 2>&1
