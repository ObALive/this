# C04 doc-space cleanup: align filename version with in-document version, then rewrite path references.
# ASCII-only script body (Windows PowerShell 5.1 reads .ps1 as ANSI unless BOM); all CJK literals live in tokens.json.
# Usage: & .\align_v2.ps1          -> dry run
#        & .\align_v2.ps1 -Apply   -> execute
param([switch]$Apply)

$root    = 'D:\myspace\Git\mygame\Dsh\Design'
$cfgPath = Join-Path $PSScriptRoot 'tokens.json'
$enc     = New-Object System.Text.UTF8Encoding($false)

$cfg = [System.IO.File]::ReadAllText($cfgPath, $enc) | ConvertFrom-Json
$metaWord = $cfg.metaField
$pOpen = $cfg.parenOpen
$pClose = $cfg.parenClose
$metaRe = '^\|\s*' + [regex]::Escape($metaWord) + '\s*\|\s*(v[0-9]+(?:\.[0-9]+)?)\s*\|'
$titleRe = [regex]::Escape($pOpen) + 'v[0-9]+(?:\.[0-9]+)?' + [regex]::Escape($pClose)

function Get-VerKey([string]$v) {
    # v1.20 -> 1020 ; v4.2 -> 4002 : compare as integer tuple, not decimal.
    $s = $v -replace '^v', ''
    $p = $s.Split('.')
    $major = [int]$p[0]
    $minor = if ($p.Count -gt 1) { [int]$p[1] } else { 0 }
    return $major * 1000 + $minor
}

$docs = @()
foreach ($f in (Get-ChildItem -LiteralPath $root -Recurse -File -Include *.md, *.csv)) {
    $rel = $f.FullName.Substring($root.Length + 1)
    if ($f.Extension -ne '.md') {
        $docs += [pscustomobject]@{ File = $f; Rel = $rel; Target = $null; Bare = $null; Meta = $null; FnVer = $null }
        continue
    }
    $lines = [System.IO.File]::ReadAllLines($f.FullName, $enc)
    $meta = $null; $vers = @()
    foreach ($l in $lines) {
        if ($l -match $metaRe) { if (-not $meta) { $meta = $Matches[1] } }
        elseif ($l -match '^\|\s*(v[0-9]+(?:\.[0-9]+)?)\s*\|') { $vers += $Matches[1] }
    }
    $cand = @(); if ($meta) { $cand += $meta }; $cand += $vers
    $target = $null
    if ($cand.Count -gt 0) { $target = ($cand | Sort-Object { Get-VerKey $_ } | Select-Object -Last 1) }
    $bare = if ($target) { $target -replace '^v', '' } else { $null }
    $fnVer = if ($f.Name -match '_v([0-9]+(?:\.[0-9]+)?)\.md$') { $Matches[1] } else { $null }
    $docs += [pscustomobject]@{ File = $f; Rel = $rel; Target = $target; Bare = $bare; Meta = $meta; FnVer = $fnVer }
}

# ---------- 1. version normalisation ----------
$fixPlan = @()
foreach ($d in $docs) {
    if (-not $d.Target) { continue }
    $needTitle = $false
    $lines = [System.IO.File]::ReadAllLines($d.File.FullName, $enc)
    if ($lines[0] -match $titleRe) { if ($lines[0] -notmatch [regex]::Escape($pOpen + $d.Target + $pClose)) { $needTitle = $true } }
    $needMeta = ($d.Meta -and $d.Meta -ne $d.Target)
    if ($needTitle -or $needMeta) { $fixPlan += $d }
}
"==== 1. version normalisation: {0} docs ====" -f $fixPlan.Count
foreach ($d in $fixPlan) {
    $m = if ($d.Meta -and $d.Meta -ne $d.Target) { "meta:$($d.Meta)->$($d.Target)" } else { 'meta-ok' }
    "  {0,-58} target={1,-6} {2}" -f $d.Rel, $d.Target, $m
}

