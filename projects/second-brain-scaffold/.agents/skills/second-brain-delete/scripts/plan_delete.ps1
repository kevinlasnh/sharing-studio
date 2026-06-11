param(
    [string]$VaultRoot = ".",
    [Parameter(Mandatory = $true)][string]$Target,
    [ValidateSet("auto", "note", "domain", "raw", "daily", "workflow")][string]$TargetType = "auto",
    [Parameter(Mandatory = $true)][string]$OutputManifest
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

    if ($fullPath.Equals($rootNorm, [System.StringComparison]::OrdinalIgnoreCase)) {
        return ""
    }
    if (-not $fullPath.StartsWith($rootWithSlash, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $null
    }
    return $fullPath.Substring($rootWithSlash.Length)
}

function Convert-FromVaultPath {
    param([string]$VaultPath)
    return Join-Path $resolvedRoot ($VaultPath -replace "/", [System.IO.Path]::DirectorySeparatorChar)
}

function Get-FileSha256Text {
    param([string]$Text)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return (($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join "")
    } finally {
        $sha.Dispose()
    }
}

function Invoke-Git {
    param([string[]]$GitArgs)
    $output = & git -C $resolvedRoot @GitArgs 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return ($output -join "`n").Trim()
}

function Test-AllowedPrivateHfRemote {
    param([string]$RemoteUrl)
    return ($RemoteUrl -eq "<hf-private-dataset-url>")
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

function Get-KnowledgeMarkdownFiles {
    Get-ChildItem -LiteralPath $resolvedRoot -Recurse -Filter "*.md" -File |
        Where-Object {
            $vp = Convert-ToVaultPath $_.FullName
            $vp -and
            $vp -notmatch '^\.claude/' -and
            $vp -notmatch '^\.agents/' -and
            $vp -notmatch '^\.gemini/' -and
            $vp -notmatch '^\.claudian/' -and
            $vp -notmatch '^\.workflows/' -and
            $vp -notmatch '^\.brv/' -and
            $vp -notmatch '^\.obsidian/' -and
            $vp -notmatch '^templates/'
        }
}

function Get-KnownTargets {
    param($MarkdownFiles)
    $known = @{}
    foreach ($file in $MarkdownFiles) {
        $vp = Convert-ToVaultPath $file.FullName
        $withoutExt = $vp -replace '\.md$', ''
        $base = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        $known[$withoutExt] = $vp
        if (-not $known.ContainsKey($base)) {
            $known[$base] = $vp
        }
    }
    return $known
}

function Get-MarkdownRefs {
    param(
        [string]$SourcePath,
        [hashtable]$KnownTargets
    )

    $rows = New-Object System.Collections.Generic.List[object]
    $full = Convert-FromVaultPath $SourcePath
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { return $rows }
    $text = Get-Content -LiteralPath $full -Raw -Encoding UTF8
    $lines = $text -split "`r?`n"
    $wikilinkPattern = [regex]'(!?)\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|([^\]]+))?\]\]'
    $markdownPattern = [regex]'\[[^\]]+\]\(([^)]+)\)'

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        foreach ($match in $wikilinkPattern.Matches($line)) {
            $target = $match.Groups[2].Value.Trim()
            $key = $target -replace '\.md$', ''
            $resolved = $null
            if ($KnownTargets.ContainsKey($key)) { $resolved = $KnownTargets[$key] }
            $rows.Add([pscustomobject]@{
                source = $SourcePath
                line = $i + 1
                target = $target
                target_path = $resolved
                context = $line.Trim()
                embedded = ($match.Groups[1].Value -eq "!")
                link_type = "wikilink"
            })
        }
        foreach ($match in $markdownPattern.Matches($line)) {
            $target = $match.Groups[1].Value.Trim()
            if ($target -match '^(https?|mailto):') { continue }
            $rows.Add([pscustomobject]@{
                source = $SourcePath
                line = $i + 1
                target = $target
                target_path = $target
                context = $line.Trim()
                embedded = $false
                link_type = "markdown"
            })
        }
    }
    return $rows
}

function Test-DisposableFixture {
    param([string]$VaultPath)
    return (
        $VaultPath -match '^wiki/delete-test-[^/]+(/|$)' -or
        $VaultPath -match '^raw/delete-test-' -or
        $VaultPath -eq 'daily/2099-12-31.md'
    )
}

function Convert-ListToUniqueArray {
    param($Value)
    if ($null -eq $Value) { return @() }
    return @($Value | ForEach-Object { [string]$_ } | Where-Object { $_ } | Sort-Object -Unique)
}

function Convert-ObjectListToArray {
    param($Value)
    if ($null -eq $Value) { return @() }
    $items = New-Object 'System.Collections.Generic.List[object]'
    foreach ($item in $Value) {
        if ($null -ne $item) {
            $items.Add([object]$item)
        }
    }
    if ($items.Count -eq 0) { return @() }
    return @($items.ToArray())
}

$refusal = New-Object System.Collections.Generic.List[string]
$targetPath = Convert-ToVaultPath $Target
if ($null -eq $targetPath) {
    $refusal.Add("target is outside vault root")
    $targetPath = $Target
}
$targetPath = ($targetPath -replace "\\", "/").TrimEnd("/")

if ($Target -match '[\*\?]') {
    $refusal.Add("wildcard targets are not allowed")
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
        $refusal.Add("protected infrastructure path: $targetPath")
        break
    }
}
if ($targetPath -eq ".workflows/.active-session") {
    $refusal.Add("active workflow pointer cannot be deleted")
}

