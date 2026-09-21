param(
    [ValidateSet('bin32','bin64')][string]$Architecture = 'bin32',
    [string]$Client = 'D:\games\aioncl-recette',
    [string]$Diagnostic,
    [switch]$Baseline,
    [switch]$CameraPatch,
    [switch]$RestoreOnly,
    [string]$State
)
$ErrorActionPreference = 'Stop'
$bin = Join-Path $Client $Architecture
$exe = Join-Path $bin 'aionclassic.bin'
$target = Join-Path $bin 'version.dll'
$original = "$target.aioncl-original"
$relay = Join-Path $bin 'aioncl_original.dll'

function Restore-Test {
    $saved = Get-Content -LiteralPath $State -Raw | ConvertFrom-Json
    if ($saved.Completed) { return }
    $startedUtc = [DateTimeOffset]::Parse($saved.StartUtc).UtcDateTime
    # Refuse to stop any process except this experiment's executable and start time.
    Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -eq $exe -and $_.StartTime.ToUniversalTime() -ge $startedUtc -and
        (($_.Id -eq $saved.ProcessId) -or
            (!$saved.ProcessId -and $_.StartTime.ToUniversalTime() -le $startedUtc.AddSeconds(15)))
    } | ForEach-Object { Stop-Process -Id $_.Id -Force; $_.WaitForExit(10000) | Out-Null }
    if ((Get-FileHash -LiteralPath $original).Hash -ne $saved.OriginalHash) {
        throw 'Original DLL hash changed; refusing unverified restoration'
    }
    # Image mappings can remain locked briefly even after process exit.
    for ($attempt = 0; ; ++$attempt) {
        try {
            if ((Get-FileHash -LiteralPath $target).Hash -ne $saved.OriginalHash) {
                Copy-Item -LiteralPath $original -Destination $target -Force
            }
            if (Test-Path -LiteralPath $relay) { Remove-Item -LiteralPath $relay -Force }
            break
        } catch {
            if ($attempt -ge 29) { throw }
            Start-Sleep -Seconds 1
        }
    }
    if ((Get-FileHash -LiteralPath $target).Hash -ne $saved.OriginalHash) { throw 'Restoration hash mismatch' }
    if ($saved.ConfigBackup) {
        if ((Get-FileHash -LiteralPath $saved.ConfigBackup).Hash -ne $saved.ConfigHash) { throw 'Config backup changed' }
        Copy-Item -LiteralPath $saved.ConfigBackup -Destination (Join-Path $Client 'system.cfg') -Force
        if ((Get-FileHash (Join-Path $Client 'system.cfg')).Hash -ne $saved.ConfigHash) { throw 'Config restoration mismatch' }
    }
    $saved | Add-Member -NotePropertyName Completed -NotePropertyValue $true -Force
    $saved | ConvertTo-Json | Set-Content -LiteralPath $State
    'RESTORED original SHA256 verified'
}

