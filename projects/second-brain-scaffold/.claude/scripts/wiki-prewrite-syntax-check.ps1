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

function Test-WikiMarkdownPath {
    param([string]$PathText)

    if ([string]::IsNullOrWhiteSpace($PathText)) {
        return $false
    }

    $vaultPath = Get-VaultRelativePath -PathText $PathText
    return $vaultPath -match '^wiki/.+\.md$'
}

function Get-VaultRelativePath {
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

    return $fullNorm.Substring($rootWithSlash.Length)
}

function Get-ExpectedPermalink {
    param([string]$PathText)

    $vaultPath = Get-VaultRelativePath -PathText $PathText
    $vaultPath = $vaultPath -replace "\\", "/"
    if ($vaultPath -match '^wiki/([^/]+)/_index\.md$') {
        return "second-brain/wiki/$($Matches[1])/index"
    }
    if ($vaultPath -match '^wiki/([^/]+)/([^/]+)\.md$') {
        return "second-brain/wiki/$($Matches[1])/$($Matches[2])"
    }
    return $null
}

function Test-WikiPathSchema {
    param([string]$VaultPath)

    $violations = New-Object System.Collections.Generic.List[string]
    $domainPattern = '^[a-z0-9]+(?:-[a-z0-9]+)*$'
    $slugPattern = '^[a-z0-9]+(?:-[a-z0-9]+)*$'

    if ($VaultPath -match '^wiki/([^/]+)/_index\.md$') {
        $domain = $Matches[1]
        if ($domain -cnotmatch $domainPattern) {
            $violations.Add("wiki domain directory must be lowercase English kebab-case: $domain")
        }
    } elseif ($VaultPath -match '^wiki/([^/]+)/([^/]+)\.md$') {
        $domain = $Matches[1]
        $slug = $Matches[2]
        if ($domain -cnotmatch $domainPattern) {
            $violations.Add("wiki domain directory must be lowercase English kebab-case: $domain")
        }
        if ($slug -cnotmatch $slugPattern) {
            $violations.Add("wiki content filename must be lowercase English kebab-case: $slug.md")
        }
    } else {
        $violations.Add("wiki markdown path must be wiki/{domain}/_index.md or wiki/{domain}/{slug}.md")
    }

    return $violations
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

function Get-NonFenceLines {
    param([string[]]$Lines)

    $inFence = $false
    $result = New-Object System.Collections.Generic.List[object]

    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $line = $Lines[$i]
        if ($line -match '^\s*```') {
            $inFence = -not $inFence
            continue
        }
        if (-not $inFence) {
            $result.Add([pscustomobject]@{
                Number = $i + 1
                Text = $line
            })
        }
    }

    return $result
}

function Get-ProposedSnippets {
    param($Hook)

    $snippets = New-Object System.Collections.Generic.List[object]
    if ($null -eq $Hook.tool_input) {
        return $snippets
    }

    $toolInput = $Hook.tool_input

    if ($toolInput.PSObject.Properties.Name -contains "content") {
        $snippets.Add([pscustomobject]@{
            Kind = "full-file"
            Text = [string]$toolInput.content
        })
    }

    if ($toolInput.PSObject.Properties.Name -contains "new_string") {
        $snippets.Add([pscustomobject]@{
            Kind = "edit-fragment"
            Text = [string]$toolInput.new_string
        })
    }

    if ($toolInput.PSObject.Properties.Name -contains "edits" -and $null -ne $toolInput.edits) {
        foreach ($edit in $toolInput.edits) {
            if ($edit.PSObject.Properties.Name -contains "new_string") {
                $snippets.Add([pscustomobject]@{
                    Kind = "edit-fragment"
                    Text = [string]$edit.new_string
                })
            }
        }
    }

    return $snippets
}

