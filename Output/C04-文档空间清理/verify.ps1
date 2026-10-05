# C04 post-run verification: (a) filename/meta/title version alignment, (b) dangling .md/.csv references, (c) leftover revoked-system handles.
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
    if ($lines[0] -match $titleRe) { $title = 'v' + $Matches[1] }
    $fn = if ($f.Name -match '_v([0-9]+(?:\.[0-9]+)?)\.md$') { 'v' + $Matches[1] } else { $null }
    if (-not $fn) { continue }
    $set = @($fn, $meta, $title) | Where-Object { $_ }
    $distinct = $set | Select-Object -Unique
    if ($distinct.Count -gt 1) { $bad++; "  MISMATCH {0,-58} file={1} meta={2} title={3}" -f $rel, $fn, $meta, $title }
}
if ($bad -eq 0) { "  OK: all filenames match in-document versions" } else { "  {0} mismatches" -f $bad }

"`n==== B. dangling .md/.csv references ===="
$miss = 0
foreach ($f in $files) {
    $rel = $f.FullName.Substring($Root.Length + 1)
    $text = [System.IO.File]::ReadAllText($f.FullName, $enc)
    foreach ($m in [regex]::Matches($text, '`([^`\r\n]*\.(?:md|csv))`')) {
        $p = $m.Groups[1].Value
        if ($p -match '^[A-Za-z]:') { continue }
        $full = if ($p.StartsWith('Dsh/')) { Join-Path $Workspace ($p -replace '/', '\') } else { Join-Path $Root ($p -replace '/', '\') }
        if (-not (Test-Path -LiteralPath $full)) { $miss++; "  MISSING {0,-52} -> {1}" -f $rel, $p }
    }
}
if ($miss -eq 0) { "  OK: every backticked path resolves" } else { "  {0} unresolved references" -f $miss }

"`n==== C. revoked-system handles still present (informational) ===="
$pat = '03-10|03-20|03-30|08-10|08-20|09-10|09-30'
foreach ($f in $files) {
    $rel = $f.FullName.Substring($Root.Length + 1)
    $hits = Select-String -LiteralPath $f.FullName -Pattern $pat
    if ($hits) { "  {0,-56} x{1}" -f $rel, $hits.Count }
}
