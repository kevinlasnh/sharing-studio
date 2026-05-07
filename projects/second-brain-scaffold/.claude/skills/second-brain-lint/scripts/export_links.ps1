param(
    [string]$VaultRoot = ".",
    [switch]$ContentOnly
)

$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()

$resolvedRoot = (Get-Item -LiteralPath (Resolve-Path -LiteralPath $VaultRoot).Path).FullName

function Convert-ToVaultPath {
    param([string]$PathText)
    $fullPath = ([System.IO.Path]::GetFullPath($PathText) -replace "\\", "/").TrimEnd("/")
    $rootNorm = ($resolvedRoot -replace "\\", "/").TrimEnd("/")
    $rootWithSlash = $rootNorm + "/"

    if ($fullPath.StartsWith($rootWithSlash, [System.StringComparison]::OrdinalIgnoreCase)) {
        $relative = $fullPath.Substring($rootWithSlash.Length)
    } elseif ($fullPath.Equals($rootNorm, [System.StringComparison]::OrdinalIgnoreCase)) {
        $relative = ""
    } else {
        $relative = $fullPath
    }

    return $relative
}

function Get-PageKind {
    param([string]$VaultPath)
    if ($VaultPath -eq "index.md") { return "root-index" }
    if ($VaultPath -like "daily/*.md") { return "daily" }
    if ($VaultPath -like "wiki/*/_index.md") { return "domain-index" }
    if ($VaultPath -like "wiki/*.md" -or $VaultPath -like "wiki/*/*.md") { return "content" }
    return "other"
}

function Get-Domain {
    param([string]$VaultPath)
    if ($VaultPath -match '^wiki/([^/]+)/') { return $Matches[1] }
    return $null
}

function Remove-InlineCode {
    param([string]$Line)
    return ([regex]::Replace($Line, '`[^`]*`', ''))
}

function Get-ScanLines {
    param([string[]]$Lines)

    $inFence = $false
    $inFrontmatter = $false
    $frontmatterDone = $false
    $result = New-Object System.Collections.Generic.List[object]

    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $line = $Lines[$i]
        $lineNumber = $i + 1

        if ($lineNumber -eq 1 -and $line.Trim() -eq "---") {
            $inFrontmatter = $true
            $result.Add([pscustomobject]@{ Number = $lineNumber; Text = $line; Frontmatter = $true })
            continue
        }

        if ($inFrontmatter) {
            $result.Add([pscustomobject]@{ Number = $lineNumber; Text = $line; Frontmatter = $true })
            if ($line.Trim() -eq "---") {
                $inFrontmatter = $false
                $frontmatterDone = $true
            }
            continue
        }

        if (-not $frontmatterDone -and $line.Trim() -eq "---") {
            $frontmatterDone = $true
        }

        if ($line -match '^\s*```') {
            $inFence = -not $inFence
            continue
        }

        if (-not $inFence) {
            if ($line -match '^\s*<!--.*-->\s*$') {
                continue
            }
            $result.Add([pscustomobject]@{ Number = $lineNumber; Text = (Remove-InlineCode $line); Frontmatter = $false })
        }
    }

    return $result
}

$markdownFiles = Get-ChildItem -LiteralPath $resolvedRoot -Recurse -Filter "*.md" -File |
    Where-Object { (Convert-ToVaultPath $_.FullName) -notmatch '^\.claude/' }

$knownTargets = @{}
foreach ($file in $markdownFiles) {
    $vaultPath = Convert-ToVaultPath $file.FullName
    $withoutExt = $vaultPath -replace '\.md$', ''
    $basename = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    $knownTargets[$withoutExt] = $vaultPath
    if (-not $knownTargets.ContainsKey($basename)) {
        $knownTargets[$basename] = $vaultPath
    }
}

$linkPattern = [regex]'(!?)\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]'
$rows = New-Object System.Collections.Generic.List[object]

foreach ($file in $markdownFiles) {
    $source = Convert-ToVaultPath $file.FullName
    $sourceKind = Get-PageKind $source
    if ($ContentOnly -and $sourceKind -ne "content") { continue }

    $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    $lines = $text -split "`r?`n"
    $scanLines = Get-ScanLines $lines

    foreach ($line in $scanLines) {
        foreach ($match in $linkPattern.Matches($line.Text)) {
            $target = $match.Groups[2].Value.Trim()
            if ($target -match '\s\[\[') { continue }
            if ($target -match '^\s*$') { continue }
            if ($target -match '[`$]') { continue }

            $targetKey = $target -replace '\.md$', ''
            $targetPath = $null
            $targetExists = $knownTargets.ContainsKey($targetKey)
            if ($targetExists) { $targetPath = $knownTargets[$targetKey] }

            $rows.Add([pscustomobject]@{
                source = $source
                source_kind = $sourceKind
                target = $target
                target_path = $targetPath
                target_exists = $targetExists
                line = $line.Number
                context = $line.Text.Trim()
                same_domain = ((Get-Domain $source) -ne $null -and (Get-Domain $source) -eq (Get-Domain $targetPath))
                reciprocal = $false
                frontmatter_only = [bool]$line.Frontmatter
                embedded = ($match.Groups[1].Value -eq "!")
            })
        }
    }
}

$edgeSet = @{}
foreach ($row in $rows) {
    if ($null -ne $row.target_path) {
        $edgeSet["$($row.source)|$($row.target_path)"] = $true
    }
}

foreach ($row in $rows) {
    if ($null -ne $row.target_path) {
        $row.reciprocal = $edgeSet.ContainsKey("$($row.target_path)|$($row.source)")
    }
}

$rows | ConvertTo-Json -Depth 5
