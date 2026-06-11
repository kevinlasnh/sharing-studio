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
            $violations.Add("[wiki-syntax-check] VIOLATION 0A: wiki domain directory must be lowercase English kebab-case: $domain")
        }
    } elseif ($VaultPath -match '^wiki/([^/]+)/([^/]+)\.md$') {
        $domain = $Matches[1]
        $slug = $Matches[2]
        if ($domain -cnotmatch $domainPattern) {
            $violations.Add("[wiki-syntax-check] VIOLATION 0A: wiki domain directory must be lowercase English kebab-case: $domain")
        }
        if ($slug -cnotmatch $slugPattern) {
            $violations.Add("[wiki-syntax-check] VIOLATION 0B: wiki content filename must be lowercase English kebab-case: $slug.md")
        }
    } else {
        $violations.Add("[wiki-syntax-check] VIOLATION 0C: wiki markdown path must be wiki/{domain}/_index.md or wiki/{domain}/{slug}.md")
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
        if ($lines[$i].Trim() -eq "---") {
            return $null
        }
        if ($Lines[$i] -match "^$([regex]::Escape($Key)):\s*(.*)$") {
            return $Matches[1].Trim().Trim("'`"")
        }
    }
    return $null
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
$vaultPath = Get-VaultRelativePath -PathText $filePath
foreach ($violation in (Test-WikiPathSchema -VaultPath $vaultPath)) {
    $violations.Add($violation)
}

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

$expectedPermalink = Get-ExpectedPermalink -PathText $filePath
if (-not [string]::IsNullOrWhiteSpace($expectedPermalink)) {
    $actualPermalink = Get-FrontmatterScalar -Lines $lines -Key "permalink"
    if ([string]::IsNullOrWhiteSpace($actualPermalink)) {
        $violations.Add("[wiki-syntax-check] VIOLATION 2C: frontmatter 缺少路径确定性 permalink。应为: $expectedPermalink")
    } elseif ($actualPermalink -ne $expectedPermalink) {
        $violations.Add("[wiki-syntax-check] VIOLATION 2D: permalink 与路径不一致。应为: $expectedPermalink；实际: $actualPermalink")
    }
}

foreach ($requiredKey in @("title", "type", "permalink")) {
    $value = Get-FrontmatterScalar -Lines $lines -Key $requiredKey
    if ([string]::IsNullOrWhiteSpace($value)) {
        $violations.Add("[wiki-syntax-check] VIOLATION 2E: frontmatter 缺少必需字段 '$requiredKey'")
    }
}

$actualType = Get-FrontmatterScalar -Lines $lines -Key "type"
if ($vaultPath -match '^wiki/[^/]+/_index\.md$' -and $actualType -ne "index") {
    $violations.Add("[wiki-syntax-check] VIOLATION 2F: domain index frontmatter type must be 'index'")
} elseif ($vaultPath -match '^wiki/[^/]+/[^/]+\.md$' -and $vaultPath -notmatch '/_index\.md$' -and $actualType -eq "index") {
    $violations.Add("[wiki-syntax-check] VIOLATION 2G: wiki content page frontmatter type must not be 'index'")
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