# ---------- 2. rename plan ----------
$renames = @()
foreach ($d in $docs) {
    if (-not $d.Bare -or -not $d.FnVer) { continue }
    if ($d.FnVer -eq $d.Bare) { continue }
    $newName = $d.File.Name -replace ('_v' + [regex]::Escape($d.FnVer) + '\.md$'), ('_v' + $d.Bare + '.md')
    $renames += [pscustomobject]@{ Old = $d.File.FullName; New = (Join-Path $d.File.DirectoryName $newName); OldName = $d.File.Name; NewName = $newName }
}
"`n==== 2. rename: {0} files ====" -f $renames.Count
$dupNew = $renames | Group-Object NewName | Where-Object Count -gt 1
if ($dupNew) { "!! target name collision:"; $dupNew | ForEach-Object { "   $($_.Name)" } }
$dupBase = (Get-ChildItem -LiteralPath $root -Recurse -File -Include *.md).Name | Group-Object | Where-Object Count -gt 1
if ($dupBase) { "!! duplicate basenames (affects token rewrite):"; $dupBase | ForEach-Object { "   $($_.Name) x$($_.Count)" } }
foreach ($r in ($renames | Sort-Object OldName)) { "  {0,-58} -> {1}" -f $r.OldName, $r.NewName }

# ---------- 3. path-token rewrite plan ----------
$tokens = @()
foreach ($r in $renames) { $tokens += [pscustomobject]@{ Old = $r.OldName; New = $r.NewName } }
foreach ($p in $cfg.map.PSObject.Properties) { $tokens += [pscustomobject]@{ Old = $p.Name; New = $p.Value } }
$tokens = $tokens | Sort-Object { $_.Old.Length } -Descending

$hitFiles = @{}
foreach ($d in $docs) {
    $text = [System.IO.File]::ReadAllText($d.File.FullName, $enc)
    $n = 0
    foreach ($t in $tokens) { $n += ([regex]::Matches($text, [regex]::Escape($t.Old))).Count }
    if ($n -gt 0) { $hitFiles[$d.Rel] = $n }
}
"`n==== 3. files whose references need rewriting: {0} (hits {1}) ====" -f $hitFiles.Count, (($hitFiles.Values | Measure-Object -Sum).Sum)
$hitFiles.GetEnumerator() | Sort-Object Name | ForEach-Object { "  {0,-60} {1}" -f $_.Key, $_.Value }

if (-not $Apply) { "`n(dry run: nothing written. add -Apply to execute)"; return }

# ---------- execute ----------
foreach ($d in $fixPlan) {
    $lines = [System.IO.File]::ReadAllLines($d.File.FullName, $enc)
    if ($lines[0] -match $titleRe) { $lines[0] = [regex]::Replace($lines[0], $titleRe, $pOpen + $d.Target + $pClose, 1) }
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $metaRe) {
            $lines[$i] = [regex]::Replace($lines[$i], 'v[0-9]+(?:\.[0-9]+)?', $d.Target, 1)
            break
        }
    }
    [System.IO.File]::WriteAllLines($d.File.FullName, $lines, $enc)
}
"version normalisation done: {0} docs" -f $fixPlan.Count

foreach ($r in $renames) { Move-Item -LiteralPath $r.Old -Destination ($r.Old + '.tmp') }
foreach ($r in $renames) { Move-Item -LiteralPath ($r.Old + '.tmp') -Destination $r.New }
"rename done: {0} files" -f $renames.Count

$changed = 0
foreach ($f in (Get-ChildItem -LiteralPath $root -Recurse -File -Include *.md, *.csv)) {
    $text = [System.IO.File]::ReadAllText($f.FullName, $enc)
    $new = $text
    foreach ($t in $tokens) { $new = $new.Replace($t.Old, $t.New) }
    if ($new -ne $text) { [System.IO.File]::WriteAllText($f.FullName, $new, $enc); $changed++ }
}
"reference rewrite done: {0} files updated" -f $changed