if ($RestoreOnly) {
    Start-Sleep -Seconds 165
    Restore-Test
    exit
}
if ((!$Diagnostic -and !$Baseline) -or !$State) { throw 'Diagnostic (or Baseline) and State paths are required' }
if (Test-Path -LiteralPath $State) { throw 'Use a new state path for each experiment' }
if (!(Test-Path -LiteralPath $original)) { throw 'Missing known original DLL' }
if (Test-Path -LiteralPath $relay) { throw 'Relay already exists; investigate prior test first' }
$running = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -like 'aionclassic*' }
if ($running) { throw 'Aion is already running; no files changed' }
$hash = (Get-FileHash -LiteralPath $original).Hash
if ((Get-FileHash -LiteralPath $target).Hash -ne $hash) { throw 'Active DLL differs from original; no files changed' }
if (!$Baseline) {
    $pe = [IO.File]::ReadAllBytes($Diagnostic)
    $offset = [BitConverter]::ToInt32($pe, 0x3c)
    $machine = [BitConverter]::ToUInt16($pe, $offset + 4)
    $expected = if ($Architecture -eq 'bin32') { 0x14c } else { 0x8664 }
    if ($machine -ne $expected) { throw 'Diagnostic architecture mismatch' }
}
$launcherProfile = Get-Content (Join-Path $PSScriptRoot 'launcher.json') -Raw | ConvertFrom-Json
$server = Get-Content (Join-Path $PSScriptRoot 'server-config.json') -Raw | ConvertFrom-Json
$ip = [Net.Dns]::GetHostAddresses($server.loginHost) | Where-Object { $_.AddressFamily -eq 'InterNetwork' } | Select-Object -First 1
if (!$ip) { throw 'No IPv4 address for the configured AionCL server' }
$arguments = $launcherProfile.launchArguments.Replace('{ip}', $ip.IPAddressToString).Replace('{port}', [string]$server.loginPort)
$start = [datetime]::UtcNow
$testState = @{ StartUtc = $start.ToString('o'); OriginalHash = $hash; ProcessId = 0; Completed = $false }
if ($CameraPatch) {
    $cfg = Join-Path $Client 'system.cfg'
    if (!(Test-Path -LiteralPath $cfg)) { throw 'Camera test requires an existing system.cfg to back up' }
    $testState.ConfigBackup = "$State.system.cfg"
    Copy-Item -LiteralPath $cfg -Destination $testState.ConfigBackup
    $testState.ConfigHash = (Get-FileHash -LiteralPath $cfg).Hash
}
$testState | ConvertTo-Json | Set-Content -LiteralPath $State
$watchArgs = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -RestoreOnly -Architecture {1} -Client "{2}" -State "{3}"' -f $PSCommandPath,$Architecture,$Client,$State
$watchdog = Start-Process powershell.exe -ArgumentList $watchArgs -WindowStyle Hidden -PassThru
try {
    if (!$Baseline) {
        Copy-Item -LiteralPath $original -Destination $relay
        Copy-Item -LiteralPath $Diagnostic -Destination $target -Force
    }
    $launch = New-Object System.Diagnostics.ProcessStartInfo
    $launch.FileName = $exe
    $launch.WorkingDirectory = $bin
    $launch.Arguments = $arguments
    $launch.UseShellExecute = $false
    $launch.EnvironmentVariables.Remove('AIONCL_CAMERA_TEST')
    if ($CameraPatch) { $launch.EnvironmentVariables['AIONCL_CAMERA_TEST'] = '1' }
    $process = [Diagnostics.Process]::Start($launch)
    $testState.ProcessId = $process.Id
    $testState | ConvertTo-Json | Set-Content -LiteralPath $State
    "STARTED architecture=$Architecture pid=$($process.Id) baseline=$Baseline"
    $log = Join-Path $bin "aioncl-camera-$($process.Id).log"
    $end = [datetime]::UtcNow.AddSeconds(130)
    do {
        Start-Sleep -Seconds 2
        $process.Refresh()
        if ($process.HasExited) { "EXIT code=$($process.ExitCode)"; break }
        if ((Test-Path $log) -and (Select-String -LiteralPath $log -Pattern '^complete=1$' -Quiet)) { break }
    } while ([datetime]::UtcNow -lt $end)
    "ALIVE=$(!$process.HasExited) LOG=$log"
    if (Test-Path $log) { Get-Content -LiteralPath $log }
    if ($CameraPatch -and (!(Test-Path $log) -or
        !(Select-String -LiteralPath $log -Pattern '^patch_test applied=1 restored=1$' -Quiet))) {
        throw 'Camera apply/rollback validation failed; inspect diagnostic log'
    }
    # Exclude event message bodies: they can include unrelated process arguments.
    Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=$start.ToLocalTime(); Id=1000} -ErrorAction SilentlyContinue |
        ForEach-Object {
            if ($_.Properties[0].Value -like 'aionclassic*') {
                "CRASH app=$($_.Properties[0].Value) module=$($_.Properties[3].Value) code=$($_.Properties[6].Value)"
            }
        }
} finally {
    Restore-Test
    if (!$watchdog.HasExited) { Stop-Process -Id $watchdog.Id -Force }
}
