@echo off
REM ============================================================
REM PHASE 2: Complete Docker Environment Reset
REM ============================================================
REM This script:
REM 1. Removes old container
REM 2. Cleans up browser session lock
REM 3. Recreates container with new code
REM 4. Waits for VNC initialization
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo  PHASE 2: DOCKER ENVIRONMENT RESET
echo ============================================================
echo.

REM Get current directory
for /f "delims=" %%i in ('cd') do set "PROJECTDIR=%%i"
echo [INFO] Project directory: !PROJECTDIR!

REM Step 1: Remove old container
echo.
echo [STEP 1] Removing old container (if exists)...
docker rm -f mcp_gemini_1 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Old container removed
) else (
    echo [INFO] No old container found (OK)
)

REM Step 2: Clean browser session lock
echo.
echo [STEP 2] Cleaning browser session lock...
if exist "!PROJECTDIR!\data\browser_sessions\acc_1\SingletonLock" (
    del /F "!PROJECTDIR!\data\browser_sessions\acc_1\SingletonLock" >nul 2>&1
    echo [OK] Lock file removed
) else (
    echo [INFO] No lock file found (OK)
)

REM Step 3: Check if Docker image exists
echo.
echo [STEP 3] Verifying Docker image...
docker images | findstr "research_automation" >nul
if %errorlevel% equ 0 (
    echo [OK] Docker image found
) else (
    echo [ERROR] Docker image not found. Build it first with:
    echo         cd infra/docker && docker-compose build
    exit /b 1
)

REM Step 4: Create new container
echo.
echo [STEP 4] Creating new container with updated code...
echo [INFO] Running: docker run -d --name mcp_gemini_1 ...
docker run -d ^
  --name mcp_gemini_1 ^
  -p 8001:8000 ^
  -p 5901:5900 ^
  -e DISPLAY=:99 ^
  -e ACCOUNT_ID=acc_1 ^
  -v "!PROJECTDIR!/src:/app/src" ^
  -v "!PROJECTDIR!/temp:/app/temp" ^
  -v "!PROJECTDIR!/data/browser_sessions/acc_1:/app/data/browser_sessions/acc_1" ^
  research_automation-gemini-acc-1

if %errorlevel% equ 0 (
    echo [OK] Container created successfully
) else (
    echo [ERROR] Failed to create container
    exit /b 1
)

REM Step 5: Wait for VNC server initialization
echo.
echo [STEP 5] Waiting for VNC server to initialize (15 seconds)...
for /l %%i in (15,-1,1) do (
    cls
    echo.
    echo ============================================================
    echo  WAITING FOR CONTAINER BOOT
    echo ============================================================
    echo.
    echo  Initializing Docker container...
    echo  - Starting Playwright browser
    echo  - Launching VNC display
    echo  - Loading Python code
    echo.
    echo  Remaining: %%i seconds
    echo.
    echo  Container status:
    docker ps -f name=mcp_gemini_1 --format "  {{.Status}}"
    echo.
    echo ============================================================
    timeout /t 1 /nobreak >nul
)

cls
echo.
echo ============================================================
echo  PHASE 2 COMPLETE ✓
echo ============================================================
echo.
echo Container mcp_gemini_1 is now running with:
echo   - New ai_studio_controller.py code
echo   - Port 8001: Browser Agent (Playwright)
echo   - Port 5901: VNC Display (for visual debugging)
echo.
echo Ready for PHASE 3: Automated self-test
echo.
echo To monitor container:
echo   docker logs -f mcp_gemini_1
echo.
echo To view in VNC:
echo   VNC Viewer -> localhost:5901
echo.
echo ============================================================
echo.

pause
