@echo off
echo --- CLEARING SYSTEM STATE ---
taskkill /F /IM python.exe /T
taskkill /F /IM node.exe /T
docker exec mcp_gemini_1 pkill -f openclaw.mjs
echo --- RESETTING TASKS ---
python scripts\emergency_reset.py
echo --- SYSTEM READY ---
pause
