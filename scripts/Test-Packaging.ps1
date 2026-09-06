#requires -Version 5.1
[CmdletBinding()]
param()
. "$PSScriptRoot/Common.ps1"
$testRoot = Join-Path $PSScriptRoot ('../.local/test-' + [Guid]::NewGuid().ToString('N'))
$source = Join-Path $testRoot 'source'
[IO.Directory]::CreateDirectory((Join-Path $source 'sub')) | Out-Null
$data = New-Object byte[] 50000
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($data) } finally { $rng.Dispose() }
[IO.File]::WriteAllBytes((Join-Path $source 'one.dat'), $data)
[IO.File]::WriteAllBytes((Join-Path $source 'sub/two.dat'), $data)
[IO.File]::WriteAllText((Join-Path $source ('sub/unicode-' + [char]0xe9 + '.txt')), 'AionCL')
[IO.File]::WriteAllText((Join-Path $source 'empty'), '')
[IO.File]::WriteAllText((Join-Path $source 'excluded.log'), 'excluded')
$configPath = Join-Path $testRoot 'config.json'
Write-Json ([ordered]@{clientVersion = '2.4.0'; maxPackageBytes = 125000; exclude = @('*.log')}) $configPath
$outA = Join-Path $testRoot 'a'
$outB = Join-Path $testRoot 'b'
function Assert-Fails([scriptblock]$Action, [string]$ExpectedMessage) {
    $failed = $false
    try { & $Action } catch {
        if ($_.Exception.Message -notlike $ExpectedMessage) { throw }
        $failed = $true
    }
    if (!$failed) { throw "Expected failure: $ExpectedMessage" }
}
& "$PSScriptRoot/Build-Packages.ps1" -SourcePath $source -OutputRoot $outA -ConfigPath $configPath
$manifestPath = Join-Path $outA 'v2.4.0/install-manifest.json'
$m = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($m.packages.Count -ne 2 -or $m.sourceFileCount -ne 4) { throw 'Splitting/exclusion test failed.' }
$before = (Get-Item $manifestPath).LastWriteTimeUtc
& "$PSScriptRoot/Build-Packages.ps1" -SourcePath $source -OutputRoot $outA -ConfigPath $configPath
if ((Get-Item $manifestPath).LastWriteTimeUtc -ne $before) { throw 'Reuse modified the manifest.' }
& "$PSScriptRoot/Build-Packages.ps1" -SourcePath $source -OutputRoot $outB -ConfigPath $configPath
if ((Get-Sha256 $manifestPath) -ne (Get-Sha256 (Join-Path $outB 'v2.4.0/install-manifest.json'))) { throw 'Reproducibility failed.' }
$zipPath = Join-Path (Split-Path $manifestPath) $m.packages[0].name
$original = [IO.File]::ReadAllBytes($zipPath)
try {
    $changed = $original.Clone(); $changed[20] = $changed[20] -bxor 1
    [IO.File]::WriteAllBytes($zipPath, $changed)
    Assert-Fails { & "$PSScriptRoot/Test-Packages.ps1" -ManifestPath $manifestPath } '*checksum/size mismatch*'
} finally { [IO.File]::WriteAllBytes($zipPath, $original) }
$jsonBytes = [IO.File]::ReadAllBytes($manifestPath)
try {
    [IO.File]::AppendAllText($manifestPath, ' ')
    Assert-Fails { & "$PSScriptRoot/Test-Packages.ps1" -ManifestPath $manifestPath } '*Manifest checksum mismatch*'
} finally { [IO.File]::WriteAllBytes($manifestPath, $jsonBytes) }
$sumsPath = Join-Path (Split-Path $manifestPath) 'SHA256SUMS'
$sumsBytes = [IO.File]::ReadAllBytes($sumsPath)
try {
    # Re-sign only the checksum list to exercise deep verification independently.
    $altered = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $altered.packages[0].files[0].sha256 = '0' * 64
    Write-Json $altered $manifestPath
    $sums = @($altered.packages | ForEach-Object { "$($_.sha256)  $($_.name)" }) + "$(Get-Sha256 $manifestPath)  install-manifest.json"
    [IO.File]::WriteAllText($sumsPath, ($sums -join "`n") + "`n")
    Assert-Fails { & "$PSScriptRoot/Test-Packages.ps1" -ManifestPath $manifestPath -Deep } '*File checksum mismatch*'
} finally {
    [IO.File]::WriteAllBytes($manifestPath, $jsonBytes)
    [IO.File]::WriteAllBytes($sumsPath, $sumsBytes)
}
[IO.File]::WriteAllText((Join-Path $source 'empty'), 'changed')
Assert-Fails { & "$PSScriptRoot/Build-Packages.ps1" -SourcePath $source -OutputRoot $outA -ConfigPath $configPath } '*different inputs*'
Assert-Fails { & "$PSScriptRoot/Build-Packages.ps1" -SourcePath $source -OutputRoot (Join-Path $source 'output') -ConfigPath $configPath } '*non-nested*'
Assert-Fails { Assert-RelativePath '../escape' } '*Unsafe relative path*'
Assert-Fails { Assert-PublicBaseUrl 'https://user:credential@example.org/download' } '*public HTTPS*'
Write-Json ([ordered]@{clientVersion = '2.4.0'; maxPackageBytes = 65536; exclude = @('*.log')}) $configPath
Assert-Fails { & "$PSScriptRoot/Build-Packages.ps1" -SourcePath $source -OutputRoot (Join-Path $testRoot 'oversize') -ConfigPath $configPath } '*File too large*'
Write-Host 'PASS: splitting, Unicode, empty files, exclusions, deep file hashes, reuse, reproducibility, corruption, changed inputs, unsafe paths/URLs and oversized files.'
Write-Host "Test fixtures retained under $testRoot (ignored by Git)."