$actualType = $TargetType
if ($actualType -eq "auto") {
    if ($targetPath -match '^wiki/[^/]+/[^/]+\.md$' -and $targetPath -notmatch '/_index\.md$') {
        $actualType = "note"
    } elseif ($targetPath -match '^wiki/[^/]+$') {
        $actualType = "domain"
    } elseif ($targetPath -match '^raw/[^/]+$') {
        $actualType = "raw"
    } elseif ($targetPath -match '^daily/\d{4}-\d{2}-\d{2}\.md$') {
        $actualType = "daily"
    } elseif ($targetPath -match '^\.workflows/[^/]+$') {
        $actualType = "workflow"
    } else {
        $actualType = "unknown"
    }
}
if ($actualType -eq "unknown") {
    $refusal.Add("target cannot be classified as note/domain/raw/daily/workflow")
}

$targetFullPath = Convert-FromVaultPath $targetPath
$exists = Test-Path -LiteralPath $targetFullPath
if (-not $exists -and $actualType -ne "unknown") {
    $refusal.Add("target does not exist: $targetPath")
}

$activeSessionPath = $null
$activeSessionFile = Join-Path $resolvedRoot ".workflows/.active-session"
if (Test-Path -LiteralPath $activeSessionFile -PathType Leaf) {
    $activeSessionText = (Get-Content -LiteralPath $activeSessionFile -Raw -Encoding UTF8).Trim()
    if ($activeSessionText) {
        $activeSessionPath = Convert-ToVaultPath $activeSessionText
    }
}
if ($actualType -eq "workflow" -and $activeSessionPath -and $targetPath.Equals($activeSessionPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    $refusal.Add("current active workflow cannot be deleted")
}

$markdownFiles = @(Get-KnowledgeMarkdownFiles)
$knownTargets = Get-KnownTargets $markdownFiles
$allRefs = New-Object System.Collections.Generic.List[object]
foreach ($file in $markdownFiles) {
    $sourcePath = Convert-ToVaultPath $file.FullName
    foreach ($row in Get-MarkdownRefs -SourcePath $sourcePath -KnownTargets $knownTargets) {
        $allRefs.Add($row)
    }
}

$deletedPaths = New-Object System.Collections.Generic.List[string]
$indexPaths = New-Object System.Collections.Generic.List[string]
$inboundRefs = New-Object System.Collections.Generic.List[object]
$outboundRefs = New-Object System.Collections.Generic.List[object]
$rawRefs = New-Object System.Collections.Generic.List[object]
$modifiedReferencePaths = New-Object System.Collections.Generic.List[string]

if ($actualType -eq "note") {
    $deletedPaths.Add($targetPath)
    $domainIndex = $null
    if ($targetPath -match '^wiki/([^/]+)/([^/]+)\.md$') {
        $domainIndex = "wiki/$($Matches[1])/_index.md"
        $indexPaths.Add($domainIndex)
        $modifiedReferencePaths.Add($domainIndex)
    }
    foreach ($row in $allRefs) {
        if ($row.target_path -eq $targetPath -and $row.source -ne $targetPath -and $row.source -ne $domainIndex) { $inboundRefs.Add($row) }
        if ($row.source -eq $targetPath) { $outboundRefs.Add($row) }
    }
} elseif ($actualType -eq "raw") {
    $deletedPaths.Add($targetPath)
    foreach ($row in $allRefs) {
        if ($row.target -eq $targetPath -or $row.target_path -eq $targetPath) {
            $inboundRefs.Add($row)
            $rawRefs.Add($row)
        }
    }
} elseif ($actualType -eq "daily") {
    $deletedPaths.Add($targetPath)
    foreach ($row in $allRefs) {
        if ($row.source -eq $targetPath) { $outboundRefs.Add($row) }
        if ($row.target_path -eq $targetPath -and $row.source -ne $targetPath) { $inboundRefs.Add($row) }
    }
} elseif ($actualType -eq "domain") {
    $domain = ($targetPath -replace '^wiki/', '')
    $indexPaths.Add("index.md")
    $modifiedReferencePaths.Add("index.md")
    if ($exists) {
        Get-ChildItem -LiteralPath $targetFullPath -Recurse -File | ForEach-Object {
            $deletedPaths.Add((Convert-ToVaultPath $_.FullName))
        }
    }
    foreach ($row in $allRefs) {
        $targetInDomain = ($row.target_path -like "wiki/$domain/*")
        $sourceInDomain = ($row.source -like "wiki/$domain/*")
        if ($targetInDomain -and -not $sourceInDomain -and $row.source -ne "index.md") { $inboundRefs.Add($row) }
        if ($sourceInDomain) { $outboundRefs.Add($row) }
    }
} elseif ($actualType -eq "workflow") {
    if ($exists -and (Get-Item -LiteralPath $targetFullPath).PSIsContainer) {
        Get-ChildItem -LiteralPath $targetFullPath -Recurse -File | ForEach-Object {
            $deletedPaths.Add((Convert-ToVaultPath $_.FullName))
        }
    } else {
        $deletedPaths.Add($targetPath)
    }
}

if (($actualType -eq "note" -or $actualType -eq "raw" -or $actualType -eq "daily") -and $inboundRefs.Count -gt 0) {
    $refusal.Add("target has inbound references; remove or repair refs before apply")
}
if ($actualType -eq "domain" -and $inboundRefs.Count -gt 0) {
    $refusal.Add("domain has inbound references from outside the domain")
}

$isFixture = Test-DisposableFixture $targetPath
$requiresPreDeleteBackup = ($actualType -in @("note", "domain", "raw", "daily")) -and (-not $isFixture)

$head = Invoke-Git -GitArgs @("rev-parse", "HEAD")
$hfUrl = Invoke-Git -GitArgs @("remote", "get-url", "hf")
$hfMainContainsHead = $false
if ($requiresPreDeleteBackup -and -not (Test-AllowedPrivateHfRemote -RemoteUrl $hfUrl)) {
    $refusal.Add("real knowledge delete requires hf remote to be the private Second Brain backup dataset")
}
if ($head -and (Test-AllowedPrivateHfRemote -RemoteUrl $hfUrl)) {
    $remoteHead = Invoke-Git -GitArgs @("ls-remote", "hf", "refs/heads/main")
    if ($remoteHead -and $remoteHead -match ("^" + [regex]::Escape($head) + "\s+")) {
        $hfMainContainsHead = $true
    }
}
$dirtyOutput = Invoke-Git -GitArgs @("status", "--short")
$dirtyPaths = @()
if ($dirtyOutput) {
    $dirtyPaths = @($dirtyOutput -split "`n" | ForEach-Object { Convert-GitStatusLineToPath $_ } | Where-Object { $_ })
}
$scopedDirtyPaths = @($dirtyPaths | Where-Object { Test-ExplicitlyScopedDirtyPath $_ })
$unscopedDirtyPaths = @($dirtyPaths | Where-Object { -not (Test-ExplicitlyScopedDirtyPath $_) })

$preDeleteBackupCommit = $null
if ($requiresPreDeleteBackup -and $head -and $hfMainContainsHead) {
    $preDeleteBackupCommit = $head
}
if ($requiresPreDeleteBackup -and -not $preDeleteBackupCommit) {
    $refusal.Add("real knowledge delete requires current HEAD to be available from hf/main before apply")
}
if ($requiresPreDeleteBackup -and $unscopedDirtyPaths.Count -gt 0) {
    $refusal.Add("real knowledge delete requires a clean worktree outside explicitly scoped .workflows artifacts; unscoped dirty paths: $($unscopedDirtyPaths -join ', ')")
}

$validationReportPath = $OutputManifest -replace '\.json$', '.validation.json'
$manifestVaultPath = Convert-ToVaultPath $OutputManifest
$validationVaultPath = Convert-ToVaultPath $validationReportPath
if ($null -eq $validationVaultPath) { $validationVaultPath = $validationReportPath }

$tokenSeed = "$actualType|$targetPath|$head"
$token = "DELETE:${targetPath}:$((Get-FileSha256Text $tokenSeed).Substring(0, 12))"

[string[]]$dirtyPathArray = @(Convert-ListToUniqueArray -Value @($dirtyPaths))
[string[]]$scopedDirtyPathArray = @(Convert-ListToUniqueArray -Value @($scopedDirtyPaths))
[string[]]$unscopedDirtyPathArray = @(Convert-ListToUniqueArray -Value @($unscopedDirtyPaths))
[string[]]$deletedPathArray = @(Convert-ListToUniqueArray -Value @($deletedPaths))
[string[]]$modifiedReferencePathArray = @(Convert-ListToUniqueArray -Value @($modifiedReferencePaths))
[string[]]$indexPathArray = @(Convert-ListToUniqueArray -Value @($indexPaths))
[object[]]$inboundRefArray = @(Convert-ObjectListToArray -Value $inboundRefs)
[object[]]$outboundRefArray = @(Convert-ObjectListToArray -Value $outboundRefs)
[object[]]$rawRefArray = @(Convert-ObjectListToArray -Value $rawRefs)
$operationScope = "knowledge-delete"
if ($actualType -eq "workflow") {
    $operationScope = "workflow-artifact-delete"
} elseif ($isFixture) {
    $operationScope = "disposable-fixture-delete"
}

$worktreeState = [ordered]@{}
$worktreeState["clean"] = ($dirtyPaths.Count -eq 0)
$worktreeState["dirty_paths"] = $dirtyPathArray
$worktreeState["explicitly_scoped_dirty_paths"] = $scopedDirtyPathArray
$worktreeState["unscoped_dirty_paths"] = $unscopedDirtyPathArray
$worktreeState["acceptable"] = ($unscopedDirtyPaths.Count -eq 0)

$manifest = [ordered]@{}
$manifest["manifest_version"] = 1
$manifest["generated_at"] = (Get-Date).ToString("o")
$manifest["vault_root"] = $resolvedRoot
$manifest["target_input"] = $Target
$manifest["target_type"] = $actualType
$manifest["target_path"] = $targetPath
$manifest["operation_scope"] = $operationScope
$manifest["allowed"] = ($refusal.Count -eq 0)
$manifest["refusal_reasons"] = @($refusal)
$manifest["requires_pre_delete_backup"] = [bool]$requiresPreDeleteBackup
$manifest["is_disposable_fixture"] = [bool]$isFixture
$manifest["pre_delete_head"] = $head
$manifest["hf_remote_url"] = $hfUrl
$manifest["hf_main_contains_head"] = [bool]$hfMainContainsHead
$manifest["worktree_clean_or_explicitly_scoped_dirty_paths"] = $worktreeState
$manifest["pre_delete_backup_commit"] = $preDeleteBackupCommit
$manifest["deleted_paths"] = $deletedPathArray
$manifest["modified_reference_paths"] = $modifiedReferencePathArray
$manifest["index_paths"] = $indexPathArray
$manifest["validation_report_path"] = $validationVaultPath
$manifest["inbound_refs"] = $inboundRefArray
$manifest["outbound_refs"] = $outboundRefArray
$manifest["raw_refs"] = $rawRefArray
$manifest["confirmation_token"] = $token

$outFull = $OutputManifest
if (-not [System.IO.Path]::IsPathRooted($outFull)) {
    $outFull = Join-Path $resolvedRoot $outFull
}
$outDir = Split-Path -Parent $outFull
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outFull -Encoding UTF8
$manifest | ConvertTo-Json -Depth 10
