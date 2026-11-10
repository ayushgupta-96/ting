# Unregister Toing Backend Service from Windows Task Scheduler
$taskName = "ToingBackendService"
try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
    Write-Host "SUCCESS: '$taskName' removed from Windows Task Scheduler." -ForegroundColor Green
} catch {
    Write-Host "Task '$taskName' was not found or already removed." -ForegroundColor Yellow
}