function Test-ProposedMarkdown {
    param(
        [string]$Text,
        [string]$Kind,
        [string]$PathText
    )

    $violations = New-Object System.Collections.Generic.List[string]
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $violations
    }

    $lines = $Text -split "`r?`n"
    $visibleLines = Get-NonFenceLines -Lines $lines

    $markdownInternalLinkPattern = [regex]'\[[^\]]+\]\((?!https?://)[^)]*\.md[^)]*\)'
    $linkMatches = New-Object System.Collections.Generic.List[string]
    foreach ($line in $visibleLines) {
        if ($markdownInternalLinkPattern.IsMatch($line.Text)) {
            $linkMatches.Add(("{0}: {1}" -f $line.Number, $line.Text.Trim()))
        }
    }
    if ($linkMatches.Count -gt 0) {
        $violations.Add(
            "standard markdown internal .md links must be wikilinks: " +
            (($linkMatches | Select-Object -First 10) -join " | ")
        )
    }

    $inlineArrayPattern = [regex]'^(tags|aliases|cssclasses|related):\s*\['
    $inlineArrayMatches = New-Object System.Collections.Generic.List[string]
    $frontmatterScanLimit = if ($Kind -eq "full-file") { [Math]::Min(40, $lines.Count) } else { $lines.Count }
    for ($i = 0; $i -lt $frontmatterScanLimit; $i++) {
        if ($inlineArrayPattern.IsMatch($lines[$i])) {
            $inlineArrayMatches.Add(("{0}: {1}" -f ($i + 1), $lines[$i].Trim()))
        }
    }
    if ($inlineArrayMatches.Count -gt 0) {
        $violations.Add(
            "frontmatter inline YAML arrays must be multiline lists: " +
            (($inlineArrayMatches | Select-Object -First 10) -join " | ")
        )
    }

    $allowedCalloutTypes = @(
        "note", "abstract", "summary", "tldr", "info", "todo", "tip", "hint", "important",
        "success", "check", "done", "question", "help", "faq", "warning", "caution",
        "attention", "failure", "fail", "missing", "danger", "error", "bug", "example",
        "quote", "cite", "contradiction"
    )
    $calloutPattern = [regex]'^\s*>\s*\[!([^\]\+\-]+)'
    $badCalloutMatches = New-Object System.Collections.Generic.List[string]
    foreach ($line in $visibleLines) {
        $match = $calloutPattern.Match($line.Text)
        if ($match.Success) {
            $calloutType = $match.Groups[1].Value.Trim().ToLowerInvariant()
            if ($allowedCalloutTypes -notcontains $calloutType) {
                $badCalloutMatches.Add(("{0}: {1}" -f $line.Number, $line.Text.Trim()))
            }
        }
    }
    if ($badCalloutMatches.Count -gt 0) {
        $violations.Add(
            "unsupported Obsidian callout type: " +
            (($badCalloutMatches | Select-Object -First 10) -join " | ")
        )
    }

    if ($Kind -eq "full-file") {
        $firstLine = if ($lines.Count -gt 0) { $lines[0].Trim() } else { "" }
        if ($firstLine -ne "---") {
            $violations.Add("full wiki page content must start with YAML frontmatter delimiter ---")
        } else {
            $closingFrontmatterLine = $null
            for ($i = 1; $i -lt $lines.Count; $i++) {
                if ($lines[$i].Trim() -eq "---") {
                    $closingFrontmatterLine = $i + 1
                    break
                }
            }
            if ($null -eq $closingFrontmatterLine) {
                $violations.Add("YAML frontmatter must have a closing --- delimiter")
            }
        }

        foreach ($requiredKey in @("title", "type", "permalink")) {
            $value = Get-FrontmatterScalar -Lines $lines -Key $requiredKey
            if ([string]::IsNullOrWhiteSpace($value)) {
                $violations.Add("frontmatter must include '$requiredKey'")
            }
        }

        $vaultPath = Get-VaultRelativePath -PathText $PathText
        $actualType = Get-FrontmatterScalar -Lines $lines -Key "type"
        if ($vaultPath -match '^wiki/[^/]+/_index\.md$' -and $actualType -ne "index") {
            $violations.Add("domain index frontmatter type must be 'index'")
        } elseif ($vaultPath -match '^wiki/[^/]+/[^/]+\.md$' -and $vaultPath -notmatch '/_index\.md$' -and $actualType -eq "index") {
            $violations.Add("wiki content page frontmatter type must not be 'index'")
        }

        $expectedPermalink = Get-ExpectedPermalink -PathText $PathText
        if (-not [string]::IsNullOrWhiteSpace($expectedPermalink)) {
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

$filePath = Get-HookFilePath -Hook $hook
if (-not (Test-WikiMarkdownPath -PathText $filePath)) {
    exit 0
}

$snippets = Get-ProposedSnippets -Hook $hook
if ($snippets.Count -eq 0) {
    exit 0
}

$allViolations = New-Object System.Collections.Generic.List[string]
$vaultPath = Get-VaultRelativePath -PathText $filePath
foreach ($violation in (Test-WikiPathSchema -VaultPath $vaultPath)) {
    $allViolations.Add("path: $violation")
}
foreach ($snippet in $snippets) {
    $violations = Test-ProposedMarkdown -Text $snippet.Text -Kind $snippet.Kind -PathText $filePath
    foreach ($violation in $violations) {
        $allViolations.Add("$($snippet.Kind): $violation")
    }
}

if ($allViolations.Count -gt 0) {
    $payload = @{
        hookSpecificOutput = @{
            hookEventName = "PreToolUse"
            permissionDecision = "deny"
            permissionDecisionReason = "Second Brain wiki prewrite syntax check blocked '$filePath': " + (($allViolations | Select-Object -First 20) -join " ; ")
        }
    } | ConvertTo-Json -Compress

    Write-Output $payload
}

exit 0
