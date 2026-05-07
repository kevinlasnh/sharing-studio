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

$filePath = Get-HookFilePath -Hook $hook
if (-not (Test-WikiMarkdownPath -PathText $filePath)) {
    exit 0
}

$resolvedPath = Resolve-HookFilePath -PathText $filePath -Hook $hook
if (-not (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
    exit 0
}

try {
    $content = Get-Content -LiteralPath $resolvedPath -Raw -Encoding UTF8 -ErrorAction Stop
} catch {
    exit 0
}

$lines = $content -split "`r?`n"
$visibleLines = Get-NonFenceLines -Lines $lines
$violations = New-Object System.Collections.Generic.List[string]

$markdownInternalLinkPattern = [regex]'\[[^\]]+\]\((?!https?://)[^)]*\.md[^)]*\)'
$linkMatches = New-Object System.Collections.Generic.List[string]
foreach ($line in $visibleLines) {
    if ($markdownInternalLinkPattern.IsMatch($line.Text)) {
        $linkMatches.Add(("{0}: {1}" -f $line.Number, $line.Text))
    }
}

if ($linkMatches.Count -gt 0) {
    $violations.Add(
        "[wiki-syntax-check] VIOLATION 1: 标准 markdown 内部链接 (.md) 必须改为 [[note-name]] wikilink 格式`n    " +
        (($linkMatches | Select-Object -First 20) -join "`n    ")
    )
}

$firstLine = ""
if ($lines.Count -gt 0) {
    $firstLine = $lines[0].Trim()
}

if ($firstLine -ne "---") {
    $violations.Add("[wiki-syntax-check] VIOLATION 2: 首行不是 '---'，缺失 frontmatter。实际首行: $firstLine")
} else {
    $closingFrontmatterLine = $null
    for ($i = 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -eq "---") {
            $closingFrontmatterLine = $i + 1
            break
        }
    }
    if ($null -eq $closingFrontmatterLine) {
        $violations.Add("[wiki-syntax-check] VIOLATION 2B: frontmatter 缺少闭合 '---'")
    }
}

$inlineArrayPattern = [regex]'^(tags|aliases|cssclasses|related):\s*\['
$inlineArrayMatches = New-Object System.Collections.Generic.List[string]
$frontmatterScanLimit = [Math]::Min(30, $lines.Count)
for ($i = 0; $i -lt $frontmatterScanLimit; $i++) {
    if ($inlineArrayPattern.IsMatch($lines[$i])) {
        $inlineArrayMatches.Add(("{0}: {1}" -f ($i + 1), $lines[$i]))
    }
}

if ($inlineArrayMatches.Count -gt 0) {
    $violations.Add(
        "[wiki-syntax-check] VIOLATION 3: frontmatter 使用 inline YAML 数组，必须改为多行列表`n    " +
        ($inlineArrayMatches -join "`n    ") +
        "`n    正确格式:`n      tags:`n        - x`n        - y"
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
            $badCalloutMatches.Add(("{0}: {1}" -f $line.Number, $line.Text))
        }
    }
}

if ($badCalloutMatches.Count -gt 0) {
    $violations.Add(
        "[wiki-syntax-check] VIOLATION 4: 使用了未允许的 Obsidian callout 类型。只能使用官方 callout 类型，或 vault 自定义 contradiction`n    " +
        ($badCalloutMatches -join "`n    ")
    )
}

if ($violations.Count -gt 0) {
    $reason = "wiki/ Markdown 写入校验失败，请先修正后继续。`n`n" + ($violations -join "`n`n")
    $payload = @{
        decision = "block"
        reason = $reason
    } | ConvertTo-Json -Compress

    Write-Output $payload
}

exit 0
