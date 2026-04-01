#!/bin/bash
set -e

# Cleanup any stale locks from previous unclean shutdowns
echo "[Entrypoint] Cleaning up old Xvfb locks..."
rm -rf /tmp/.X99-lock /tmp/.X11-unix/X99

# ARE: Nuclear Wipe of browser session locks to prevent SingletonLock crashes
echo "[Entrypoint] Cleaning up browser session locks..."
rm -rf /app/data/browser_sessions/*/SingletonLock

# 1. Start Xvfb (Virtual Display) in background
echo "[Entrypoint] Starting Xvfb on :99 (1920x1080)..."
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &

# Wait for Xvfb to be ready
echo "[Entrypoint] Waiting for Xvfb..."
for i in {1..10}; do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "[Entrypoint] Xvfb is ready!"
        break
    fi
    echo "[Entrypoint] Waiting for Xvfb... ($i/10)"
    sleep 1
done

# 2. Start Window Manager
echo "[Entrypoint] Starting Fluxbox..."
fluxbox > /dev/null 2>&1 &

# 2.5 Start VNC Server (no password, for debugging)
echo "[Entrypoint] Starting VNC Server on port 5900..."
x11vnc -display :99 -nopw -forever -shared -quiet &

# 3. Start Application
export PYTHONPATH=/app

if [ $# -eq 0 ]; then
    echo "[Entrypoint] Starting DEFAULT MCP Server..."
    exec python src/mcp/server/main.py
else
    echo "[Entrypoint] Starting CUSTOM Command: $@"
    exec "$@"
fi
