@echo off
REM ============================================================
REM COMPLETE PIPELINE: Phase 1-3 Execution
REM ============================================================
REM Phase 1: Code refactoring (ALREADY COMPLETE)
REM Phase 2: Docker reset
REM Phase 3: Automated self-test
REM ============================================================

setlocal enabledelayedexpansion

cls
echo.
echo ██████╗ ███████╗███████╗ █████╗ ███████╗████████╗ ██████╗ ██╗ ██╗███████╗
echo ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔═══██╗██║  ██║██╔════╝
echo ██████╔╝█████╗  █████╗  ███████║█████╗     ██║   ██║   ██║███████║█████╗
echo ██╔══██╗██╔══╝  ██╔══╝  ██╔══██║██╔══╝     ██║   ██║   ██║╚════██║██╔══╝
echo ██║  ██║███████╗██║     ██║  ██║███████╗   ██║   ╚██████╔╝     ██║███████╗
echo ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝╚══════╝   ╚═╝    ╚═════╝      ╚═╝╚══════╝
echo.
echo  AI Studio Browser Automation - Complete Pipeline
echo.
echo ============================================================
echo.

REM Check if we're in the right directory
if not exist "src\core\ai_studio_controller.py" (
    echo ERROR: ai_studio_controller.py not found
    echo Please run this script from: Research_Automation directory
    pause
    exit /b 1
)

echo [INFO] PHASE OVERVIEW:
echo.
echo  PHASE 1: Code Refactoring
echo    Status: ✓ COMPLETE
echo    - Eliminated coordinate-based clicks
echo    - Implemented robust locators
echo    - Added SPA state triggering
echo.
echo  PHASE 2: Docker Environment Reset
echo    Status: ⏳ PENDING
echo    - Remove old container
echo    - Clean browser sessions
echo    - Start new container with updated code
echo.
echo  PHASE 3: Automated Self-Test
echo    Status: ⏳ PENDING
echo    - Test proxy connection
echo    - Test AI Studio submission
echo    - Verify response extraction
echo.
echo ============================================================
echo.
echo Proceed with Phase 2 & 3? (y/n)
set /p PROCEED="Enter choice: "
if /i not "%PROCEED%"=="y" (
    echo Aborted.
    exit /b 0
)

REM ============================================================
REM PHASE 2: Docker Reset
REM ============================================================
echo.
echo ============================================================
echo EXECUTING: PHASE 2 - Docker Environment Reset
echo ============================================================
echo.

REM Get current directory
for /f "delims=" %%i in ('cd') do set "PROJECTDIR=%%i"

echo [STEP 1] Removing old container...
docker rm -f mcp_gemini_1 >nul 2>&1
echo [STEP 2] Cleaning browser session lock...
if exist "!PROJECTDIR!\data\browser_sessions\acc_1\SingletonLock" (
    del /F "!PROJECTDIR!\data\browser_sessions\acc_1\SingletonLock" >nul 2>&1
)
echo [STEP 3] Creating new container...
docker run -d ^
  --name mcp_gemini_1 ^
  -p 8001:8000 ^
  -p 5901:5900 ^
  -e DISPLAY=:99 ^
  -e ACCOUNT_ID=acc_1 ^
  -v "!PROJECTDIR!/src:/app/src" ^
  -v "!PROJECTDIR!/temp:/app/temp" ^
  -v "!PROJECTDIR!/data/browser_sessions/acc_1:/app/data/browser_sessions/acc_1" ^
  research_automation-gemini-acc-1 >nul 2>&1

if %errorlevel% equ 0 (
    echo.
    echo [STEP 4] Waiting for container boot (15 seconds)...
    for /l %%i in (15,-1,1) do (
        <nul set /p ".=." 
        timeout /t 1 /nobreak >nul
    )
    echo.
    echo ✓ PHASE 2 COMPLETE
) else (
    echo.
    echo ✗ PHASE 2 FAILED: Could not create container
    echo   Check if Docker is running and image exists:
    echo   docker images ^| findstr research_automation
    pause
    exit /b 1
)

REM ============================================================
REM PHASE 3: Automated Self-Test
REM ============================================================
echo.
echo ============================================================
echo EXECUTING: PHASE 3 - Automated Self-Test
echo ============================================================
echo.

python PHASE3_SELF_TEST.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo ✓✓✓ ALL PHASES SUCCESSFUL ✓✓✓
    echo ============================================================
    echo.
    echo The pipeline is now fully refactored and tested!
    echo.
    echo Next steps:
    echo   1. Monitor with: docker logs -f mcp_gemini_1
    echo   2. Debug with VNC: localhost:5901
    echo   3. Test again with: python PHASE3_SELF_TEST.py
    echo.
) else (
    echo.
    echo ============================================================
    echo ✗ PHASE 3 FAILED
    echo ============================================================
    echo.
    echo Debugging:
    echo   1. Check Docker logs: docker logs mcp_gemini_1
    echo   2. View browser: VNC Viewer -^> localhost:5901
    echo   3. Ensure proxy is accessible: curl http://localhost:9002/v1/models
    echo.
)

pause
