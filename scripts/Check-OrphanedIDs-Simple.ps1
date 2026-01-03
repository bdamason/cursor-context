# Simple script to check if failed External IDs exist in Salesforce
param(
    [string]$OrgUsername = "benjamin.mason@eso.com"
)

Write-Host "Checking orphaned External IDs..." -ForegroundColor Cyan

# Auth
$authJson = sf org display --target-org $OrgUsername --json | ConvertFrom-Json
$token = $authJson.result.accessToken
$instance = $authJson.result.instanceUrl

$headers = @{ 
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json" 
}

# Get recent jobs
$response = Invoke-RestMethod -Uri "$instance/services/data/v65.0/jobs/ingest" -Headers $headers
$accountJobs = $response.records | Where-Object { 
    $_.object -eq 'Account' -and $_.operation -eq 'upsert' 
} | Select-Object -First 10

# Check each job for failures
$orphanedIds = @()

foreach ($job in $accountJobs) {
    $detail = Invoke-RestMethod -Uri "$instance/services/data/v65.0/jobs/ingest/$($job.id)" -Headers $headers
    
    if ($detail.numberRecordsFailed -gt 0) {
        Write-Host "Job $($job.id): $($detail.numberRecordsFailed) failures" -ForegroundColor Yellow
        
        # Get failed records
        $failedHeaders = @{ 
            "Authorization" = "Bearer $token"
            "Accept" = "text/csv"
        }
        $csv = Invoke-RestMethod -Uri "$instance/services/data/v65.0/jobs/ingest/$($job.id)/failedResults" -Headers $failedHeaders
        
        # Parse CSV to get External IDs
        $lines = $csv -split "`n"
        for ($i = 1; $i -lt $lines.Count; $i++) {
            if ($lines[$i].Trim() -eq "") { continue }
            $values = $lines[$i] -split ','
            $extId = $values[2].Trim('"')
            
            if ($extId -ne "" -and $orphanedIds -notcontains $extId) {
                # Check if exists in Salesforce
                $soql = "SELECT Id FROM Account WHERE ESO_Internal_ID__c = '$extId'"
                $encodedQuery = [System.Web.HttpUtility]::UrlEncode($soql)
                $sfResult = Invoke-RestMethod -Uri "$instance/services/data/v65.0/query?q=$encodedQuery" -Headers $headers
                
                if ($sfResult.totalSize -eq 0) {
                    Write-Host "  ❌ $extId - NOT in Salesforce (ORPHANED)" -ForegroundColor Red
                    $orphanedIds += $extId
                } else {
                    Write-Host "  ⚠️ $extId - EXISTS in Salesforce (different error)" -ForegroundColor Yellow
                }
            }
        }
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Total Orphaned IDs: $($orphanedIds.Count)" -ForegroundColor $(if ($orphanedIds.Count -gt 0) { "Red" } else { "Green" })

if ($orphanedIds.Count -gt 0) {
    Write-Host ""
    Write-Host "Orphaned External IDs:" -ForegroundColor Red
    $orphanedIds | ForEach-Object { Write-Host "  $_" }
    
    # Save to file
    $orphanedIds | Out-File "C:\cursor_repo\orphaned_ids.txt"
    Write-Host ""
    Write-Host "Saved to: C:\cursor_repo\orphaned_ids.txt" -ForegroundColor Gray
}



