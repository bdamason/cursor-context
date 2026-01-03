# =============================================================================
# Script: run-confluence-sync.ps1
# Purpose: Load secrets from Bitwarden and sync documentation to Confluence
# Author: ESO BI Team
# Date: 2025-11-29
# =============================================================================

param(
    [Parameter(Mandatory=$false)]
    [switch]$SkipSecrets,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Confluence Documentation Sync" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found! Please install Python." -ForegroundColor Red
    exit 1
}

# Check required packages
Write-Host ""
Write-Host "[INFO] Checking required Python packages..." -ForegroundColor Gray

$requiredPackages = @("atlassian-python-api", "md2cf", "mistune")
$missingPackages = @()

foreach ($pkg in $requiredPackages) {
    $installed = pip show $pkg 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingPackages += $pkg
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "[WARN] Missing packages: $($missingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "[INFO] Installing missing packages..." -ForegroundColor Gray
    foreach ($pkg in $missingPackages) {
        pip install $pkg
    }
}

Write-Host "[OK] All required packages installed" -ForegroundColor Green

# Load secrets from Bitwarden (unless skipped)
if (-not $SkipSecrets) {
    Write-Host ""
    Write-Host "[INFO] Loading secrets from Bitwarden..." -ForegroundColor Gray
    
    # Check if secrets are already loaded
    if ($env:CONFLUENCE_USERNAME -and $env:CONFLUENCE_API_TOKEN) {
        Write-Host "[OK] Confluence credentials already loaded" -ForegroundColor Green
    } else {
        # Run the Bitwarden loader
        if (Test-Path ".\load-secrets-from-bitwarden.ps1") {
            & .\load-secrets-from-bitwarden.ps1
            
            if (-not $env:CONFLUENCE_USERNAME -or -not $env:CONFLUENCE_API_TOKEN) {
                Write-Host "[ERROR] Failed to load Confluence credentials!" -ForegroundColor Red
                Write-Host ""
                Write-Host "Make sure you have:" -ForegroundColor Yellow
                Write-Host "  1. Bitwarden CLI installed (winget install Bitwarden.CLI)" -ForegroundColor White
                Write-Host "  2. Logged in (bw login)" -ForegroundColor White
                Write-Host "  3. Vault unlocked (bw unlock)" -ForegroundColor White
                Write-Host '  4. Session set ($env:BW_SESSION="<key>")' -ForegroundColor White
                Write-Host "  5. 'confluence-mcp' item in Bitwarden with username and API token" -ForegroundColor White
                Write-Host ""
                exit 1
            }
        } else {
            Write-Host "[ERROR] load-secrets-from-bitwarden.ps1 not found!" -ForegroundColor Red
            Write-Host ""
            Write-Host "Set credentials manually:" -ForegroundColor Yellow
            Write-Host '  $env:CONFLUENCE_USERNAME = "your-email@eso.com"' -ForegroundColor White
            Write-Host '  $env:CONFLUENCE_API_TOKEN = "your-api-token"' -ForegroundColor White
            Write-Host ""
            exit 1
        }
    }
}

# Verify credentials
Write-Host ""
Write-Host "[INFO] Verifying Confluence credentials..." -ForegroundColor Gray
if ($env:CONFLUENCE_USERNAME) {
    Write-Host "  Username: $($env:CONFLUENCE_USERNAME)" -ForegroundColor Green
} else {
    Write-Host "  Username: [NOT SET]" -ForegroundColor Red
    exit 1
}

if ($env:CONFLUENCE_API_TOKEN) {
    $tokenPreview = $env:CONFLUENCE_API_TOKEN.Substring(0, [Math]::Min(8, $env:CONFLUENCE_API_TOKEN.Length)) + "..."
    Write-Host "  API Token: $tokenPreview" -ForegroundColor Green
} else {
    Write-Host "  API Token: [NOT SET]" -ForegroundColor Red
    exit 1
}

# Run the sync
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Starting Confluence Sync..." -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] Would sync the following files:" -ForegroundColor Yellow
    Write-Host ""
    python -c @"
import sync_to_confluence
for path, mapping in sync_to_confluence.FILE_MAPPINGS.items():
    print(f'  {path}')
    print(f'    -> {mapping["parent"]} / {mapping["title"]}')
"@
    Write-Host ""
    Write-Host "[DRY RUN] No changes made. Remove -DryRun to actually sync." -ForegroundColor Yellow
} else {
    python sync_to_confluence.py
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Sync Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "View in Confluence: https://esosolutions.atlassian.net/wiki/spaces/IA/pages" -ForegroundColor Gray
Write-Host ""



























