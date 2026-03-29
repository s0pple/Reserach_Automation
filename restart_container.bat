@echo off
echo ==========================================
echo Restarting Docker Container: mcp_gemini_1
echo ==========================================
docker restart mcp_gemini_1
echo.
echo Waiting 15 seconds for container to boot...
timeout /t 15 /nobreak
echo.
echo ✓ Container restart complete
echo ==========================================
