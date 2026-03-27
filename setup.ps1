# Research Automation - Environment Setup Script
# Run this script once to create and configure the project's virtual environment.
# Usage: .\setup.ps1

param(
    [switch]$SkipPlaywright
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Research Automation - Environment Setup  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Check for Python ---
Write-Host "[1/4] Checking for Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "      Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Error "Python not found. Please install Python 3.9+ and add it to your PATH."
    exit 1
}

# --- 2. Create virtual environment ---
$venvPath = Join-Path $PSScriptRoot "venv"
if (Test-Path $venvPath) {
    Write-Host "[2/4] Virtual environment already exists at .\venv - skipping creation." -ForegroundColor Yellow
} else {
    Write-Host "[2/4] Creating virtual environment in .\venv ..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment."
        exit 1
    }
    Write-Host "      Virtual environment created successfully." -ForegroundColor Green
}

# --- 3. Install dependencies ---
Write-Host "[3/4] Installing dependencies from requirements.txt ..." -ForegroundColor Yellow
$pipExe = Join-Path $venvPath "Scripts\pip.exe"
& $pipExe install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to upgrade pip."
    exit 1
}
& $pipExe install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies."
    exit 1
}
Write-Host "      Dependencies installed successfully." -ForegroundColor Green

# --- 4. Install Playwright browsers ---
if (-not $SkipPlaywright) {
    Write-Host "[4/4] Installing Playwright browser (Chromium) ..." -ForegroundColor Yellow
    $playwrightExe = Join-Path $venvPath "Scripts\playwright.exe"
    & $playwrightExe install chromium
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install Playwright browser."
        exit 1
    }
    Write-Host "      Playwright Chromium installed successfully." -ForegroundColor Green
} else {
    Write-Host "[4/4] Skipping Playwright browser installation (-SkipPlaywright flag set)." -ForegroundColor Yellow
}

# --- Done ---
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Setup complete!                          " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To activate the environment in a new terminal, run:" -ForegroundColor White
Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host ""
Write-Host "To run research:" -ForegroundColor White
Write-Host "    python run_research.py `"your topic here`" --iterations=2 --browser=True" -ForegroundColor Green
Write-Host ""
