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

# Group by object and date
Write-Host "Breakdown by Object and Date:`n"

# Get unique objects
$objects = $jobs | Select-Object -ExpandProperty object -Unique | Sort-Object

foreach ($obj in $objects) {
    $objJobs = $jobs | Where-Object { $_.object -eq $obj }
    Write-Host "  $obj ($($objJobs.Count) jobs)"
    
    # Get dates for this object
    $dates = $objJobs | ForEach-Object {
        $createdUTC = [datetime]::Parse($_.createdDate)
        $createdEST = $createdUTC.AddHours(-5)
        $createdEST.Date
    } | Select-Object -Unique | Sort-Object -Descending | Select-Object -First 5
    
    foreach ($date in $dates) {
        $dateJobs = $objJobs | Where-Object {
            $createdUTC = [datetime]::Parse($_.createdDate)
            $createdEST = $createdUTC.AddHours(-5)
            $createdEST.Date -eq $date
        }
        Write-Host "      $($date.ToString('yyyy-MM-dd')): $($dateJobs.Count) jobs"
    }
    Write-Host ""
}

# Show the 10 most recent jobs
Write-Host "`nMost Recent 10 Jobs:"
$recentJobs = $jobs | Sort-Object createdDate -Descending | Select-Object -First 10

foreach ($job in $recentJobs) {
    $createdUTC = [datetime]::Parse($job.createdDate)
    $createdEST = $createdUTC.AddHours(-5)
    
    Write-Host "  $($job.id) - $($job.object) - $($job.operation) - $($createdEST.ToString('yyyy-MM-dd hh:mm tt')) EST"
}



























































