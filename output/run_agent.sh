#!/bin/bash
# run_agent.sh - Transparent Diagnostic Bridge
export DISPLAY=:99
export OPENAI_BASE_URL=http://host.docker.internal:9002/v1
export OPENCLAW_CONFIG_PATH=/app/openclaw-main/openclaw.json

echo "=== AGENT START ==="
echo "Date: $(date)"
echo "PWD: $(pwd)"
echo "Whoami: $(whoami)"
echo "Node: $(node -v)"

echo "--- NETWORK DIAGNOSTIC ---"
echo "Testing connectivity to Proxy at host.docker.internal:9002..."
curl -is http://host.docker.internal:9002/v1/models | head -n 5 || echo "ERROR: Proxy unreachable!"

cd /app/openclaw-main || { echo "ERROR: cd failed"; exit 1; }
echo "Inside Dir: $(pwd)"
ls -la openclaw.mjs dist/entry.js

echo "--- EXECUTING NODE ---"
# Removed stdbuf (can cause hangs in some Node environments).
export TERM=xterm-256color
node openclaw.mjs agent --local --agent main --session-id "$1" --message "$2" 2>&1


EXIT_CODE=$?

echo "--- NODE EXITED (Code: $EXIT_CODE) ---"
exit $EXIT_CODE
