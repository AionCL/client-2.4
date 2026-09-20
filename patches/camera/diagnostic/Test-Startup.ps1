param(
    [ValidateSet('bin32','bin64')][string]$Architecture = 'bin32',
    [string]$Client = 'D:\games\aioncl-recette',
    [string]$Diagnostic,
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
    # Refuse to stop any process except this experiment's executable and start time.
    Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -eq $exe -and $_.StartTime.ToUniversalTime() -ge [datetime]$saved.StartUtc
    } | ForEach-Object { Stop-Process -Id $_.Id -Force; $_.WaitForExit(10000) | Out-Null }
    if ((Get-FileHash -LiteralPath $original).Hash -ne $saved.OriginalHash) {
        throw 'Original DLL hash changed; refusing unverified restoration'
    }
    Copy-Item -LiteralPath $original -Destination $target -Force
    if ((Get-FileHash -LiteralPath $target).Hash -ne $saved.OriginalHash) { throw 'Restoration hash mismatch' }
    if (Test-Path -LiteralPath $relay) { Remove-Item -LiteralPath $relay -Force }
    'RESTORED original SHA256 verified'
}

if ($RestoreOnly) {
    Start-Sleep -Seconds 110
    Restore-Test
    exit
}
if (!$Diagnostic -or !$State) { throw 'Diagnostic and State paths are required' }
if (Test-Path -LiteralPath $State) { throw 'Use a new state path for each experiment' }
if (!(Test-Path -LiteralPath $original)) { throw 'Missing known original DLL' }
if (Test-Path -LiteralPath $relay) { throw 'Relay already exists; investigate prior test first' }
$running = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -like 'aionclassic*' }
if ($running) { throw 'Aion is already running; no files changed' }
$hash = (Get-FileHash -LiteralPath $original).Hash
if ((Get-FileHash -LiteralPath $target).Hash -ne $hash) { throw 'Active DLL differs from original; no files changed' }
$pe = [IO.File]::ReadAllBytes($Diagnostic)
$offset = [BitConverter]::ToInt32($pe, 0x3c)
$machine = [BitConverter]::ToUInt16($pe, $offset + 4)
$expected = if ($Architecture -eq 'bin32') { 0x14c } else { 0x8664 }
if ($machine -ne $expected) { throw 'Diagnostic architecture mismatch' }
$start = [datetime]::UtcNow
@{ StartUtc = $start.ToString('o'); OriginalHash = $hash } | ConvertTo-Json | Set-Content -LiteralPath $State
$watchArgs = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -RestoreOnly -Architecture {1} -Client "{2}" -State "{3}"' -f $PSCommandPath,$Architecture,$Client,$State
$watchdog = Start-Process powershell.exe -ArgumentList $watchArgs -WindowStyle Hidden -PassThru
try {
    Copy-Item -LiteralPath $original -Destination $relay
    Copy-Item -LiteralPath $Diagnostic -Destination $target -Force
    $launch = New-Object System.Diagnostics.ProcessStartInfo
    $launch.FileName = $exe
    $launch.WorkingDirectory = $bin
    $launch.Arguments = '-DEVMODE'
    $launch.UseShellExecute = $false
    $process = [Diagnostics.Process]::Start($launch)
    "STARTED architecture=$Architecture pid=$($process.Id)"
    $log = Join-Path $bin "aioncl-camera-$($process.Id).log"
    $end = [datetime]::UtcNow.AddSeconds(85)
    do {
        Start-Sleep -Seconds 2
        $process.Refresh()
        if ($process.HasExited) { "EXIT code=$($process.ExitCode)"; break }
        if ((Test-Path $log) -and (Select-String -LiteralPath $log -Pattern '^complete=1$' -Quiet)) { break }
    } while ([datetime]::UtcNow -lt $end)
    "ALIVE=$(!$process.HasExited) LOG=$log"
    if (Test-Path $log) { Get-Content -LiteralPath $log }
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
