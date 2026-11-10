#!/usr/bin/env python3
"""
Launcher script that automatically verifies port availability and falls back to an available port.
Usage:
    python run.py [--port <number>] [--host <ip>]
"""

import sys
import socket
import argparse
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

if sys.platform == "win32":
    import asyncio
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

import uvicorn
from app.core.config import settings

def is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        # connect_ex returns 0 if connection succeeded (i.e. port is in use)
        return s.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", port)) != 0

def find_available_port(host: str, start_port: int, max_attempts: int = 20) -> int:
    for p in range(start_port, start_port + max_attempts):
        if is_port_free(host, p):
            return p
    return start_port

def main():
    parser = argparse.ArgumentParser(description="Run Toing Platform FastAPI backend")
    parser.add_argument("--host", default=settings.HOST or "0.0.0.0", help="Binding host")
    parser.add_argument("--port", type=int, default=settings.PORT or 8001, help="Binding port")
    parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload")
    args = parser.parse_args()

    host = args.host
    desired_port = args.port

    actual_port = desired_port
    if not is_port_free(host, desired_port):
        print(f"[!] Warning: Port {desired_port} is currently busy / occupied.")
        actual_port = find_available_port(host, desired_port + 1)
        print(f"[+] Automatically switched to available port: {actual_port}")
    else:
        print(f"[+] Selected port {actual_port} is available.")

    print("=" * 60)
    print(f"🚀 Launching Toing Platform Backend on http://{host}:{actual_port}")
    print(f"📖 Swagger Docs:  http://localhost:{actual_port}/docs")
    print(f"💓 Health Check:  http://localhost:{actual_port}/health")
    print("=" * 60)

    uvicorn.run("app.main:app", host=host, port=actual_port, reload=args.reload)

if __name__ == "__main__":
    main()
