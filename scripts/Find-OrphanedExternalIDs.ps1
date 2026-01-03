# Find Orphaned External IDs in Bulk API Failures
# This script downloads failed records from Bulk API and checks if they exist in Salesforce

param(
    [Parameter(Mandatory=$false)]
    [string]$OrgUsername = "benjamin.mason@eso.com",
    
    [Parameter(Mandatory=$false)]
    [int]$HoursBack = 168, # 1 week default
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "C:\cursor_repo\orphaned_ids_report"
)

Write-Host "🔍 Finding Orphaned External IDs..." -ForegroundColor Cyan
Write-Host ""

# Create output directory
if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath | Out-Null
}

# Authenticate
Write-Host "Authenticating..." -ForegroundColor Yellow
try {
    $authJson = sf org display --target-org $OrgUsername --json | ConvertFrom-Json
    $token = $authJson.result.accessToken
    $instance = $authJson.result.instanceUrl
    Write-Host "✓ Connected to $instance" -ForegroundColor Green
}
catch {
    Write-Host "✗ Failed to authenticate" -ForegroundColor Red
    exit 1
}

# Get Bulk API jobs
Write-Host ""
Write-Host "Fetching Bulk API jobs..." -ForegroundColor Yellow
$headers = @{ 
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json" 
}

$response = Invoke-RestMethod -Uri "$instance/services/data/v65.0/jobs/ingest" -Headers $headers -Method Get
$cutoffTime = (Get-Date).AddHours(-$HoursBack)

$accountJobs = $response.records | Where-Object { 
    $_.object -eq 'Account' -and 
    $_.operation -eq 'upsert' -and
    $_.jobType -eq 'V2Ingest' -and
    [DateTime]$_.createdDate -gt $cutoffTime
} | Sort-Object createdDate -Descending

Write-Host "✓ Found $($accountJobs.Count) jobs" -ForegroundColor Green

# Get job details and find failures
$failedJobs = @()
foreach ($job in $accountJobs) {
    $detail = Invoke-RestMethod -Uri "$instance/services/data/v65.0/jobs/ingest/$($job.id)" -Headers $headers -Method Get
    if ($detail.numberRecordsFailed -gt 0) {
        $failedJobs += [PSCustomObject]@{
            JobId = $job.id
            CreatedDate = $job.createdDate
            Failed = $detail.numberRecordsFailed
            Processed = $detail.numberRecordsProcessed
        }
    }
}

Write-Host "Found $($failedJobs.Count) jobs with failures" -ForegroundColor $(if ($failedJobs.Count -gt 0) { "Yellow" } else { "Green" })

if ($failedJobs.Count -eq 0) {
    Write-Host ""
    Write-Host "✅ No failures found!" -ForegroundColor Green
    exit 0
}

# Download failed records
Write-Host ""
Write-Host "Downloading failed records..." -ForegroundColor Yellow

