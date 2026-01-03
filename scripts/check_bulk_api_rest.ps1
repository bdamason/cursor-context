# Get access token
$orgInfo = sf org display --target-org benjamin.mason@eso.com --json | ConvertFrom-Json
$accessToken = $orgInfo.result.accessToken
$instanceUrl = $orgInfo.result.instanceUrl

Write-Host "Instance: $instanceUrl`n"

# Query Bulk API v2 jobs
$url = "$instanceUrl/services/data/v62.0/jobs/ingest"
$headers = @{
    "Authorization" = "Bearer $accessToken"
    "Content-Type" = "application/json"
}

Write-Host "Querying Bulk API v2 jobs..."
$response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get

$jobs = $response.records

Write-Host "Found $($jobs.Count) total Bulk API v2 jobs`n"

# Filter for Nov 21 and Account object
$nov21Jobs = $jobs | Where-Object {
    $_.object -eq 'Account' -and
    $_.createdDate -like '2025-11-21*'
} | Sort-Object createdDate

Write-Host "Found $($nov21Jobs.Count) Account Bulk API jobs on Nov 21:`n"

foreach ($job in $nov21Jobs) {
    # Convert UTC to EST (subtract 5 hours)
    $createdUTC = [datetime]::Parse($job.createdDate)
    $createdEST = $createdUTC.AddHours(-5)
    
    Write-Host "  Job ID: $($job.id)"
    Write-Host "    Object: $($job.object)"
    Write-Host "    Operation: $($job.operation)"
    Write-Host "    State: $($job.state)"
    Write-Host "    Created: $($createdEST.ToString('hh:mm:ss tt')) EST"
    Write-Host "    Records Processed: $($job.numberRecordsProcessed)"
    Write-Host "    Records Failed: $($job.numberRecordsFailed)"
    
    # Highlight jobs around 8:56 AM
    if ($createdEST.Hour -eq 8 -and $createdEST.Minute -ge 50) {
        Write-Host "    *** NEAR 8:56 AM ***" -ForegroundColor Yellow
    }
    
    Write-Host ""
}



























































