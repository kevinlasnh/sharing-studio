$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()

$inputText = [Console]::In.ReadToEnd()

try {
    $hook = $inputText | ConvertFrom-Json -ErrorAction Stop
} catch {
    exit 0
}

function Get-HookFilePath {
    param($Hook)

    if ($null -eq $Hook.tool_input) {
        return ""
    }

    $toolInput = $Hook.tool_input
    if ($toolInput.PSObject.Properties.Name -contains "file_path") {
        return [string]$toolInput.file_path
    }
    if ($toolInput.PSObject.Properties.Name -contains "path") {
        return [string]$toolInput.path
    }
    return ""
}

function Normalize-VaultPath {
    param([string]$PathText)

    if ([string]::IsNullOrWhiteSpace($PathText)) {
        return ""
    }

    $normalized = ($PathText -replace "\\", "/").Trim()
    $projectDir = $env:CLAUDE_PROJECT_DIR
    if (-not [string]::IsNullOrWhiteSpace($projectDir)) {
        $projectNorm = ($projectDir -replace "\\", "/").TrimEnd("/")
        if ($normalized.StartsWith($projectNorm, [System.StringComparison]::OrdinalIgnoreCase)) {
            $normalized = $normalized.Substring($projectNorm.Length).TrimStart("/")
        }
    }

    return $normalized.ToLowerInvariant()
}

function Deny-Path {
    param(
        [string]$PathText,
        [string]$Reason
    )

    $payload = @{
        hookSpecificOutput = @{
            hookEventName = "PreToolUse"
            permissionDecision = "deny"
            permissionDecisionReason = "Second Brain path policy blocked '$PathText': $Reason"
        }
    } | ConvertTo-Json -Compress

    Write-Output $payload
}

$filePath = Get-HookFilePath -Hook $hook
$vaultPath = Normalize-VaultPath -PathText $filePath

if ([string]::IsNullOrWhiteSpace($vaultPath)) {
    exit 0
}

if ($vaultPath -in @("wiki/log.md", "wiki/hot.md", "wiki/ingest-log.md")) {
    Deny-Path -PathText $filePath -Reason "this scaffold is deprecated; daily journal + page frontmatter replace it"
    exit 0
}

if ($vaultPath -in @("wiki/overview.md", "wiki/index.md")) {
    Deny-Path -PathText $filePath -Reason "this wiki-level scaffold is deprecated; use root index.md and Obsidian Graph View"
    exit 0
}

if ($vaultPath -match '^\.raw/') {
    Deny-Path -PathText $filePath -Reason ".raw/ is not part of this vault; use root raw/ only for user-supplied files"
    exit 0
}

if ($vaultPath -match '^raw/.+\.md$') {
    Deny-Path -PathText $filePath -Reason "raw/ must not store Markdown notes; raw Markdown can create unintended Obsidian graph edges. Store as .txt/.pdf/original attachment, or ingest into wiki/"
    exit 0
}

if ($vaultPath -match '^wiki/sources/') {
    Deny-Path -PathText $filePath -Reason "wiki/sources/ is deprecated; use source_type/source_date frontmatter or raw/ wikilinks"
    exit 0
}

if ($vaultPath -match '^wiki/meta/(dashboard|overview)\.(md|canvas)$') {
    Deny-Path -PathText $filePath -Reason "lint reports are conversation output by default; dashboard/canvas artifacts are not part of this vault scaffold"
    exit 0
}

if ($vaultPath -match '^wiki/meta/lint-report.*\.md$') {
    Deny-Path -PathText $filePath -Reason "lint reports must stay in conversation output by default; save requested reports by appending a plain-text summary to daily/YYYY-MM-DD.md with no wikilinks or local/relative Markdown links"
    exit 0
}

if ($vaultPath -match '^wiki/.+\.canvas$') {
    Deny-Path -PathText $filePath -Reason "canvas files are outside the current second-brain skill workflow and conflict with the vault scaffold"
    exit 0
}

exit 0
