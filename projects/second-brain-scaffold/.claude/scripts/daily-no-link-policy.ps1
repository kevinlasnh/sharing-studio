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

    $projectDir = $env:CLAUDE_PROJECT_DIR
    if ([string]::IsNullOrWhiteSpace($projectDir)) {
        $projectDir = (Get-Location).Path
    }

    try {
        $root = [System.IO.Path]::GetFullPath($projectDir).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
        $candidate = $PathText.Trim()
        if (-not [System.IO.Path]::IsPathRooted($candidate)) {
            $candidate = Join-Path -Path $root -ChildPath $candidate
        }
        $full = [System.IO.Path]::GetFullPath($candidate).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    } catch {
        return ""
    }

    $rootNorm = ($root -replace "\\", "/").TrimEnd("/")
    $fullNorm = ($full -replace "\\", "/").TrimEnd("/")
    $rootWithSlash = $rootNorm + "/"
    if ($fullNorm.Equals($rootNorm, [System.StringComparison]::OrdinalIgnoreCase)) {
        return ""
    }
    if (-not $fullNorm.StartsWith($rootWithSlash, [System.StringComparison]::OrdinalIgnoreCase)) {
        return ""
    }

    return $fullNorm.Substring($rootWithSlash.Length).ToLowerInvariant()
}

function Resolve-HookFilePath {
    param(
        [string]$PathText,
        $Hook
    )

    $basePath = $env:CLAUDE_PROJECT_DIR
    if ([string]::IsNullOrWhiteSpace($basePath) -and $null -ne $Hook.cwd) {
        $basePath = [string]$Hook.cwd
    }
    if ([string]::IsNullOrWhiteSpace($basePath)) {
        $basePath = (Get-Location).Path
    }

    if ([System.IO.Path]::IsPathRooted($PathText)) {
        return [System.IO.Path]::GetFullPath($PathText)
    }

    return [System.IO.Path]::GetFullPath((Join-Path -Path $basePath -ChildPath $PathText))
}

function Get-FrontmatterScalar {
    param(
        [string[]]$Lines,
        [string]$Key
    )

    if ($Lines.Count -eq 0 -or $Lines[0].Trim() -ne "---") {
        return $null
    }
    for ($i = 1; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].Trim() -eq "---") {
            return $null
        }
        if ($Lines[$i] -match "^$([regex]::Escape($Key)):\s*(.*)$") {
            return $Matches[1].Trim().Trim("'`"")
        }
    }
    return $null
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
    param(
        [string]$Text,
        [string]$Kind,
        [string]$VaultPath
    )

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

    if ($Kind -eq "full-file") {
        if ($VaultPath -notmatch '^daily/(\d{4}-\d{2}-\d{2})\.md$') {
            $violations.Add("daily note path must be daily/YYYY-MM-DD.md")
        } else {
            $expectedPermalink = "second-brain/daily/$($Matches[1])"
            $actualPermalink = Get-FrontmatterScalar -Lines $lines -Key "permalink"
            if ([string]::IsNullOrWhiteSpace($actualPermalink)) {
                $violations.Add("frontmatter must include deterministic permalink: $expectedPermalink")
            } elseif ($actualPermalink -ne $expectedPermalink) {
                $violations.Add("frontmatter permalink must match path: expected '$expectedPermalink', got '$actualPermalink'")
            }
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
if ($vaultPath -notmatch '^daily/\d{4}-\d{2}-\d{2}\.md$') {
    $allViolations.Add("path: daily notes must use daily/YYYY-MM-DD.md")
}
$snippets = Get-ProposedSnippets -Hook $hook

foreach ($snippet in $snippets) {
    $violations = Test-DailyText -Text $snippet.Text -Kind $snippet.Kind -VaultPath $vaultPath
    foreach ($violation in $violations) {
        $allViolations.Add("$($snippet.Kind): $violation")
    }
}

$shouldScanCurrentFile = ($hookEventName -eq "PostToolUse" -or $snippets.Count -eq 0)
$resolvedPath = Resolve-HookFilePath -PathText $filePath -Hook $hook
if ($shouldScanCurrentFile -and (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
    try {
        $content = Get-Content -LiteralPath $resolvedPath -Raw -Encoding UTF8 -ErrorAction Stop
        $violations = Test-DailyText -Text $content -Kind "full-file" -VaultPath $vaultPath
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
