# Automated Windows Task Scheduler Setup for Toing Backend & Tunnel
$taskName = "ToingBackendService"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbsPath = Join-Path $scriptDir "run_silent.vbs"

Write-Host "Registering '$taskName' in Windows Task Scheduler..." -ForegroundColor Cyan

$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbsPath`"" -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 10 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force
    Write-Host "SUCCESS: '$taskName' registered successfully!" -ForegroundColor Green
    Write-Host "It will now start automatically whenever your laptop logs in." -ForegroundColor Yellow
} catch {
    Write-Host "ERROR: Failed to register task: $_" -ForegroundColor Red
}
