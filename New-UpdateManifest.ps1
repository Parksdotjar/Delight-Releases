param(
    [Parameter(Mandatory)][string]$Tag,
    [Parameter(Mandatory)][string]$AssetDirectory,
    [Parameter(Mandatory)][string]$OutputPath,
    [string]$Notes = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($Tag -cnotmatch '^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$') { throw 'Use a stable version tag such as v0.0.2.' }
$version = $Tag.Substring(1)
$platforms = [ordered]@{}
$assets = @(Get-ChildItem -LiteralPath $AssetDirectory -File | Where-Object Extension -eq '.exe')
if ($assets.Count -eq 0) { throw 'Attach a standalone Delight EXE before publishing the release.' }
foreach ($asset in $assets) {
    if ($asset.Name -cnotmatch '^[A-Za-z0-9][A-Za-z0-9_.-]*\.exe$') { throw "Use an EXE filename without spaces: $($asset.Name)" }
    if ($asset.Length -lt 70 -or $asset.Length -gt 2GB) { throw 'EXE size is outside the supported range.' }
    $reader = [IO.BinaryReader]::new([IO.File]::OpenRead($asset.FullName))
    try {
        if ($reader.ReadUInt16() -ne 0x5a4d) { throw 'Asset is not a Windows EXE.' }
        $reader.BaseStream.Position = 60
        $offset = $reader.ReadUInt32()
        if ($offset -lt 64 -or $offset -gt $asset.Length - 6) { throw 'Invalid PE header offset.' }
        $reader.BaseStream.Position = $offset
        if ($reader.ReadUInt32() -ne 0x4550) { throw 'Invalid PE signature.' }
        $platform = switch ($reader.ReadUInt16()) {
            0x8664 { 'windows-x64' }
            0xaa64 { 'windows-arm64' }
            0x014c { 'windows-x86' }
            default { throw 'Unsupported EXE processor.' }
        }
    } finally { $reader.Dispose() }
    if ($platforms.Contains($platform)) { throw "Multiple EXEs for $platform. Attach one standalone app per processor, not an installer." }
    $info = [Diagnostics.FileVersionInfo]::GetVersionInfo($asset.FullName)
    if ($info.ProductName -cne 'Delight' -or $info.InternalName -cne 'delight') { throw 'Only a standalone Delight executable is accepted.' }
    if ($info.ProductVersion -cne $version -and $info.ProductVersion -cne "$version.0") {
        throw "The EXE reports version '$($info.ProductVersion)', but the tag is $Tag. Bump the workspace version and rebuild first."
    }
    $platforms[$platform] = [ordered]@{
        url = "https://github.com/Parksdotjar/Delight-Releases/releases/download/$Tag/$($asset.Name)"
        sha256 = (Get-FileHash -LiteralPath $asset.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        size = $asset.Length
    }
}
if ($Notes.Length -gt 4000) { $Notes = $Notes.Substring(0, 4000) }
$manifest = [ordered]@{ schema = 1; version = $version; tag = $Tag; notes = $Notes; platforms = $platforms }
$json = $manifest | ConvertTo-Json -Depth 5
[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath), $json, [Text.UTF8Encoding]::new($false))
Write-Host "Verified $($assets.Count) executable(s); generated $OutputPath for $Tag."
