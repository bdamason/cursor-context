# =============================================================================
# Script: start-cursor-with-secrets.ps1
# Purpose: Launch Cursor IDE with Bitwarden secrets loaded into environment
# Author: ESO BI Team
# Date: 2025-11-26
# Usage: Right-click > Run with PowerShell, or create a shortcut
# =============================================================================

# Set working directory to script location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Cursor IDE Launcher with Secrets" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: SSL workaround for corporate environments
Write-Host "[1/4] Setting SSL workaround..." -ForegroundColor Yellow
$env:NODE_TLS_REJECT_UNAUTHORIZED = "0"
Write-Host "      Done" -ForegroundColor Green
Write-Host ""

# Step 2: Check Bitwarden status
Write-Host "[2/4] Checking Bitwarden status..." -ForegroundColor Yellow
try {
    $status = bw status 2>$null | ConvertFrom-Json
} catch {
    Write-Host "      Bitwarden CLI not found or error occurred" -ForegroundColor Red
    Write-Host "      Please install: winget install Bitwarden.CLI" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

if ($status.status -eq "unauthenticated") {
    Write-Host "      You need to log in to Bitwarden first" -ForegroundColor Red
    Write-Host ""
    Write-Host "      Run this command manually:" -ForegroundColor Yellow
    Write-Host "        bw login" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "      Status: $($status.status)" -ForegroundColor Green
Write-Host ""

# Step 3: Unlock vault if needed
Write-Host "[3/4] Unlocking Bitwarden vault..." -ForegroundColor Yellow
if ($status.status -eq "locked") {
    Write-Host "      Enter your master password below:" -ForegroundColor Cyan
    Write-Host ""
    $env:BW_SESSION = $(bw unlock --raw)
    
    if (-not $env:BW_SESSION) {
        Write-Host ""
        Write-Host "      Failed to unlock vault" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host ""
    Write-Host "      Vault unlocked successfully" -ForegroundColor Green
} else {
    Write-Host "      Vault already unlocked" -ForegroundColor Green
}
Write-Host ""

# Step 4: Load secrets
Write-Host "[4/4] Loading secrets from Bitwarden..." -ForegroundColor Yellow
Write-Host ""

# Run the load secrets script
& "$scriptDir\load-secrets-from-bitwarden.ps1"

if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
    Write-Host ""
    Write-Host "Warning: Some secrets may not have loaded" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Launching Cursor IDE..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Launch Cursor from this directory (inherits environment variables)
Start-Process "cursor" -ArgumentList "." -WorkingDirectory $scriptDir

Write-Host "Cursor launched! This window will close in 3 seconds..." -ForegroundColor Green
Start-Sleep -Seconds 3





