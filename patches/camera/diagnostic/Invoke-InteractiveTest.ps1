param(
    [ValidateSet('bin32','bin64')][string]$Architecture = 'bin32',
    [string]$Diagnostic,
    [switch]$Baseline,
    [Parameter(Mandatory=$true)][string]$RunDirectory
)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $RunDirectory) { throw 'RunDirectory must be new' }
New-Item -ItemType Directory -Path $RunDirectory | Out-Null
$user = (Get-CimInstance Win32_ComputerSystem).UserName
if (!$user) { throw 'No interactive user session' }
$taskName = 'AionCL-Camera-' + [guid]::NewGuid().ToString('N')
$script = Join-Path $PSScriptRoot 'Test-Startup.ps1'
$output = Join-Path $RunDirectory 'result.txt'
$state = Join-Path $RunDirectory 'state.json'
foreach ($path in @($script,$output,$state,$Diagnostic)) {
    if ($path -match "['`r`n]") { throw 'Unsupported character in test path' }
}
$mode = if ($Baseline) { '-Baseline' } else { "-Diagnostic '$Diagnostic'" }
$command = "try { & '$script' -Architecture $Architecture $mode -State '$state' *> '$output'; exit 0 } catch { `$_.Exception.Message | Out-File -Append '$output'; exit 1 }"
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded"
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal -Settings $settings | Out-Null
    Start-ScheduledTask -TaskName $taskName
    $deadline = [datetime]::UtcNow.AddMinutes(3)
    do {
        Start-Sleep -Seconds 3
        $task = Get-ScheduledTask -TaskName $taskName
        $info = Get-ScheduledTaskInfo -TaskName $taskName
        if ($task.State -ne 'Running' -and $info.LastRunTime.Year -gt 2000) { break }
    } while ([datetime]::UtcNow -lt $deadline)
    "TASK state=$($task.State) result=$($info.LastTaskResult)"
    if (Test-Path -LiteralPath $output) { Get-Content -LiteralPath $output }
    if ($task.State -eq 'Running') { throw 'Test still running; watchdog restoration remains armed' }
    if ($info.LastTaskResult -ne 0) { throw 'Interactive test failed; inspect result and restoration' }
} finally {
    if ((Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue).State -ne 'Running') {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    }
}
