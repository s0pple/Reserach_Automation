@echo off
REM ============================================================
REM PHASE 2 & 3: Docker Restart + Test Execution
REM ============================================================

echo.
echo ============================================================
echo PHASE 2: RESTARTING DOCKER CONTAINER
echo ============================================================

docker restart mcp_gemini_1
echo.
echo Waiting 15 seconds for container to boot...
timeout /t 15 /nobreak

echo.
echo ============================================================
echo PHASE 3: TESTING VIA INVOKE-RESTMETHOD
echo ============================================================
echo.
echo Running PowerShell test command...
echo.

powershell -NoProfile -Command ^
  "$result = Invoke-RestMethod -Uri 'http://localhost:9002/v1/responses' -Method Post -Headers @{'Content-Type'='application/json'} -Body '{\"input\": [{\"role\": \"user\", \"content\": \"Erklaere mir in exakt einem Satz, was Venture Capital ist.\"}]}' -ErrorAction Stop; Write-Output ($result | ConvertTo-Json -Depth 10)"

echo.
echo ============================================================
echo Test command executed
echo ============================================================
