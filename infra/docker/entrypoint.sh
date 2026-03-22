#!/bin/bash
set -e

# Cleanup any stale locks from previous unclean shutdowns
echo "[Entrypoint] Cleaning up old Xvfb locks..."
rm -rf /tmp/.X99-lock /tmp/.X11-unix/X99

# 1. Start Xvfb (Virtual Display) in background
echo "[Entrypoint] Starting Xvfb on :99..."
Xvfb :99 -screen 0 1280x800x24 > /dev/null 2>&1 &

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

# 2. Start Window Manager (Optional, but good for some apps)
echo "[Entrypoint] Starting Fluxbox..."
fluxbox > /dev/null 2>&1 &

# 2.5 Start VNC Server to watch the Linux screen (No password)
echo "[Entrypoint] Starting VNC Server on port 5900..."
x11vnc -display :99 -nopw -forever -shared -quiet &

# 3. Start MCP Server (The Main Process)
# Assuming main.py or similar entrypoint exists. 
# We'll use a placeholder for now, to be replaced by the actual python start command.
echo "[Entrypoint] Ready for Interactive Debugging! Keeping container alive."
export PYTHONPATH=/app ; python src/mcp/server/main.py
