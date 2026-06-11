param(
    [string]$VaultRoot = ".",
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [string]$OutputReport
)

$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()

$resolvedRoot = (Get-Item -LiteralPath (Resolve-Path -LiteralPath $VaultRoot).Path).FullName

function Convert-ToVaultPath {
    param([string]$PathText)
    $candidate = $PathText
    if (-not [System.IO.Path]::IsPathRooted($candidate)) {
        $candidate = Join-Path $resolvedRoot $candidate
    }
    $fullPath = ([System.IO.Path]::GetFullPath($candidate) -replace "\\", "/").TrimEnd("/")
    $rootNorm = ($resolvedRoot -replace "\\", "/").TrimEnd("/")
    $rootWithSlash = $rootNorm + "/"
    if ($fullPath.Equals($rootNorm, [System.StringComparison]::OrdinalIgnoreCase)) { return "" }
    if (-not $fullPath.StartsWith($rootWithSlash, [System.StringComparison]::OrdinalIgnoreCase)) { return $null }
    return $fullPath.Substring($rootWithSlash.Length)
}

function Convert-FromVaultPath {
    param([string]$VaultPath)
    return Join-Path $resolvedRoot ($VaultPath -replace "/", [System.IO.Path]::DirectorySeparatorChar)
}

function Get-KnowledgeMarkdownFiles {
    Get-ChildItem -LiteralPath $resolvedRoot -Recurse -Filter "*.md" -File |
        Where-Object {
            $vp = Convert-ToVaultPath $_.FullName
            $vp -and
            $vp -notmatch '^\.workflows/' -and
            $vp -notmatch '^\.claude/' -and
            $vp -notmatch '^\.agents/' -and
            $vp -notmatch '^\.gemini/' -and
            $vp -notmatch '^\.claudian/' -and
            $vp -notmatch '^\.brv/' -and
            $vp -notmatch '^\.obsidian/' -and
            $vp -notmatch '^templates/'
        }
}

function Test-TextReference {
    param(
        [string]$FilePath,
        [string[]]$Patterns
    )
    $text = Get-Content -LiteralPath $FilePath -Raw -Encoding UTF8
    foreach ($pattern in $Patterns) {
        if ($pattern -and $text -match $pattern) { return $true }
    }
    return $false
}

$manifestFull = $ManifestPath
if (-not [System.IO.Path]::IsPathRooted($manifestFull)) {
    $manifestFull = Join-Path $resolvedRoot $manifestFull
}
if (-not (Test-Path -LiteralPath $manifestFull -PathType Leaf)) {
    throw "Manifest not found: $ManifestPath"
}
$manifest = Get-Content -LiteralPath $manifestFull -Raw -Encoding UTF8 | ConvertFrom-Json

$issues = New-Object System.Collections.Generic.List[object]
$checks = New-Object System.Collections.Generic.List[object]

foreach ($path in @($manifest.deleted_paths)) {
    $full = Convert-FromVaultPath $path
    $exists = Test-Path -LiteralPath $full
    $checks.Add([pscustomobject]@{ check = "deleted_path_absent"; path = $path; passed = (-not $exists) })
    if ($exists) {
        $issues.Add([pscustomobject]@{ issue = "deleted path still exists"; path = $path })
    }
}

$patterns = New-Object System.Collections.Generic.List[string]
if ($manifest.target_type -eq "note") {
    $target = [string]$manifest.target_path
    $withoutExt = $target -replace '\.md$', ''
    $basename = [System.IO.Path]::GetFileNameWithoutExtension($target)
    $patterns.Add([regex]::Escape($target))
    $patterns.Add([regex]::Escape($withoutExt))
    $patterns.Add('\[\[' + [regex]::Escape($basename) + '([#\|\]])')
} elseif ($manifest.target_type -eq "raw") {
    $target = [string]$manifest.target_path
    $patterns.Add([regex]::Escape($target))
} elseif ($manifest.target_type -eq "domain") {
    $patterns.Add([regex]::Escape(([string]$manifest.target_path) + "/"))
    $patterns.Add([regex]::Escape(([string]$manifest.target_path) + "/_index"))
}

if ($patterns.Count -gt 0) {
    foreach ($file in Get-KnowledgeMarkdownFiles) {
        $vp = Convert-ToVaultPath $file.FullName
        if (@($manifest.deleted_paths) -contains $vp) { continue }
        if (Test-TextReference -FilePath $file.FullName -Patterns @($patterns)) {
            $issues.Add([pscustomobject]@{ issue = "remaining reference to deleted target"; path = $vp })
        }
    }
}

foreach ($indexPath in @($manifest.index_paths)) {
    if (-not $indexPath) { continue }
    $full = Convert-FromVaultPath $indexPath
    if (Test-Path -LiteralPath $full -PathType Leaf) {
        $hasRef = $false
        if ($patterns.Count -gt 0) {
            $hasRef = Test-TextReference -FilePath $full -Patterns @($patterns)
        }
        $checks.Add([pscustomobject]@{ check = "index_clean"; path = $indexPath; passed = (-not $hasRef) })
        if ($hasRef) {
            $issues.Add([pscustomobject]@{ issue = "index still references deleted target"; path = $indexPath })
        }
    }
}

$deepAudit = [ordered]@{ ran = $false; exit_code = $null; summary = $null }
$deepAuditScript = Join-Path $resolvedRoot ".claude/skills/second-brain-lint/scripts/deep_audit.ps1"
if (Test-Path -LiteralPath $deepAuditScript -PathType Leaf) {
    $auditOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $deepAuditScript -VaultRoot $resolvedRoot -SkipBasicMemory 2>&1
    $deepAudit.ran = $true
    $deepAudit.exit_code = $LASTEXITCODE
    $deepAudit.summary = ($auditOutput | Select-Object -Last 20) -join "`n"
    if ($LASTEXITCODE -ne 0) {
        $issues.Add([pscustomobject]@{ issue = "deep_audit reported issues"; path = ".claude/skills/second-brain-lint/scripts/deep_audit.ps1" })
    }
}

$reportPath = $OutputReport
if (-not $reportPath) {
    $reportPath = [string]$manifest.validation_report_path
}
if (-not $reportPath) {
    $reportPath = ($ManifestPath -replace '\.json$', '.validation.json')
}
$reportFull = if ([System.IO.Path]::IsPathRooted($reportPath)) { $reportPath } else { Join-Path $resolvedRoot $reportPath }
$reportVaultPath = Convert-ToVaultPath $reportFull
if ($null -eq $reportVaultPath) { $reportVaultPath = $reportPath }

$report = [ordered]@{}
$report["validation_version"] = 1
$report["generated_at"] = (Get-Date).ToString("o")
$report["manifest_path"] = (Convert-ToVaultPath $manifestFull)
$report["target_type"] = $manifest.target_type
$report["target_path"] = $manifest.target_path
$report["clean"] = ($issues.Count -eq 0)
$report["checks"] = [object[]]$checks.ToArray()
$report["issues"] = [object[]]$issues.ToArray()
$report["deleted_paths"] = [object[]]@($manifest.deleted_paths)
$report["modified_reference_paths"] = [object[]]@($manifest.modified_reference_paths)
$report["index_paths"] = [object[]]@($manifest.index_paths)
$report["deep_audit"] = $deepAudit
$report["validation_report_path"] = $reportVaultPath

$outDir = Split-Path -Parent $reportFull
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportFull -Encoding UTF8
$report | ConvertTo-Json -Depth 10
