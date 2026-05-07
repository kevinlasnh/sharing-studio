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

function Resolve-HookFilePath {
    param(
        [string]$PathText,
        $Hook
    )

    if ([System.IO.Path]::IsPathRooted($PathText)) {
        return $PathText
    }

    $basePath = $env:CLAUDE_PROJECT_DIR
    if ([string]::IsNullOrWhiteSpace($basePath) -and $null -ne $Hook.cwd) {
        $basePath = [string]$Hook.cwd
    }
    if ([string]::IsNullOrWhiteSpace($basePath)) {
        $basePath = (Get-Location).Path
    }

    return (Join-Path -Path $basePath -ChildPath $PathText)
}

function Remove-InlineCode {
    param([string]$Line)
    return ([regex]::Replace($Line, '`[^`]*`', ''))
}

function Get-VisibleLines {
    param([string[]]$Lines)

    $inFence = $false
    $result = New-Object System.Collections.Generic.List[object]

    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $line = $Lines[$i]
        if ($line -match '^\s*```') {
            $inFence = -not $inFence
            continue
        }
        if ($inFence) {
            continue
        }
        if ($line -match '^\s*<!--.*-->\s*$') {
            continue
        }

        $result.Add([pscustomobject]@{
            Number = $i + 1
            Text = (Remove-InlineCode $line)
        })
    }

    return $result
}

function Test-DailyText {
    param([string]$Text)

    $violations = New-Object System.Collections.Generic.List[string]
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $violations
    }

    $lines = $Text -split "`r?`n"
    $visibleLines = Get-VisibleLines -Lines $lines
    $wikilinkPattern = [regex]'\[\[[^\]]+\]\]'
    $localMarkdownPattern = [regex]::new('!?\[[^\]]*\]\((?!https?://)[^)]*\)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)

    foreach ($line in $visibleLines) {
        if ($wikilinkPattern.IsMatch($line.Text)) {
            $violations.Add(("{0}: {1}" -f $line.Number, $line.Text.Trim()))
        } elseif ($localMarkdownPattern.IsMatch($line.Text)) {
            $violations.Add(("{0}: {1}" -f $line.Number, $line.Text.Trim()))
        }
    }

    return $violations
}

function Get-ProposedSnippets {
    param($Hook)

    $snippets = New-Object System.Collections.Generic.List[object]
    if ($null -eq $Hook.tool_input) {
        return $snippets
    }

    $toolInput = $Hook.tool_input

    if ($toolInput.PSObject.Properties.Name -contains "content") {
        $snippets.Add([pscustomobject]@{ Kind = "full-file"; Text = [string]$toolInput.content })
    }

    if ($toolInput.PSObject.Properties.Name -contains "new_string") {
        $snippets.Add([pscustomobject]@{ Kind = "edit-fragment"; Text = [string]$toolInput.new_string })
    }

    if ($toolInput.PSObject.Properties.Name -contains "edits" -and $null -ne $toolInput.edits) {
        foreach ($edit in $toolInput.edits) {
            if ($edit.PSObject.Properties.Name -contains "new_string") {
                $snippets.Add([pscustomobject]@{ Kind = "edit-fragment"; Text = [string]$edit.new_string })
            }
        }
    }

    return $snippets
}

$filePath = Get-HookFilePath -Hook $hook
$vaultPath = Normalize-VaultPath -PathText $filePath
$hookEventName = "PreToolUse"
if ($hook.PSObject.Properties.Name -contains "hook_event_name") {
    $hookEventName = [string]$hook.hook_event_name
} elseif ($hook.PSObject.Properties.Name -contains "hookEventName") {
    $hookEventName = [string]$hook.hookEventName
}

if ($vaultPath -notmatch '^daily/[^/]+\.md$') {
    exit 0
}

$allViolations = New-Object System.Collections.Generic.List[string]
$snippets = Get-ProposedSnippets -Hook $hook

foreach ($snippet in $snippets) {
    $violations = Test-DailyText -Text $snippet.Text
    foreach ($violation in $violations) {
        $allViolations.Add("$($snippet.Kind): $violation")
    }
}

$shouldScanCurrentFile = ($hookEventName -eq "PostToolUse" -or $snippets.Count -eq 0)
$resolvedPath = Resolve-HookFilePath -PathText $filePath -Hook $hook
if ($shouldScanCurrentFile -and (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
    try {
        $content = Get-Content -LiteralPath $resolvedPath -Raw -Encoding UTF8 -ErrorAction Stop
        $violations = Test-DailyText -Text $content
        foreach ($violation in $violations) {
            $allViolations.Add("file: $violation")
        }
    } catch {
        exit 0
    }
}

if ($allViolations.Count -gt 0) {
    $reason = "Second Brain daily no-link policy blocked '$filePath': daily notes must not contain wikilinks or local/relative markdown links. Use plain text paths such as wiki/domain/page.md; http(s) web links are allowed. " + (($allViolations | Select-Object -First 20) -join " ; ")
    $payload = @{
        decision = "block"
        reason = $reason
        hookSpecificOutput = @{
            hookEventName = $hookEventName
            permissionDecision = "deny"
            permissionDecisionReason = $reason
        }
    } | ConvertTo-Json -Compress

    Write-Output $payload
}

exit 0
