# Monitor Salesforce Bulk API Jobs
# Usage: .\Monitor-BulkAPIJobs.ps1 -OrgUsername "sfdc@eso.com" -HoursBack 1

param(
    [Parameter(Mandatory=$false)]
    [string]$OrgUsername = "sfdc@eso.com",
    
    [Parameter(Mandatory=$false)]
    [int]$HoursBack = 24,
    
    [Parameter(Mandatory=$false)]
    [switch]$DownloadFailedRecords,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "C:\cursor_repo\bulk_api_reports"
)

Write-Host "🔍 Monitoring Bulk API v2 Jobs..." -ForegroundColor Cyan
Write-Host "Org: $OrgUsername" -ForegroundColor Gray
Write-Host "Looking back: $HoursBack hours" -ForegroundColor Gray
Write-Host ""

# Create output directory if it doesn't exist
if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath | Out-Null
}

# Get Salesforce auth
Write-Host "Authenticating..." -ForegroundColor Yellow
try {
    $authJson = sf org display --target-org $OrgUsername --json | ConvertFrom-Json
    $token = $authJson.result.accessToken
    $instance = $authJson.result.instanceUrl
    Write-Host "✓ Connected to $instance" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to authenticate. Make sure you're logged in:" -ForegroundColor Red
    Write-Host "  sf org login web --alias $OrgUsername" -ForegroundColor Yellow
    exit 1
}

# Query Bulk API jobs
Write-Host ""
Write-Host "Fetching Bulk API v2 jobs..." -ForegroundColor Yellow
$headers = @{ 
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json" 
}

try {
    $response = Invoke-RestMethod -Uri "$instance/services/data/v65.0/jobs/ingest" -Headers $headers -Method Get
    $allJobs = $response.records
} catch {
    Write-Host "✗ Failed to fetch jobs: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Filter to Account upserts in time window
$cutoffTime = (Get-Date).AddHours(-$HoursBack)
$accountJobs = $allJobs | Where-Object { 
    $_.object -eq 'Account' -and 
    $_.operation -eq 'upsert' -and
    $_.jobType -eq 'V2Ingest' -and
    [DateTime]$_.createdDate -gt $cutoffTime
} | Sort-Object createdDate -Descending

Write-Host "✓ Found $($accountJobs.Count) Account upsert jobs" -ForegroundColor Green

if ($accountJobs.Count -eq 0) {
    Write-Host "No Account upsert jobs found in the last $HoursBack hours." -ForegroundColor Yellow
    exit 0
}

# Get detailed stats for each job
Write-Host ""
Write-Host "Analyzing jobs..." -ForegroundColor Yellow

$jobDetails = @()
$totalFailed = 0
$totalProcessed = 0

foreach ($job in $accountJobs) {
    try {
        $detail = Invoke-RestMethod -Uri "$instance/services/data/v65.0/jobs/ingest/$($job.id)" -Headers $headers -Method Get
        
        $jobDetails += [PSCustomObject]@{
            JobId = $job.id
            CreatedDate = $job.createdDate
            State = $detail.state
            RecordsProcessed = $detail.numberRecordsProcessed
            RecordsFailed = $detail.numberRecordsFailed
            ProcessingTime = "$([Math]::Round($detail.totalProcessingTime / 1000, 2))s"
            FailureRate = if ($detail.numberRecordsProcessed -gt 0) { 
                "$([Math]::Round(($detail.numberRecordsFailed / $detail.numberRecordsProcessed) * 100, 2))%"
            } else { "0%" }
        }
        
        $totalFailed += $detail.numberRecordsFailed
        $totalProcessed += $detail.numberRecordsProcessed
    } catch {
        Write-Host "  ⚠ Could not fetch details for job $($job.id)" -ForegroundColor Yellow
    }
}

# Display summary table
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "                    BULK API JOB SUMMARY" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
$jobDetails | Format-Table -AutoSize

# Overall statistics
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "                    OVERALL STATISTICS" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Total Jobs:       $($jobDetails.Count)"
Write-Host "Total Processed:  $totalProcessed records"
Write-Host "Total Failed:     $totalFailed records" -ForegroundColor $(if ($totalFailed -gt 0) { "Red" } else { "Green" })
Write-Host "Overall Variance: $([Math]::Round(($totalFailed / $totalProcessed) * 100, 4))%" -ForegroundColor $(if ($totalFailed -gt 0) { "Red" } else { "Green" })

# Alert if failures detected
if ($totalFailed -gt 0) {
    Write-Host ""
    Write-Host "🚨 ALERT: $totalFailed record(s) failed!" -ForegroundColor Red
    Write-Host ""
    
    $failedJobs = $jobDetails | Where-Object { $_.RecordsFailed -gt 0 }
    Write-Host "Jobs with failures:" -ForegroundColor Yellow
    $failedJobs | Format-Table JobId, CreatedDate, RecordsFailed -AutoSize
    
    # Download failed records if requested
    if ($DownloadFailedRecords) {
        Write-Host ""
        Write-Host "Downloading failed records..." -ForegroundColor Yellow
        
        foreach ($failedJob in $failedJobs) {
            $failedRecordsPath = Join-Path $OutputPath "failed_records_$($failedJob.JobId).csv"
            
            try {
                $failedHeaders = @{ 
                    "Authorization" = "Bearer $token"
                    "Accept" = "text/csv"
                }
                $failedCsv = Invoke-RestMethod -Uri "$instance/services/data/v65.0/jobs/ingest/$($failedJob.JobId)/failedResults" -Headers $failedHeaders -Method Get
                $failedCsv | Out-File -FilePath $failedRecordsPath -Encoding utf8
                Write-Host "  ✓ Saved failed records to: $failedRecordsPath" -ForegroundColor Green
            } catch {
                Write-Host "  ✗ Could not download failed records for job $($failedJob.JobId)" -ForegroundColor Red
            }
        }
    } else {
        Write-Host ""
        Write-Host "💡 Tip: Run with -DownloadFailedRecords to download failure details" -ForegroundColor Cyan
    }
} else {
    Write-Host ""
    Write-Host "✅ All records processed successfully!" -ForegroundColor Green
}

# Save report
$reportPath = Join-Path $OutputPath "bulk_api_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$jobDetails | ConvertTo-Json | Out-File -FilePath $reportPath -Encoding utf8
Write-Host ""
Write-Host "📊 Report saved to: $reportPath" -ForegroundColor Gray

# Return exit code based on failures
if ($totalFailed -gt 0) {
    exit 1
} else {
    exit 0
}



