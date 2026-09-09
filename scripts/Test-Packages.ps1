#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ManifestPath,
    [switch]$Deep
)
. "$PSScriptRoot/Common.ps1"
$ManifestPath = (Get-Item -LiteralPath $ManifestPath).FullName
$directory = Split-Path -Parent $ManifestPath
$m = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($m.formatVersion -ne 1 -or $m.product -ne 'AionCL' -or $m.gameVersion -ne '2.4' -or $m.archiveFormat -ne 'zip' -or
    $m.clientVersion -notmatch '^2\.4\.\d+(?:-[a-zA-Z0-9.-]+)?$' -or $m.buildId -notmatch '^[a-f0-9]{64}$' -or
    $m.maxPackageBytes -lt 65536 -or $m.maxPackageBytes -ge 2GB -or @($m.packages).Count -eq 0 -or @($m.packages).Count -gt 998) { throw 'Invalid manifest header.' }
$expectedSums = @{}
foreach ($line in [IO.File]::ReadAllLines((Join-Path $directory 'SHA256SUMS'))) {
    if ($line -notmatch '^([a-f0-9]{64})  ([^/\\]+)$') { throw 'Invalid SHA256SUMS line.' }
    if ($expectedSums.ContainsKey($Matches[2])) { throw 'Duplicate checksum entry.' }
    $expectedSums[$Matches[2]] = $Matches[1]
}
if ($expectedSums.Count -ne @($m.packages).Count + 1 -or $expectedSums['install-manifest.json'] -ne (Get-Sha256 $ManifestPath)) { throw 'Manifest checksum mismatch.' }
$allPaths = @{}
$names = @{}
[long]$totalSize = 0; [long]$totalSource = 0; [long]$totalCount = 0
$index = 0
foreach ($package in $m.packages) {
    $index++
    if ($package.name -notmatch '^aioncl-client-2\.4\.\d+(?:-[a-zA-Z0-9.-]+)?-\d{3}\.zip$' -or $names.ContainsKey($package.name)) { throw 'Invalid or duplicate package name.' }
    $names[$package.name] = $true
    foreach ($url in $package.mirrors) { Assert-PublicBaseUrl $url }
    if ($package.size -lt 0 -or $package.size -gt $m.maxPackageBytes -or $package.sha256 -notmatch '^[a-f0-9]{64}$') { throw 'Invalid package metadata.' }
    $path = Join-Path $directory $package.name
    if ((Get-Item -LiteralPath $path).Length -ne $package.size -or (Get-Sha256 $path) -ne $package.sha256 -or
        $expectedSums[$package.name] -ne $package.sha256) { throw "Package checksum/size mismatch: $($package.name)" }
    $files = @{}
    [long]$sourceBytes = 0
    foreach ($file in $package.files) {
        Assert-RelativePath $file.path
        if ($allPaths.ContainsKey($file.path) -or $file.size -lt 0 -or $file.sha256 -notmatch '^[a-f0-9]{64}$') { throw "Invalid or duplicate file: $($file.path)" }
        $allPaths[$file.path] = $true; $files[$file.path] = $file
        $sourceBytes += $file.size
    }
    if ($files.Count -ne $package.fileCount -or $sourceBytes -ne $package.uncompressedSize) { throw 'Package totals mismatch.' }
    if ($Deep) {
        Write-Host "Checking archive contents: $($package.name)"
        $zip = [IO.Compression.ZipFile]::OpenRead($path)
        try {
            if ($zip.Entries.Count -ne $files.Count) { throw 'Archive entry count mismatch.' }
            $seen = @{}
            foreach ($entry in $zip.Entries) {
                Assert-RelativePath $entry.FullName
                if (!$files.ContainsKey($entry.FullName) -or $seen.ContainsKey($entry.FullName)) { throw 'Unexpected or duplicate ZIP entry.' }
                $seen[$entry.FullName] = $true
                $file = $files[$entry.FullName]
                if ($entry.FullName -cne $file.path -or $entry.Length -ne $file.size) { throw 'ZIP path/size mismatch.' }
                $content = $entry.Open()
                try { if ((Get-StreamHash $content) -ne $file.sha256) { throw "File checksum mismatch: $($file.path)" } }
                finally { $content.Dispose() }
            }
        } finally { $zip.Dispose() }
    }
    $totalSize += $package.size; $totalSource += $sourceBytes; $totalCount += $files.Count
}
$actualZips = @(Get-ChildItem -LiteralPath $directory -Filter '*.zip' -File)
if ($actualZips.Count -ne $names.Count) { throw 'Unexpected ZIP files in output directory.' }
if ($totalSize -ne $m.compressedBytes -or $totalSource -ne $m.sourceBytes -or $totalCount -ne $m.sourceFileCount) { throw 'Manifest totals mismatch.' }
Write-Host "OK: $($names.Count) packages, $totalCount files, $totalSize compressed bytes (Deep=$Deep)."
