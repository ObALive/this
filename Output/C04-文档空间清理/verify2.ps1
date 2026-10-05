# C04 post-run verification v2: correct multi-base path resolution + title display.
param([string]$Root = 'D:\myspace\Git\mygame\Dsh\Design', [string]$Workspace = 'D:\myspace\Git\mygame')

$enc = New-Object System.Text.UTF8Encoding($false)
$cfg = [System.IO.File]::ReadAllText((Join-Path $PSScriptRoot 'tokens.json'), $enc) | ConvertFrom-Json
$metaWord = $cfg.metaField; $pOpen = $cfg.parenOpen; $pClose = $cfg.parenClose
$metaRe  = '^\|\s*' + [regex]::Escape($metaWord) + '\s*\|\s*(v[0-9]+(?:\.[0-9]+)?)\s*\|'
$titleRe = [regex]::Escape($pOpen) + '(v[0-9]+(?:\.[0-9]+)?)' + [regex]::Escape($pClose)

$files = Get-ChildItem -LiteralPath $Root -Recurse -File -Include *.md, *.csv
"files scanned: {0}" -f $files.Count

"`n==== A. version alignment (filename vs meta vs title) ===="
$bad = 0
foreach ($f in $files) {
    if ($f.Extension -ne '.md') { continue }
    $rel = $f.FullName.Substring($Root.Length + 1)
    $lines = [System.IO.File]::ReadAllLines($f.FullName, $enc)
    $meta = $null
    foreach ($l in $lines) { if ($l -match $metaRe) { $meta = $Matches[1]; break } }
    $title = $null
    if ($lines[0] -match $titleRe) { $title = $Matches[1] }
    $fn = if ($f.Name -match '_v([0-9]+(?:\.[0-9]+)?)\.md$') { 'v' + $Matches[1] } else { $null }
    if (-not $fn) { continue }
    $set = @($fn, $meta, $title) | Where-Object { $_ } | Select-Object -Unique
    if ($set.Count -gt 1) { $bad++; "  MISMATCH {0,-56} file=v{1} meta={2} title={3}" -f $rel, $fn, $meta, $title }
}
if ($bad -eq 0) { "  OK: filename = meta = title for every versioned doc" } else { "  {0} mismatches" -f $bad }

"`n==== B. unresolved .md/.csv references ===="
$miss = 0
foreach ($f in $files) {
    $rel = $f.FullName.Substring($Root.Length + 1)
    $text = [System.IO.File]::ReadAllText($f.FullName, $enc)
    foreach ($m in [regex]::Matches($text, '`([^`\r\n]*\.(?:md|csv))`')) {
        $p = $m.Groups[1].Value
        if ($p -match '[{}]' -or $p -match '^[A-Za-z]:') { continue }
        $rel2 = $p -replace '/', '\'
        $bases = @($Workspace, $Root, $f.DirectoryName, (Split-Path $f.DirectoryName -Parent), (Split-Path (Split-Path $f.DirectoryName -Parent) -Parent), (Split-Path (Split-Path (Split-Path $f.DirectoryName -Parent) -Parent) -Parent))
        $ok = $false
        foreach ($b in $bases) { if ($b -and (Test-Path -LiteralPath (Join-Path $b $rel2))) { $ok = $true; break } }
        if (-not $ok) { $miss++; "  UNRESOLVED {0,-52} -> {1}" -f $rel, $p }
    }
}
if ($miss -eq 0) { "  OK: every backticked path resolves from at least one base" } else { "  {0} unresolved references" -f $miss }

"`n==== C. file inventory after cleanup ===="
Get-ChildItem -LiteralPath $Root -Directory | ForEach-Object {
    $c = (Get-ChildItem -LiteralPath $_.FullName -Recurse -File | Measure-Object).Count
    "  {0,-24} files={1}" -f $_.Name, $c
}
"  current-version docs per system (highest version file):"
Get-ChildItem -LiteralPath $Root -Recurse -File -Include *.md | Where-Object { $_.Name -match '_v' } | Group-Object { $_.DirectoryName } | ForEach-Object {
    $top = $_.Group | Sort-Object { [double](($_.Name -replace '.*_v([0-9.]+)\.md$','$1')) } | Select-Object -Last 1
    "    {0,-52} -> {1}" -f $top.DirectoryName.Substring($Root.Length + 1), $top.Name
}
