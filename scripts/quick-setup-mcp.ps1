# Quick Setup for MCP with ea-dev-keyvault-shared
# This script sets up your local environment to work with the existing Key Vault

Write-Host ""
Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host " MCP Quick Setup - Enterprise Analytics Dev Environment" -ForegroundColor Cyan
Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host ""

# Load Key Vault configuration
. .\mcp-keyvault-config.ps1
$config = Get-MCPKeyVaultConfig

Write-Host "Configuration Details:" -ForegroundColor Yellow
Show-MCPKeyVaultConfig

# Step 1: Check Azure login
Write-Host "Step 1: Checking Azure authentication..." -ForegroundColor Yellow
$azContext = az account show 2>$null | ConvertFrom-Json

if (-not $azContext) {
    Write-Host "  [WARNING] Not logged in to Azure" -ForegroundColor Yellow
    Write-Host "  Attempting to login..." -ForegroundColor Gray
    az login --tenant $config.TenantId
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Login failed. Please run 'az login' manually." -ForegroundColor Red
        exit 1
    }
    
    $azContext = az account show | ConvertFrom-Json
}

Write-Host "  [OK] Logged in as: $($azContext.user.name)" -ForegroundColor Green

# Step 2: Check subscription
Write-Host ""
Write-Host "Step 2: Verifying subscription..." -ForegroundColor Yellow

if ($azContext.id -ne $config.SubscriptionId) {
    Write-Host "  [WARNING] Current subscription doesn't match. Switching..." -ForegroundColor Yellow
    az account set --subscription $config.SubscriptionId
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Switched to US-ESOSuite-Development subscription" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Failed to switch subscription" -ForegroundColor Red
        Write-Host "  You may not have access. Contact your Azure admin." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "  [OK] Already using correct subscription" -ForegroundColor Green
}

# Step 3: Verify Key Vault access
Write-Host ""
Write-Host "Step 3: Verifying Key Vault access..." -ForegroundColor Yellow

$null = az keyvault secret list --vault-name $config.Name 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] You have access to $($config.Name)" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Cannot access Key Vault" -ForegroundColor Red
    Write-Host ""
    Write-Host "  You need permissions to access this Key Vault." -ForegroundColor Yellow
    Write-Host "  Please ask your Azure administrator to grant you access:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  az keyvault set-policy ``" -ForegroundColor Gray
    Write-Host "      --name $($config.Name) ``" -ForegroundColor Gray
    Write-Host "      --upn YOUR_EMAIL@esocorp.com ``" -ForegroundColor Gray
    Write-Host "      --secret-permissions get list" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

# Step 4: Check existing secrets
Write-Host ""
Write-Host "Step 4: Checking existing secrets..." -ForegroundColor Yellow

$secrets = az keyvault secret list --vault-name $config.Name --query "[].name" -o json | ConvertFrom-Json

if ($secrets.Count -eq 0) {
    Write-Host "  [INFO] No secrets found in Key Vault" -ForegroundColor Cyan
    Write-Host "  You'll need to add secrets for MCP to work." -ForegroundColor White
    $needsSecrets = $true
} else {
    Write-Host "  [OK] Found $($secrets.Count) secret(s) in Key Vault:" -ForegroundColor Green
    $secrets | ForEach-Object {
        Write-Host "     - $_" -ForegroundColor Gray
    }
    $needsSecrets = $false
}

# Step 5: Set up environment
Write-Host ""
Write-Host "Step 5: Setting up environment..." -ForegroundColor Yellow

# Set MCP_KEYVAULT_NAME for easy reference
[System.Environment]::SetEnvironmentVariable("MCP_KEYVAULT_NAME", $config.Name, "Process")
Write-Host "  [OK] Set MCP_KEYVAULT_NAME=$($config.Name)" -ForegroundColor Green

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "  [INFO] Creating .env file..." -ForegroundColor Cyan
    "# MCP Environment Configuration`n# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n`nMCP_KEYVAULT_NAME=$($config.Name)`n" | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "  [OK] Created .env file" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host " Setup Complete!" -ForegroundColor Green
Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host ""

if ($needsSecrets) {
    Write-Host "[WARNING] Next Steps - Add Required Secrets:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Add the secrets MCP needs to function:" -ForegroundColor White
    Write-Host ""
    
    # List of required secrets
    $requiredSecrets = @(
        @{Name="azure-tenant-id"; Desc="Azure AD Tenant ID"; Example=$config.TenantId},
        @{Name="azure-client-id"; Desc="Service Principal App ID"; Example="12345678-1234-1234-1234-123456789012"},
        @{Name="azure-client-secret"; Desc="Service Principal Secret"; Example="your-secret-value"},
        @{Name="azure-subscription-id"; Desc="Azure Subscription ID"; Example=$config.SubscriptionId},
        @{Name="synapse-workspace-name"; Desc="Synapse Workspace Name"; Example="your-synapse-workspace"},
        @{Name="synapse-resource-group"; Desc="Synapse Resource Group"; Example="rg-dev-synapse"},
        @{Name="datalake-account-name"; Desc="Data Lake Storage Account"; Example="yourstorageaccount"},
        @{Name="datalake-container-name"; Desc="Data Lake Container"; Example="data"},
        @{Name="sql-server"; Desc="SQL Server Endpoint"; Example="yourserver.database.windows.net"},
        @{Name="sql-database"; Desc="SQL Database Name"; Example="yourdatabase"},
        @{Name="sql-username"; Desc="SQL Username"; Example="sqladmin"},
        @{Name="sql-password"; Desc="SQL Password"; Example="your-password"}
    )
    
    Write-Host "Method 1: Interactive (recommended for sensitive data)" -ForegroundColor Cyan
    Write-Host "  .\add-secret-to-keyvault.ps1 -SecretName 'azure-client-secret' -Prompt" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Method 2: Direct command" -ForegroundColor Cyan
    Write-Host "  az keyvault secret set --vault-name $($config.Name) --name 'azure-client-secret' --value 'YOUR_VALUE'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Required Secrets:" -ForegroundColor White
    foreach ($secret in $requiredSecrets) {
        Write-Host "  - $($secret.Name)" -ForegroundColor Gray -NoNewline
        Write-Host " - $($secret.Desc)" -ForegroundColor DarkGray
    }
    Write-Host ""
    Write-Host "TIP: Some secrets might already exist in other Key Vaults." -ForegroundColor Cyan
    Write-Host "     Ask your team where these values are stored!" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "[OK] Next Steps - Load Secrets:" -ForegroundColor Green
    Write-Host ""
    Write-Host "Load secrets into your environment:" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Option 1: Load to environment variables (current session)" -ForegroundColor Cyan
    Write-Host "  .\load-secrets-from-keyvault.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  # Option 2: Export to .env file (persistent)" -ForegroundColor Cyan
    Write-Host "  .\load-secrets-from-keyvault.ps1 -ExportToFile" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  # Option 3: Use startup script (automatic)" -ForegroundColor Cyan
    Write-Host "  .\mcp-startup.ps1" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "Documentation:" -ForegroundColor White
Write-Host "  - Full guide: AZURE_KEYVAULT_SETUP.md" -ForegroundColor Gray
Write-Host "  - Security: MCP_SECURITY_GUIDE.md" -ForegroundColor Gray
Write-Host ""

