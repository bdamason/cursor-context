# =============================================================================
# Script: fix-confluence-metadata.ps1
# Purpose: Move "Source: ... | Last Updated" metadata from top to bottom of pages
# Author: ESO BI Team
# Date: 2025-12-08
# =============================================================================

param(
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [string]$SpaceKey = "IA",
    
    [Parameter(Mandatory=$false)]
    [string]$ParentPage = "semantic"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Confluence Metadata Fix Script" -ForegroundColor White
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

$requiredPackages = @("atlassian-python-api")
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
        pip install $pkg --quiet
    }
}

Write-Host "[OK] All required packages installed" -ForegroundColor Green

# Load secrets from Bitwarden
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

# Create Python script
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Processing Confluence Pages..." -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$pythonScript = @"
import os
import sys
import re
from atlassian import Confluence

# Configuration
CONFLUENCE_URL = "https://esosolutions.atlassian.net/wiki"
CONFLUENCE_USERNAME = os.environ.get("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN")
SPACE_KEY = "$SpaceKey"
PARENT_PAGE = "$ParentPage"
DRY_RUN = $($DryRun.IsPresent)

# Connect to Confluence
try:
    confluence = Confluence(
        url=CONFLUENCE_URL,
        username=CONFLUENCE_USERNAME,
        password=CONFLUENCE_API_TOKEN,
        cloud=True
    )
    print("[OK] Connected to Confluence")
except Exception as e:
    print(f"[ERROR] Failed to connect: {e}")
    sys.exit(1)

# Get parent page
try:
    parent = confluence.get_page_by_title(space=SPACE_KEY, title=PARENT_PAGE)
    if not parent:
        print(f"[ERROR] Parent page '{PARENT_PAGE}' not found!")
        sys.exit(1)
    parent_id = parent['id']
    print(f"[OK] Found parent page: {PARENT_PAGE} (ID: {parent_id})")
except Exception as e:
    print(f"[ERROR] Error getting parent page: {e}")
    sys.exit(1)

# Get all child pages recursively
def get_all_child_pages(page_id):
    pages = []
    try:
        children = confluence.get_page_child_by_type(page_id, type='page', start=0, limit=500)
        for child in children:
            pages.append(child)
            # Recursively get children of this child
            pages.extend(get_all_child_pages(child['id']))
    except Exception as e:
        print(f"[WARN] Error getting children for page {page_id}: {e}")
    return pages

print(f"[INFO] Getting all child pages under '{PARENT_PAGE}'...")
all_pages = get_all_child_pages(parent_id)
print(f"[OK] Found {len(all_pages)} pages")
print("")

# Process each page
pages_updated = 0
pages_skipped = 0
pages_error = 0

for page in all_pages:
    page_id = page['id']
    page_title = page['title']
    
    print("=" * 60)
    print(f"Processing: {page_title}")
    print("=" * 60)
    
    try:
        # Get full page content
        full_page = confluence.get_page_by_id(page_id, expand='body.storage,version')
        content = full_page['body']['storage']['value']
        version = full_page['version']['number']
        
        # Pattern to match metadata at the beginning
        # Looks for: <p><strong>Source:</strong> ... | <strong>Last Updated:</strong> ...</p>
        metadata_pattern = r'^(<p[^>]*>)?<strong>Source:</strong>.*?<strong>Last Updated:</strong>.*?</p>\s*'
        
        match = re.search(metadata_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print(f"[SKIP] No metadata found at top")
            pages_skipped += 1
            print("")
            continue
        
        metadata_block = match.group(0)
        print(f"[OK] Found metadata block at top")
        
        # Remove metadata from top
        content_without_metadata = re.sub(metadata_pattern, '', content, count=1, flags=re.IGNORECASE | re.DOTALL)
        
        # Add horizontal rule and metadata at bottom
        new_content = content_without_metadata.rstrip()
        
        # Check if there's already a horizontal rule at the end
        if not new_content.endswith('</hr>') and not new_content.endswith('<hr />'):
            new_content += '\n<hr />\n'
        
        new_content += '\n' + metadata_block
        
        if DRY_RUN:
            print(f"[DRY RUN] Would update page (version {version} -> {version + 1})")
            pages_updated += 1
        else:
            # Update the page
            try:
                confluence.update_page(
                    page_id=page_id,
                    title=page_title,
                    body=new_content,
                    version_comment="Moved metadata to bottom of page"
                )
                print(f"[OK] Updated page (version {version} -> {version + 1})")
                pages_updated += 1
            except Exception as e:
                print(f"[ERROR] Failed to update page: {e}")
                pages_error += 1
        
        print("")
        
    except Exception as e:
        print(f"[ERROR] Error processing page: {e}")
        pages_error += 1
        print("")

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Total pages processed: {len(all_pages)}")
print(f"Pages updated: {pages_updated}")
print(f"Pages skipped: {pages_skipped}")
print(f"Pages with errors: {pages_error}")
print("")

if DRY_RUN:
    print("[DRY RUN] No actual changes were made.")
    print("Run without -DryRun flag to apply changes.")
else:
    print("[OK] All updates completed!")

print("")
print(f"View in Confluence: {CONFLUENCE_URL}/spaces/{SPACE_KEY}/pages")
"@

# Save and run Python script
$pythonScript | Out-File -FilePath "temp_fix_metadata.py" -Encoding UTF8

try {
    python temp_fix_metadata.py
} finally {
    # Clean up temp file
    if (Test-Path "temp_fix_metadata.py") {
        Remove-Item "temp_fix_metadata.py" -Force
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Script Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

