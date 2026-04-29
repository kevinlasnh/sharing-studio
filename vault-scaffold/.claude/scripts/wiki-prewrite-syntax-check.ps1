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

    $normalized = $PathText -replace "\\", "/"
    return $normalized -match '(^|/)wiki/.+\.md$'
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
        [string]$Kind
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
foreach ($snippet in $snippets) {
    $violations = Test-ProposedMarkdown -Text $snippet.Text -Kind $snippet.Kind
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
