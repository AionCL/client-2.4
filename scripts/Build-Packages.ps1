#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SourcePath,
    [string]$OutputRoot = (Join-Path $PSScriptRoot '../artifacts'),
    [string]$ConfigPath = (Join-Path $PSScriptRoot '../config/packaging.json'),
    [string]$BaseUrl = ''
)
. "$PSScriptRoot/Common.ps1"
$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$version = [string]$config.clientVersion
if ($version -notmatch '^2\.4\.\d+(?:-[a-zA-Z0-9.-]+)?$') { throw 'Expected an AionCL 2.4 semver version.' }
$limit = [long]$config.maxPackageBytes
if ($limit -lt 65536 -or $limit -ge 2GB) { throw 'maxPackageBytes must be >= 65536 and < 2 GiB.' }
Assert-PublicBaseUrl $BaseUrl
$BaseUrl = $BaseUrl.TrimEnd('/')
$source = (Get-Item -LiteralPath $SourcePath).FullName.TrimEnd('\', '/')
$root = [IO.Path]::GetFullPath($OutputRoot).TrimEnd('\', '/')
if ($root.Equals($source, [StringComparison]::OrdinalIgnoreCase) -or
    $root.StartsWith($source + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
    $source.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Source and output must be separate, non-nested directories.'
}
if ((Get-Item -LiteralPath $source).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Source cannot be a reparse point.' }
[IO.Directory]::CreateDirectory($root) | Out-Null
$lock = [IO.File]::Open((Join-Path $root '.build.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
$stage = $null
try {
    $inventory = [Collections.Generic.List[object]]::new()
    $excluded = [Collections.Generic.List[string]]::new()
    $map = @{}
    # Enumerate explicitly to reject links before traversing them.
    $pending = [Collections.Generic.Stack[string]]::new()
    $pending.Push($source)
    while ($pending.Count) {
        foreach ($item in Get-ChildItem -LiteralPath $pending.Pop() -Force) {
            $relative = $item.FullName.Substring($source.Length + 1).Replace('\', '/')
            $skip = $false
            foreach ($pattern in $config.exclude) {
                if ($relative -like $pattern -or ($item.PSIsContainer -and "$relative/" -like $pattern)) { $skip = $true; break }
            }
            if ($skip) { $excluded.Add($relative); continue }
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point is not supported: $relative" }
            Assert-RelativePath $relative
            if ($item.PSIsContainer) { $pending.Push($item.FullName); continue }
            if ($map.ContainsKey($relative)) { throw "Case-insensitive path collision: $relative" }
            $map[$relative] = $item
        }
    }
    [string[]]$paths = @($map.Keys)
    [Array]::Sort($paths, [StringComparer]::Ordinal)
    if (!$paths.Count) { throw 'No source files selected.' }
    Write-Host "Hashing $($paths.Count) source files..."
    foreach ($relative in $paths) {
        $item = $map[$relative]
        # Inspect distributable text without printing potentially sensitive values.
        if ($item.Extension -in '.ini', '.cfg', '.bat', '.ps1', '.txt', '.xml', '.json', '.yaml', '.yml', '.env', '.pem', '.key') {
            $reader = [IO.File]::OpenText($item.FullName)
            try {
                while ($null -ne ($line = $reader.ReadLine())) {
                    if ($line -match '(?i)(\b192\.168\.\d+\.\d+|\b10\.\d+\.\d+\.\d+|\b172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|(?:password|secret|token)\s*[=:]\s*\S+|BEGIN .*PRIVATE KEY|[A-Z]:\\Users\\|gh[pousr]_[A-Za-z0-9]{20,})') {
                        throw "Potential sensitive content in $relative; clean or explicitly exclude this file."
                    }
                }
            } finally { $reader.Dispose() }
        }
        $inventory.Add([pscustomobject][ordered]@{ path = $relative; size = [long]$item.Length; sha256 = (Get-Sha256 $item.FullName) })
    }
    $identity = [ordered]@{ formatVersion = 1; product = 'AionCL'; clientVersion = $version; maxPackageBytes = $limit; baseUrl = $BaseUrl; compression = 'deflate-optimal-fixed-time-v1'; files = @($inventory.ToArray()) }
    $bytes = [Text.Encoding]::UTF8.GetBytes(($identity | ConvertTo-Json -Depth 10 -Compress))
    $stream = [IO.MemoryStream]::new($bytes, $false)
    try { $buildId = Get-StreamHash $stream } finally { $stream.Dispose() }
    $destination = Join-Path $root "v$version"
    if (Test-Path -LiteralPath $destination) {
        $existing = Get-Content -LiteralPath (Join-Path $destination 'install-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($existing.buildId -ne $buildId) { throw 'Existing version has different inputs. Use a new version or a different OutputRoot.' }
        & "$PSScriptRoot/Test-Packages.ps1" -ManifestPath (Join-Path $destination 'install-manifest.json') -Deep
        Write-Host "Verified existing build: $destination"
        return
    }
    $groups = [Collections.Generic.List[object]]::new()
    $group = [Collections.Generic.List[object]]::new()
    [long]$budget = 65536
    foreach ($file in $inventory) {
        # Conservative DEFLATE expansion plus ZIP headers, UTF-8 names and ZIP64 margin.
        [long]$cost = [long][Math]::Ceiling($file.size * 1.01) + 4096 + 4 * [Text.Encoding]::UTF8.GetByteCount($file.path)
        if ($cost + 65536 -gt $limit) { throw "File too large for an independent ZIP: $($file.path). Raise the limit below 2 GiB or redesign the payload." }
        if ($budget + $cost -gt $limit -and $group.Count) {
            $groups.Add($group.ToArray()); $group = [Collections.Generic.List[object]]::new(); $budget = 65536
        }
        $group.Add($file); $budget += $cost
    }
    if ($group.Count) { $groups.Add($group.ToArray()) }
    if ($groups.Count + 2 -gt 1000) { throw 'Too many assets for one GitHub Release.' }
    $stage = Join-Path $root ('.building-' + [Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($stage) | Out-Null
    $packages = [Collections.Generic.List[object]]::new()
    $index = 0
    foreach ($batch in $groups) {
        $index++
        $name = 'aioncl-client-{0}-{1:D3}.zip' -f $version, $index
        Write-Host "Creating $name ($index/$($groups.Count))..."
        $zipPath = Join-Path $stage $name
        $zip = [IO.Compression.ZipFile]::Open($zipPath, [IO.Compression.ZipArchiveMode]::Create)
        try {
            foreach ($file in $batch) {
                $entry = $zip.CreateEntry($file.path, [IO.Compression.CompressionLevel]::Optimal)
                $entry.LastWriteTime = [DateTimeOffset]::new(2000, 1, 1, 0, 0, 0, [TimeSpan]::Zero)
                $inputStream = [IO.File]::Open((Join-Path $source $file.path), 'Open', 'Read', 'Read')
                try {
                    $outputStream = $entry.Open()
                    try { $inputStream.CopyTo($outputStream) } finally { $outputStream.Dispose() }
                } finally { $inputStream.Dispose() }
            }
        } finally { $zip.Dispose() }
        $size = (Get-Item -LiteralPath $zipPath).Length
        if ($size -gt $limit) { throw "Archive exceeds maxPackageBytes: $name" }
        $mirrors = @()
        if ($BaseUrl) { $mirrors = @("$BaseUrl/$name") }
        $packages.Add([pscustomobject][ordered]@{ name = $name; size = $size; uncompressedSize = [long](($batch | Measure-Object size -Sum).Sum); fileCount = @($batch).Count; sha256 = (Get-Sha256 $zipPath); mirrors = $mirrors; files = @($batch) })
    }
    $manifest = [ordered]@{
        formatVersion = 1; product = 'AionCL'; gameVersion = '2.4'; clientVersion = $version
        buildId = $buildId; archiveFormat = 'zip'; maxPackageBytes = $limit
        sourceFileCount = $inventory.Count; sourceBytes = [long](($inventory | Measure-Object size -Sum).Sum)
        compressedBytes = [long](($packages | Measure-Object size -Sum).Sum); packages = @($packages.ToArray())
    }
    $manifestPath = Join-Path $stage 'install-manifest.json'
    Write-Json $manifest $manifestPath
    $checksums = @($packages | ForEach-Object { "$($_.sha256)  $($_.name)" }) + "$(Get-Sha256 $manifestPath)  install-manifest.json"
    [IO.File]::WriteAllText((Join-Path $stage 'SHA256SUMS'), ($checksums -join "`n") + "`n", [Text.UTF8Encoding]::new($false))
    & "$PSScriptRoot/Test-Packages.ps1" -ManifestPath $manifestPath -Deep
    # Publish locally only after every archived file matches the source inventory.
    [IO.Directory]::Move($stage, $destination)
    $stage = $null
    Write-Host "Build complete: $destination; $($packages.Count) packages; $($manifest.compressedBytes) bytes; $($excluded.Count) excluded paths."
} finally {
    if ($stage -and [IO.Directory]::Exists($stage)) {
        $resolvedStage = [IO.Path]::GetFullPath($stage)
        if ([IO.Path]::GetDirectoryName($resolvedStage) -eq $root -and [IO.Path]::GetFileName($resolvedStage).StartsWith('.building-')) {
            [IO.Directory]::Delete($resolvedStage, $true)
        }
    }
    $lock.Dispose()
}