$allFailedRecords = @()
foreach ($job in $failedJobs) {
    try {
        $failedHeaders = @{ 
            "Authorization" = "Bearer $token"
            "Accept" = "text/csv"
        }
        $csv = Invoke-RestMethod -Uri "$instance/services/data/v65.0/jobs/ingest/$($job.JobId)/failedResults" -Headers $failedHeaders -Method Get
        
        # Parse CSV
        $lines = $csv -split "`n"
        $headers_line = $lines[0] -split ','
        
        for ($i = 1; $i -lt $lines.Count; $i++) {
            if ($lines[$i].Trim() -eq "") { continue }
            
            $values = $lines[$i] -split ','
            $record = [PSCustomObject]@{
                JobId = $job.JobId
                JobDate = $job.CreatedDate
                ESO_Internal_ID = $values[2].Trim('"')
                Error = $values[1].Trim('"')
            }
            $allFailedRecords += $record
        }
        
        Write-Host "  ✓ Job $($job.JobId): $($job.Failed) failed records" -ForegroundColor Gray
    }
    catch {
        Write-Host "  ✗ Could not download failed records for job $($job.JobId)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Total failed records: $($allFailedRecords.Count)" -ForegroundColor Yellow

# Get unique External IDs
$uniqueExternalIds = $allFailedRecords | Select-Object -ExpandProperty ESO_Internal_ID -Unique | Sort-Object

Write-Host "Unique External IDs: $($uniqueExternalIds.Count)" -ForegroundColor Yellow
Write-Host ""

# Check if each External ID exists in Salesforce
Write-Host "Checking if External IDs exist in Salesforce..." -ForegroundColor Yellow

$orphanedIds = @()
$existingIds = @()

foreach ($extId in $uniqueExternalIds) {
    if ($extId -eq "" -or $extId -eq $null) { continue }
    
    try {
        # Query Salesforce
        $soqlQuery = "SELECT Id, Name FROM Account WHERE ESO_Internal_ID__c = '$extId'"
        $encodedQuery = [System.Web.HttpUtility]::UrlEncode($soqlQuery)
        $sfResult = Invoke-RestMethod -Uri "$instance/services/data/v65.0/query?q=$encodedQuery" -Headers $headers -Method Get
        
        if ($sfResult.totalSize -eq 0) {
            # Does NOT exist in Salesforce
            $orphanedIds += [PSCustomObject]@{
                ESO_Internal_ID = $extId
                ExistsInSalesforce = $false
                FailureCount = ($allFailedRecords | Where-Object { $_.ESO_Internal_ID -eq $extId }).Count
            }
            Write-Host "  ❌ $extId - NOT FOUND in Salesforce" -ForegroundColor Red
        } else {
            # EXISTS in Salesforce (shouldn't fail!)
            $existingIds += [PSCustomObject]@{
                ESO_Internal_ID = $extId
                ExistsInSalesforce = $true
                SalesforceId = $sfResult.records[0].Id
                SalesforceName = $sfResult.records[0].Name
                FailureCount = ($allFailedRecords | Where-Object { $_.ESO_Internal_ID -eq $extId }).Count
            }
            Write-Host "  ⚠️ $extId - EXISTS in Salesforce (different issue!)" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "  ⚠️ $extId - Error checking: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Summary Report
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "                    ORPHANED IDS REPORT" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total Failed Records:    $($allFailedRecords.Count)"
Write-Host "Unique External IDs:     $($uniqueExternalIds.Count)"
Write-Host "Orphaned IDs (not in SF): $($orphanedIds.Count)" -ForegroundColor Red
Write-Host "Existing IDs (in SF):     $($existingIds.Count)" -ForegroundColor Yellow

if ($orphanedIds.Count -gt 0) {
    Write-Host ""
    Write-Host "🚨 ORPHANED EXTERNAL IDs (DO NOT EXIST IN SALESFORCE):" -ForegroundColor Red
    $orphanedIds | Format-Table -AutoSize
    
    # Save to file
    $orphanedPath = Join-Path $OutputPath "orphaned_external_ids.csv"
    $orphanedIds | Export-Csv -Path $orphanedPath -NoTypeInformation
    Write-Host "💾 Saved to: $orphanedPath" -ForegroundColor Gray
}

if ($existingIds.Count -gt 0) {
    Write-Host ""
    Write-Host "⚠️ IDs THAT EXIST IN SALESFORCE BUT STILL FAILED:" -ForegroundColor Yellow
    Write-Host "(This indicates a different issue - possibly FLS, validation rules, triggers)" -ForegroundColor Gray
    $existingIds | Format-Table ESO_Internal_ID, SalesforceName, FailureCount -AutoSize
    
    # Save to file
    $existingPath = Join-Path $OutputPath "existing_but_failed_ids.csv"
    $existingIds | Export-Csv -Path $existingPath -NoTypeInformation
    Write-Host "💾 Saved to: $existingPath" -ForegroundColor Gray
}

# Save full report
Write-Host ""
$reportPath = Join-Path $OutputPath "full_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$report = @{
    GeneratedDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    TimeRangeHours = $HoursBack
    TotalFailedRecords = $allFailedRecords.Count
    UniqueExternalIds = $uniqueExternalIds.Count
    OrphanedIds = $orphanedIds
    ExistingIds = $existingIds
    AllFailedRecords = $allFailedRecords
}
$report | ConvertTo-Json -Depth 10 | Out-File -FilePath $reportPath -Encoding utf8
Write-Host "📊 Full report saved to: $reportPath" -ForegroundColor Gray

# Recommendations
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "                    RECOMMENDATIONS" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan

if ($orphanedIds.Count -gt 0) {
    Write-Host ""
    Write-Host "🔴 ACTION REQUIRED: Orphaned External IDs found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Your SQL view contains External IDs that don't exist in Salesforce." -ForegroundColor Yellow
    Write-Host "This causes the upsert to try INSERT (which fails)." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor White
    Write-Host "1. Investigate why these IDs are in your SQL view" -ForegroundColor White
    Write-Host "2. Check if these records were deleted from Salesforce" -ForegroundColor White
    Write-Host "3. Add filtering to exclude orphaned IDs from the sync" -ForegroundColor White
    Write-Host "4. See DW2SF_REAL_ROOT_CAUSE.md for detailed solutions" -ForegroundColor White
}

if ($existingIds.Count -gt 0) {
    Write-Host ""
    Write-Host "🟡 WARNING: Some IDs exist in Salesforce but still failed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "This indicates a different issue (not orphaned IDs):" -ForegroundColor Gray
    Write-Host "- Field-level security" -ForegroundColor Gray
    Write-Host "- Validation rules" -ForegroundColor Gray
    Write-Host "- Record locking" -ForegroundColor Gray
    Write-Host "- Triggers" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Check the Error column in existing_but_failed_ids.csv" -ForegroundColor White
}

Write-Host ""

