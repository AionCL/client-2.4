Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Write-Json($Value, [string]$Path) {
    [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 20) + "`n", [Text.UTF8Encoding]::new($false))
}
function Get-Sha256([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Get-StreamHash($Stream) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($sha.ComputeHash($Stream))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Assert-RelativePath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or $Path -match '[\\:\x00-\x1f]' -or $Path.StartsWith('/') -or
        @($Path.Split('/') | Where-Object { $_ -in '', '.', '..' -or $_ -match '[. ]$|[<>"|?*]|^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)' }).Count) {
        throw "Unsafe relative path: $Path"
    }
}
function Assert-PublicBaseUrl([string]$Url) {
    if (!$Url) { return }
    $uri = $null
    if (![Uri]::TryCreate($Url, [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -ne 'https' -or
        $uri.UserInfo -or $uri.Query -or $uri.Fragment -or $uri.HostNameType -ne [UriHostNameType]::Dns -or
        $uri.Host -notmatch '\.' -or $uri.Host -match '(?i)(\.local|\.localhost|\.internal)$') {
        throw 'BaseUrl must be a public HTTPS DNS URL without credentials, query or fragment.'
    }
}
