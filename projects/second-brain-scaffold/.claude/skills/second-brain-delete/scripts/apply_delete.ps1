param(
    [string]$VaultRoot = ".",
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$ConfirmationToken,
    [string]$OutputResult,
    [switch]$DryRun
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

function Invoke-Git {
    param([string[]]$GitArgs)
    $output = & git -C $resolvedRoot @GitArgs 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return ($output -join "`n").Trim()
}

function Test-ExplicitlyScopedDirtyPath {
    param([string]$PathText)
    if ([string]::IsNullOrWhiteSpace($PathText)) { return $false }
    $normalized = ($PathText -replace "\\", "/").Trim()
    return ($normalized -match '^\.workflows(/|$)')
}

function Convert-GitStatusLineToPath {
    param([string]$LineText)
    if ([string]::IsNullOrWhiteSpace($LineText)) { return $null }
    $line = [string]$LineText
    if ($line.Length -ge 4 -and $line[2] -eq ' ') {
        return $line.Substring(3).Trim()
    }
    if ($line -match '^.{1,2}\s+(.+)$') {
        return $Matches[1].Trim()
    }
    return $line.Trim()
}

function Get-GitDirtyPaths {
    $dirtyOutput = Invoke-Git -GitArgs @("status", "--short")
    if (-not $dirtyOutput) { return @() }
    return @($dirtyOutput -split "`n" | ForEach-Object { Convert-GitStatusLineToPath $_ } | Where-Object { $_ })
}

function Add-ResultAction {
    param([string]$Action, [string]$Path, [string]$Status)
    $script:actions.Add([pscustomobject]@{ action = $Action; path = $Path; status = $Status })
}

function Remove-IndexLine {
    param(
        [string]$IndexVaultPath,
        [string]$Pattern
    )
    $full = Convert-FromVaultPath $IndexVaultPath
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { return }
    $lines = Get-Content -LiteralPath $full -Encoding UTF8
    $kept = @($lines | Where-Object { $_ -notmatch $Pattern })
    if ($kept.Count -ne $lines.Count) {
        if (-not $DryRun) {
            Set-Content -LiteralPath $full -Encoding UTF8 -Value $kept
        }
        Add-ResultAction "update-index" $IndexVaultPath ($(if ($DryRun) { "dry-run" } else { "updated" }))
    }
}

$manifestFull = $ManifestPath
if (-not [System.IO.Path]::IsPathRooted($manifestFull)) {
    $manifestFull = Join-Path $resolvedRoot $manifestFull
}
if (-not (Test-Path -LiteralPath $manifestFull -PathType Leaf)) {
    throw "Manifest not found: $ManifestPath"
}
$manifest = Get-Content -LiteralPath $manifestFull -Raw -Encoding UTF8 | ConvertFrom-Json

$errors = New-Object System.Collections.Generic.List[string]
$actions = New-Object System.Collections.Generic.List[object]

if (-not $manifest.allowed) { $errors.Add("manifest is not allowed: $($manifest.refusal_reasons -join '; ')") }
if ($ConfirmationToken -ne $manifest.confirmation_token) { $errors.Add("confirmation token mismatch") }
if ($manifest.target_path -match '[\*\?]') { $errors.Add("wildcard target in manifest") }

$targetPath = [string]$manifest.target_path
$targetFull = Convert-FromVaultPath $targetPath
$roundTrip = Convert-ToVaultPath $targetFull
if ($null -eq $roundTrip -or -not $roundTrip.Equals($targetPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    $errors.Add("target path escapes vault root")
}

$protectedPatterns = @(
    '^$',
    '^CLAUDE\.md$',
    '^AGENTS\.md$',
    '^GEMINI\.md$',
    '^index\.md$',
    '^\.claude/',
    '^\.agents/',
    '^\.gemini/',
    '^\.obsidian/',
    '^\.git/',
    '^\.brv/',
    '^\.claudian/'
)
foreach ($pattern in $protectedPatterns) {
    if ($targetPath -match $pattern) {
        $errors.Add("protected infrastructure path: $targetPath")
        break
    }
}

$activeSessionFile = Join-Path $resolvedRoot ".workflows/.active-session"
if (Test-Path -LiteralPath $activeSessionFile -PathType Leaf) {
    $activeSessionText = (Get-Content -LiteralPath $activeSessionFile -Raw -Encoding UTF8).Trim()
    if ($activeSessionText) {
        $activeVaultPath = Convert-ToVaultPath $activeSessionText
        if ($activeVaultPath -and $targetPath.Equals($activeVaultPath, [System.StringComparison]::OrdinalIgnoreCase)) {
            $errors.Add("current active workflow cannot be deleted")
        }
    }
}

if ($manifest.requires_pre_delete_backup -and -not $DryRun) {
    if (-not $manifest.pre_delete_backup_commit) { $errors.Add("missing pre_delete_backup_commit") }
    if (-not $manifest.hf_main_contains_head) { $errors.Add("hf_main_contains_head is not true") }
    if (-not $manifest.pre_delete_head) { $errors.Add("missing pre_delete_head") }
    $dirtyPaths = @(Get-GitDirtyPaths)
    $unscopedDirtyPaths = @($dirtyPaths | Where-Object { -not (Test-ExplicitlyScopedDirtyPath $_) })
    if ($unscopedDirtyPaths.Count -gt 0) {
        $errors.Add("real knowledge delete requires a clean worktree outside explicitly scoped .workflows artifacts; unscoped dirty paths: $($unscopedDirtyPaths -join ', ')")
    }
    if ($null -ne $manifest.worktree_clean_or_explicitly_scoped_dirty_paths -and
        $manifest.worktree_clean_or_explicitly_scoped_dirty_paths.PSObject.Properties.Name -contains "acceptable" -and
        -not [bool]$manifest.worktree_clean_or_explicitly_scoped_dirty_paths.acceptable) {
        $errors.Add("manifest was planned with unscoped dirty paths; re-run delete planning after committing, backing up, or reverting unrelated changes")
    }
}

$realInboundRefs = @($manifest.inbound_refs | Where-Object { $null -ne $_ -and $_.PSObject.Properties.Name -contains "source" })
if ($realInboundRefs.Count -gt 0) {
    $errors.Add("manifest still has inbound references; apply refuses semantic cleanup")
}

if ($errors.Count -gt 0) {
    $result = [ordered]@{
        applied = $false
        dry_run = [bool]$DryRun
        target_path = $targetPath
        errors = @($errors)
        actions = @()
    }
    if ($OutputResult) {
        $outFull = if ([System.IO.Path]::IsPathRooted($OutputResult)) { $OutputResult } else { Join-Path $resolvedRoot $OutputResult }
        $outDir = Split-Path -Parent $outFull
        if ($outDir -and -not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
        $result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outFull -Encoding UTF8
    }
    $result | ConvertTo-Json -Depth 10
    exit 2
}

if (-not (Test-Path -LiteralPath $targetFull)) {
    throw "Target no longer exists: $targetPath"
}

switch ($manifest.target_type) {
    "note" {
        if (-not $DryRun) { Remove-Item -LiteralPath $targetFull -Force }
        Add-ResultAction "delete-file" $targetPath ($(if ($DryRun) { "dry-run" } else { "deleted" }))
        if ($targetPath -match '^wiki/([^/]+)/([^/]+)\.md$') {
            $domain = $Matches[1]
            $slug = $Matches[2]
            Remove-IndexLine "wiki/$domain/_index.md" ("(\[\[$([regex]::Escape($slug))(\||\]\])|$([regex]::Escape("wiki/$domain/$slug")))")
        }
    }
    "raw" {
        if (-not $DryRun) { Remove-Item -LiteralPath $targetFull -Force }
        Add-ResultAction "delete-file" $targetPath ($(if ($DryRun) { "dry-run" } else { "deleted" }))
    }
    "daily" {
        if (-not $DryRun) { Remove-Item -LiteralPath $targetFull -Force }
        Add-ResultAction "delete-file" $targetPath ($(if ($DryRun) { "dry-run" } else { "deleted" }))
    }
    "domain" {
        if ($targetPath -match '^wiki/([^/]+)$') {
            $domain = $Matches[1]
            if (-not $DryRun) { Remove-Item -LiteralPath $targetFull -Recurse -Force }
            Add-ResultAction "delete-directory" $targetPath ($(if ($DryRun) { "dry-run" } else { "deleted" }))
            Remove-IndexLine "index.md" ([regex]::Escape("wiki/$domain/_index"))
        } else {
            throw "Invalid domain path: $targetPath"
        }
    }
    "workflow" {
        if (-not $DryRun) { Remove-Item -LiteralPath $targetFull -Recurse -Force }
        Add-ResultAction "delete-workflow" $targetPath ($(if ($DryRun) { "dry-run" } else { "deleted" }))
    }
    default {
        throw "Unsupported target type: $($manifest.target_type)"
    }
}

$result = [ordered]@{}
$result["applied"] = (-not $DryRun)
$result["dry_run"] = [bool]$DryRun
$result["target_path"] = $targetPath
$result["target_type"] = $manifest.target_type
$result["actions"] = [object[]]$actions.ToArray()
$result["errors"] = [object[]]@()

if ($OutputResult) {
    $outFull = if ([System.IO.Path]::IsPathRooted($OutputResult)) { $OutputResult } else { Join-Path $resolvedRoot $OutputResult }
    $outDir = Split-Path -Parent $outFull
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
    $result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outFull -Encoding UTF8
}
$result | ConvertTo-Json -Depth 10
