# =============================================================================
# Script: setup-mcp-sql-for-boss.ps1
# Purpose: Set up MCP-SQL with Azure MFA authentication for Cursor
# Author: ESO BI Team
# Date: 2025-11-25
# Usage: Run in PowerShell (no admin required for most operations)
# 
# Authentication: Azure MFA (uses your Azure AD login)
# No secrets or Key Vault required - just login with az login
# =============================================================================

param(
    [switch]$SkipPrerequisites,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# =============================================================================
# HARDCODED CONFIGURATION - No Key Vault needed
# =============================================================================
$SqlServer = "ea-sqlserver-enterpriseanalytics-shared.database.windows.net"
$SqlDatabase = "ea-prod-sqldb-semanticdb"
$CursorConfigPath = "$env:USERPROFILE\.cursor"
$McpJsonPath = "$CursorConfigPath\mcp.json"

# Colors for output
function Write-Step { param($msg) Write-Host "`n📌 $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "⚠️  $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "❌ $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "   $msg" -ForegroundColor Gray }

# Header
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║       ESO BI - MCP SQL Setup for Cursor (Azure MFA)            ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Server:   $SqlServer" -ForegroundColor Gray
Write-Host "  Database: $SqlDatabase" -ForegroundColor Gray
Write-Host "  Auth:     Azure MFA (your Azure AD login)" -ForegroundColor Gray
Write-Host ""

# =============================================================================
# STEP 1: Check Prerequisites
# =============================================================================

if (-not $SkipPrerequisites) {
    Write-Step "Checking prerequisites..."
    
    # Check Node.js
    Write-Info "Checking Node.js..."
    $nodeVersion = $null
    try {
        $nodeVersion = node --version 2>$null
    } catch { }
    
    if ($nodeVersion) {
        Write-Success "Node.js installed: $nodeVersion"
    } else {
        Write-Warning "Node.js not found!"
        Write-Host ""
        $install = Read-Host "Would you like to install Node.js now? (Y/N)"
        if ($install -eq 'Y' -or $install -eq 'y') {
            Write-Info "Installing Node.js via winget..."
            winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
            Write-Warning "Please restart PowerShell after installation and run this script again."
            exit 0
        } else {
            Write-Error "Node.js is required. Please install it manually from https://nodejs.org"
            exit 1
        }
    }
    
    # Check Azure CLI
    Write-Info "Checking Azure CLI..."
    $azVersion = $null
    try {
        $azVersion = az --version 2>$null | Select-Object -First 1
    } catch { }
    
    if ($azVersion) {
        Write-Success "Azure CLI installed"
    } else {
        Write-Warning "Azure CLI not found!"
        Write-Host ""
        $install = Read-Host "Would you like to install Azure CLI now? (Y/N)"
        if ($install -eq 'Y' -or $install -eq 'y') {
            Write-Info "Installing Azure CLI via winget..."
            winget install Microsoft.AzureCLI --accept-source-agreements --accept-package-agreements
            Write-Warning "Please restart PowerShell after installation and run this script again."
            exit 0
        } else {
            Write-Error "Azure CLI is required for Azure MFA authentication."
            exit 1
        }
    }
}

# =============================================================================
# STEP 2: Azure Login
# =============================================================================

Write-Step "Checking Azure login status..."

$azAccount = $null
try {
    $azAccount = az account show 2>$null | ConvertFrom-Json
} catch { }

if ($azAccount) {
    Write-Success "Already logged in as: $($azAccount.user.name)"
    Write-Info "Subscription: $($azAccount.name)"
} else {
    Write-Warning "Not logged in to Azure"
    Write-Host ""
    Write-Host "Opening browser for Azure login..." -ForegroundColor Yellow
    Write-Host "Please sign in with your ESO credentials." -ForegroundColor Yellow
    Write-Host ""
    
    az login
    
    $azAccount = az account show 2>$null | ConvertFrom-Json
    if ($azAccount) {
        Write-Success "Logged in as: $($azAccount.user.name)"
    } else {
        Write-Error "Azure login failed. Please try again."
        exit 1
    }
}

# =============================================================================
# STEP 3: Create Cursor Config Directory
# =============================================================================

Write-Step "Setting up Cursor configuration..."

if (-not (Test-Path $CursorConfigPath)) {
    New-Item -ItemType Directory -Path $CursorConfigPath -Force | Out-Null
    Write-Success "Created Cursor config directory: $CursorConfigPath"
} else {
    Write-Info "Cursor config directory exists: $CursorConfigPath"
}

# =============================================================================
# STEP 4: Create or Update mcp.json
# =============================================================================

Write-Step "Configuring MCP SQL server..."

# Define the MSSQL MCP configuration
$mssqlConfig = @{
    command = "npx"
    args = @("-y", "@modelcontextprotocol/server-mssql")
    env = @{
        MSSQL_HOST = $SqlServer
        MSSQL_DATABASE = $SqlDatabase
        MSSQL_AUTHENTICATION_TYPE = "azure-active-directory-default"
        MSSQL_ENCRYPT = "true"
    }
}

# Check if mcp.json already exists
if (Test-Path $McpJsonPath) {
    Write-Info "Existing mcp.json found"
    
    if (-not $Force) {
        $overwrite = Read-Host "mcp.json already exists. Add/update MSSQL config? (Y/N)"
        if ($overwrite -ne 'Y' -and $overwrite -ne 'y') {
            Write-Warning "Skipping mcp.json update. Run with -Force to overwrite."
            Write-Host ""
            Write-Host "Your existing mcp.json was not modified." -ForegroundColor Gray
            Write-Host "Restart Cursor to use any existing MCP configuration." -ForegroundColor Gray
            exit 0
        }
    }
    
    # Read existing config
    try {
        $existingConfig = Get-Content $McpJsonPath -Raw | ConvertFrom-Json
    } catch {
        Write-Warning "Could not parse existing mcp.json. Creating backup and starting fresh."
        Copy-Item $McpJsonPath "$McpJsonPath.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        $existingConfig = @{ mcpServers = @{} }
    }
    
    # Ensure mcpServers exists
    if (-not $existingConfig.mcpServers) {
        $existingConfig | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue @{} -Force
    }
    
    # Add or update mssql config
    if ($existingConfig.mcpServers -is [PSCustomObject]) {
        $existingConfig.mcpServers | Add-Member -NotePropertyName "mssql" -NotePropertyValue $mssqlConfig -Force
    } else {
        $existingConfig.mcpServers["mssql"] = $mssqlConfig
    }
    
    # Write updated config
    $existingConfig | ConvertTo-Json -Depth 10 | Set-Content $McpJsonPath -Encoding UTF8
    Write-Success "Updated mcp.json with MSSQL configuration"
    
} else {
    # Create new mcp.json
    $newConfig = @{
        mcpServers = @{
            mssql = $mssqlConfig
        }
    }
    
    $newConfig | ConvertTo-Json -Depth 10 | Set-Content $McpJsonPath -Encoding UTF8
    Write-Success "Created new mcp.json with MSSQL configuration"
}

# Display the configuration
Write-Host ""
Write-Host "Configuration saved to: $McpJsonPath" -ForegroundColor Gray
Write-Host ""
Write-Host "MSSQL MCP Configuration:" -ForegroundColor Cyan
Write-Host "  Server:   $SqlServer" -ForegroundColor Gray
Write-Host "  Database: $SqlDatabase" -ForegroundColor Gray
Write-Host "  Auth:     Azure Active Directory (MFA)" -ForegroundColor Gray

# =============================================================================
# STEP 5: Test Azure Token (Verifies MFA access)
# =============================================================================

Write-Step "Testing Azure MFA access to SQL Server..."

try {
    $token = az account get-access-token --resource https://database.windows.net/ 2>$null | ConvertFrom-Json
    if ($token) {
        Write-Success "Azure SQL access token acquired!"
        Write-Info "Token expires: $($token.expiresOn)"
        Write-Info "You have Azure MFA access to SQL Server."
    }
} catch {
    Write-Warning "Could not acquire SQL access token."
    Write-Info "This might be normal if you haven't been granted database access yet."
    Write-Info "Contact benjamin.mason@eso.com if you need database access."
}

# =============================================================================
# STEP 6: Done!
# =============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    🎉 Setup Complete! 🎉                        ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "Configuration Summary:" -ForegroundColor Cyan
Write-Host "  Config File: $McpJsonPath" -ForegroundColor Gray
Write-Host "  SQL Server:  $SqlServer" -ForegroundColor Gray
Write-Host "  Database:    $SqlDatabase" -ForegroundColor Gray
Write-Host "  Auth Method: Azure MFA (your Azure AD login)" -ForegroundColor Gray
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. RESTART CURSOR completely (close all windows and reopen)" -ForegroundColor White
Write-Host ""
Write-Host "  2. Open the AI Chat (Ctrl+L or Cmd+L)" -ForegroundColor White
Write-Host ""
Write-Host "  3. Test with this query:" -ForegroundColor White
Write-Host '     "List the schemas in the database"' -ForegroundColor Cyan
Write-Host ""
Write-Host "  4. If it works, try:" -ForegroundColor White
Write-Host '     "Show me 5 rows from [bi].[Account]"' -ForegroundColor Cyan
Write-Host ""

Write-Host "Troubleshooting:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  • 'Login failed' or 'Not authorized'" -ForegroundColor Gray
Write-Host "    → You need database access. Contact benjamin.mason@eso.com" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  • 'Azure token expired'" -ForegroundColor Gray
Write-Host "    → Run: az login" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  • 'MCP not showing in Cursor'" -ForegroundColor Gray
Write-Host "    → Restart Cursor completely (not just reload)" -ForegroundColor DarkGray
Write-Host ""

# Keep window open if run by double-clicking
if ($Host.Name -eq "ConsoleHost") {
    Write-Host "Press any key to exit..." -ForegroundColor DarkGray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

