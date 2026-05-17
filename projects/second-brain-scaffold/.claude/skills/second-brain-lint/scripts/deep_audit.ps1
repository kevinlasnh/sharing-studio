param(
    [string]$VaultRoot = ".",
    [switch]$SkipBasicMemory
)

$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()

$resolvedRoot = (Get-Item -LiteralPath (Resolve-Path -LiteralPath $VaultRoot).Path).FullName

function Convert-ToVaultPath {
    param([string]$PathText)

    $fullPath = ([System.IO.Path]::GetFullPath($PathText) -replace "\\", "/").TrimEnd("/")
    $rootNorm = ($resolvedRoot -replace "\\", "/").TrimEnd("/")
    $rootWithSlash = $rootNorm + "/"

    if ($fullPath.StartsWith($rootWithSlash, [System.StringComparison]::OrdinalIgnoreCase)) {
        $relative = $fullPath.Substring($rootWithSlash.Length)
    } elseif ($fullPath.Equals($rootNorm, [System.StringComparison]::OrdinalIgnoreCase)) {
        $relative = ""
    } else {
        $relative = $fullPath
    }

    return $relative
}

function Get-PageKind {
    param([string]$VaultPath)

    if ($VaultPath -eq "index.md") { return "root-index" }
    if ($VaultPath -like "daily/*.md") { return "daily" }
    if ($VaultPath -like "wiki/*/_index.md") { return "domain-index" }
    if ($VaultPath -like "wiki/*/*.md") { return "content" }
    return "other"
}

function Get-Domain {
    param([string]$VaultPath)

    if ($VaultPath -match '^wiki/([^/]+)/') { return $Matches[1] }
    return $null
}

function Get-ItemCount {
    param($Value)

    if ($null -eq $Value) {
        return 0
    }
    if ($Value -is [System.Collections.ICollection]) {
        return [int]$Value.Count
    }
    return @($Value).Count
}

function Get-FrontmatterInfo {
    param([string]$PathText)

    $text = Get-Content -LiteralPath $PathText -Raw -Encoding UTF8
    $lines = $text -split "`r?`n"
    $result = [ordered]@{
        has_frontmatter = $false
        close_line = 0
        keys = @()
        values = @{}
        first_line = if ($lines.Count -gt 0) { $lines[0].Trim() } else { "" }
    }

    if ($lines.Count -eq 0 -or $lines[0].Trim() -ne "---") {
        return [pscustomobject]$result
    }

    $result.has_frontmatter = $true
    for ($i = 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -eq "---") {
            $result.close_line = $i + 1
            break
        }
        if ($lines[$i] -match '^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$') {
            $key = $Matches[1]
            $result.keys += $key
            $result.values[$key] = $Matches[2]
        }
    }

    return [pscustomobject]$result
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
        $result.Add([pscustomobject]@{ Number = $i + 1; Text = (Remove-InlineCode $line) })
    }
    return $result
}

function Test-RawContext {
    param([string]$LineText)

    $contextText = [regex]::Replace(
        $LineText,
        '!?\[\[[^\]]*raw[/\\][^\]]+\]\]',
        '[rawlink]',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    $lower = $contextText.ToLowerInvariant()
    $forbiddenPattern = '(related|recommended|recommendation|further reading|see also|navigation|graph|connectivity|same batch|same-batch|batch ingest|相关|推荐|延伸阅读|参见|导航|图谱|连通|同批)'
    if ($lower -match $forbiddenPattern) {
        return "raw wikilinks must not be used for related/recommended/navigation/graph/same-batch context"
    }

    $provenancePattern = '(source|evidence|provenance|original|attachment|file|document|report|dataset|archive|citation|preserved|provided|supplied|supports|based on|来源|证据|出处|原始|原文|素材|附件|文件|文档|报告|数据集|存档|引用|凭据|保留|用户提供|支撑|基于)'
    if ($lower -notmatch $provenancePattern) {
        return "raw wikilinks must appear in an explicit source/evidence/provenance sentence"
    }

    return $null
}

function Test-RawForbiddenContext {
    param([string]$LineText)

    $contextText = [regex]::Replace(
        $LineText,
        '!?\[\[[^\]]*raw[/\\][^\]]+\]\]',
        '[rawlink]',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    $lower = $contextText.ToLowerInvariant()
    $forbiddenPattern = '(related|recommended|recommendation|further reading|see also|navigation|graph|connectivity|same batch|same-batch|batch ingest|相关|推荐|延伸阅读|参见|导航|图谱|连通|同批)'
    if ($lower -match $forbiddenPattern) {
        return "raw image embeds must not be used for related/recommended/navigation/graph/same-batch context"
    }

    return $null
}

function Test-ProvenanceContext {
    param([string]$LineText)

    $contextText = [regex]::Replace(
        $LineText,
        '!?\[\[[^\]]+\]\]|!?\[[^\]]*\]\([^)]+\)',
        '[link]',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    $lower = $contextText.ToLowerInvariant()
    $provenancePattern = '(source|evidence|provenance|original|attachment|file|document|report|dataset|archive|citation|preserved|provided|supplied|supports|based on|来源|证据|出处|原始|原文|素材|附件|文件|文档|报告|数据集|存档|引用|凭据|保留|用户提供|支撑|基于)'
    return ($lower -match $provenancePattern)
}

function Normalize-LinkTarget {
    param([string]$Target)

    $normalized = ($Target -replace "\\", "/").Trim().Trim("<", ">")
    try {
        $normalized = [System.Uri]::UnescapeDataString($normalized)
    } catch {
        # Keep the original target if percent decoding fails.
    }

    return $normalized
}

$script:RawFileBasenameMap = $null
function Get-RawFileBasenameMap {
    if ($null -ne $script:RawFileBasenameMap) {
        return $script:RawFileBasenameMap
    }

    $script:RawFileBasenameMap = @{}
    $rawRoot = Join-Path -Path $resolvedRoot -ChildPath "raw"
    if (Test-Path -LiteralPath $rawRoot -PathType Container) {
        foreach ($file in Get-ChildItem -LiteralPath $rawRoot -Recurse -File -ErrorAction SilentlyContinue) {
            $key = $file.Name.ToLowerInvariant()
            if (-not $script:RawFileBasenameMap.ContainsKey($key)) {
                $script:RawFileBasenameMap[$key] = (Convert-ToVaultPath $file.FullName).ToLowerInvariant()
            }
        }
    }

    return $script:RawFileBasenameMap
}

function Get-RawTargetInfo {
    param([string]$Target)

    $inputNormalized = ($Target -replace "\\", "/").Trim().Trim("<", ">")
    $normalized = Normalize-LinkTarget $Target
    $lower = $normalized.ToLowerInvariant()
    $candidate = $lower.TrimStart("/")
    while ($candidate.StartsWith("./", [System.StringComparison]::Ordinal)) {
        $candidate = $candidate.Substring(2)
    }

    $rawPath = $null
    if ($candidate.StartsWith("raw/", [System.StringComparison]::Ordinal)) {
        $rawPath = $candidate
    } elseif ($lower -match '(^|/)(?:\.\./)+raw/(.+)$') {
        $rawPath = "raw/" + $Matches[2]
    } elseif ($lower -match '(^|/)\./raw/(.+)$') {
        $rawPath = "raw/" + $Matches[2]
    } elseif ($lower -match '(^|/)raw/(.+)$') {
        $rawPath = "raw/" + $Matches[2]
    }

    $isBasenameReference = $false
    if ($null -eq $rawPath -and $normalized -notmatch '/' -and -not [string]::IsNullOrWhiteSpace($normalized)) {
        $rawMap = Get-RawFileBasenameMap
        $basenameKey = [System.IO.Path]::GetFileName($normalized).ToLowerInvariant()
        if ($rawMap.ContainsKey($basenameKey)) {
            $rawPath = $rawMap[$basenameKey]
            $isBasenameReference = $true
        }
    }

    [pscustomobject]@{
        IsRawLike = ($null -ne $rawPath)
        IsCanonical = (-not $isBasenameReference -and $inputNormalized.StartsWith("raw/", [System.StringComparison]::Ordinal) -and $inputNormalized -eq $normalized)
        RawPath = $rawPath
        Normalized = $normalized
        IsBasenameReference = $isBasenameReference
    }
}

function Test-LocalAttachmentTarget {
    param([string]$Target)

    $normalized = Normalize-LinkTarget $Target
    $cleanTarget = (($normalized -split '[?#]', 2)[0]).ToLowerInvariant()
    return ($cleanTarget -match '\.(pdf|txt|docx|xlsx|xls|csv|png|jpg|jpeg|webp|gif|mp3|mp4|zip|json)$')
}

function Test-RawImagePath {
    param([string]$RawPath)

    if ([string]::IsNullOrWhiteSpace($RawPath)) {
        return $false
    }

    $cleanPath = (($RawPath -split '[?#]', 2)[0]).ToLowerInvariant()
    return ($cleanPath -match '\.(png|jpg|jpeg|webp|gif)$')
}

function Get-RawImageDimensions {
    param([string]$RawPath)

    $cleanPath = (($RawPath -split '[?#]', 2)[0])
    if ([string]::IsNullOrWhiteSpace($cleanPath)) {
        return $null
    }

    $fullPath = Join-Path -Path $resolvedRoot -ChildPath $cleanPath
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        return $null
    }

    $ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $ffprobe) {
        try {
            $dimensionText = & $ffprobe.Source -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 $fullPath 2>$null |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
                Select-Object -First 1
            if ($dimensionText -match '^(\d+)x(\d+)$') {
                return [pscustomobject]@{ Width = [int]$Matches[1]; Height = [int]$Matches[2] }
            }
        } catch {
            # Fall through to System.Drawing for formats it can decode.
        }
    }

    try {
        Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
        $image = [System.Drawing.Image]::FromFile($fullPath)
        try {
            return [pscustomobject]@{ Width = [int]$image.Width; Height = [int]$image.Height }
        } finally {
            $image.Dispose()
        }
    } catch {
        return $null
    }
}

function Get-ExpectedRawImageDisplayWidth {
    param([string]$RawPath)

    $dimensions = Get-RawImageDimensions -RawPath $RawPath
    if ($null -eq $dimensions) {
        return $null
    }
    if ([int]$dimensions.Width -lt [int]$dimensions.Height) {
        return 360
    }
    return 600
}

function Test-RawImageDisplayWidth {
    param(
        [string]$RawPath,
        [string]$Display
    )

    if ([string]::IsNullOrWhiteSpace($Display)) {
        return "raw image embeds must include explicit width: use |360 for portrait images and |600 for landscape or square images"
    }

    $trimmed = $Display.Trim()
    if ($trimmed -notmatch '^\d+$') {
        return "raw image embed width must be a single numeric width, not '$trimmed'"
    }

    $actual = [int]$trimmed
    $expected = Get-ExpectedRawImageDisplayWidth -RawPath $RawPath
    if ($null -eq $expected) {
        if (@(360, 600) -notcontains $actual) {
            return "raw image embed width must be |360 or |600 when image dimensions cannot be read"
        }
        return $null
    }

    if ($actual -ne [int]$expected) {
        return "raw image embed width must be |$expected for this image orientation, got |$actual"
    }

    return $null
}

$allMarkdownFiles = Get-ChildItem -LiteralPath $resolvedRoot -Recurse -Filter "*.md" -File |
    Where-Object {
        $vaultPath = Convert-ToVaultPath $_.FullName
        $vaultPath -notmatch '^\.claude/'
    }

$wikiMarkdownFiles = $allMarkdownFiles |
    Where-Object {
        $vaultPath = Convert-ToVaultPath $_.FullName
        $vaultPath -like "wiki/*/*.md" -or $vaultPath -like "wiki/*.md"
    }

$exportScript = Join-Path -Path $resolvedRoot -ChildPath ".claude\skills\second-brain-lint\scripts\export_links.ps1"
$links = @()
if (Test-Path -LiteralPath $exportScript -PathType Leaf) {
    $linksJson = & powershell -NoProfile -ExecutionPolicy Bypass -File $exportScript -VaultRoot $resolvedRoot
    if (-not [string]::IsNullOrWhiteSpace($linksJson)) {
        $linksText = ($linksJson -join "`n")
        $parsedLinks = $linksText | ConvertFrom-Json
        $links = @($parsedLinks)
    }
}

$frontmatterIssues = New-Object System.Collections.Generic.List[object]
$filenameIssues = New-Object System.Collections.Generic.List[object]
$titleLooksSlug = New-Object System.Collections.Generic.List[object]

foreach ($file in $wikiMarkdownFiles) {
    $vaultPath = Convert-ToVaultPath $file.FullName
    $kind = Get-PageKind $vaultPath
    $domain = Get-Domain $vaultPath
    $frontmatter = Get-FrontmatterInfo $file.FullName

    if (-not $frontmatter.has_frontmatter -or $frontmatter.close_line -eq 0) {
        $frontmatterIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "missing-or-unclosed-frontmatter" })
        continue
    }

    $keys = @($frontmatter.keys)
    if ($kind -eq "domain-index") {
        foreach ($required in @("title", "type", "domain", "created", "updated")) {
            if ($keys -notcontains $required) {
                $frontmatterIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "missing $required" })
            }
        }
        foreach ($forbidden in @("source_type", "source_date", "confidence", "related")) {
            if ($keys -contains $forbidden) {
                $frontmatterIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "forbidden $forbidden on _index" })
            }
        }
        if ($frontmatter.values["type"] -and $frontmatter.values["type"].Trim() -ne "index") {
            $frontmatterIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "type is not index" })
        }
        if ($frontmatter.values["domain"] -and $frontmatter.values["domain"].Trim() -ne $domain) {
            $frontmatterIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "domain mismatch: $($frontmatter.values['domain']) vs $domain" })
        }
    } elseif ($kind -eq "content") {
        foreach ($required in @("title", "type", "domain", "created", "updated")) {
            if ($keys -notcontains $required) {
                $frontmatterIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "missing $required" })
            }
        }
        foreach ($required in @("source_type", "source_date", "confidence", "tags")) {
            if ($keys -notcontains $required) {
                $frontmatterIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "missing ingest field $required" })
            }
        }
        if ($frontmatter.values["domain"] -and $frontmatter.values["domain"].Trim() -ne $domain) {
            $frontmatterIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "domain mismatch: $($frontmatter.values['domain']) vs $domain" })
        }
        if ($frontmatter.values["type"] -and @("concept", "entity", "comparison", "procedure", "reference") -notcontains $frontmatter.values["type"].Trim()) {
            $frontmatterIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "unexpected type $($frontmatter.values['type'])" })
        }

        $slug = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        $title = if ($frontmatter.values["title"]) { $frontmatter.values["title"].Trim() } else { "" }
        if ($title -and ($title -ceq $slug -or $title -cmatch '^[a-z0-9]+(?:-[a-z0-9]+)+$')) {
            $titleLooksSlug.Add([pscustomobject]@{ file = $vaultPath; title = $frontmatter.values["title"].Trim() })
        }
    }

    if ($kind -eq "content" -and $file.Name -notmatch '^[a-z0-9]+(?:-[a-z0-9]+)*\.md$') {
        $filenameIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "content filename not lowercase English kebab-case" })
    }
    if ($kind -eq "domain-index" -and $file.Name -ne "_index.md") {
        $filenameIssues.Add([pscustomobject]@{ file = $vaultPath; issue = "domain index filename not _index.md" })
    }
}

$allPaths = Get-ChildItem -LiteralPath $resolvedRoot -Recurse -File -Force |
    ForEach-Object { Convert-ToVaultPath $_.FullName }

$forbiddenScaffold = @()
foreach ($path in $allPaths) {
    if ($path -in @("wiki/log.md", "wiki/hot.md", "wiki/ingest-log.md", "wiki/overview.md", "wiki/index.md", "wiki/meta/dashboard.md", "wiki/meta/overview.canvas")) {
        $forbiddenScaffold += $path
    } elseif ($path -match '^wiki/sources/' -or $path -match '^\.raw/' -or $path -match '^wiki/.+\.canvas$' -or $path -match '^wiki/meta/lint-report.*\.md$') {
        $forbiddenScaffold += $path
    }
}

$rawMarkdownFiles = @($allMarkdownFiles |
    Where-Object { (Convert-ToVaultPath $_.FullName) -match '^raw/.+\.md$' } |
    ForEach-Object { [pscustomobject]@{ file = Convert-ToVaultPath $_.FullName; issue = "raw/ must not store Markdown notes; store as .txt/.pdf/original attachment or ingest into wiki" } })

$graphConfigIssues = New-Object System.Collections.Generic.List[object]
$graphPath = Join-Path -Path $resolvedRoot -ChildPath ".obsidian\graph.json"
$expectedGraphGroups = @(
    [pscustomobject]@{ query = 'file:index -file:_index'; rgb = 5682409 },
    [pscustomobject]@{ query = 'file:CLAUDE OR file:AGENTS OR file:GEMINI'; rgb = 13983232 },
    [pscustomobject]@{ query = 'file:_index'; rgb = 29362 },
    [pscustomobject]@{ query = 'path:"daily/"'; rgb = 15787074 },
    [pscustomobject]@{ query = 'path:"wiki/"'; rgb = 40563 }
)
$graphSnippetName = "second-brain-graph-colors"
$graphSnippetPath = Join-Path -Path $resolvedRoot -ChildPath ".obsidian\snippets\$graphSnippetName.css"
$imageDisplaySnippetName = "second-brain-markdown-images"
$imageDisplaySnippetPath = Join-Path -Path $resolvedRoot -ChildPath ".obsidian\snippets\$imageDisplaySnippetName.css"
$markdownImageDisplayIssues = New-Object System.Collections.Generic.List[object]
$appearancePath = Join-Path -Path $resolvedRoot -ChildPath ".obsidian\appearance.json"

if (-not (Test-Path -LiteralPath $graphPath -PathType Leaf)) {
    $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/graph.json"; issue = "missing graph config" })
} else {
    try {
        $graphConfig = Get-Content -LiteralPath $graphPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
        $actualGroups = @($graphConfig.colorGroups)
        if ($actualGroups.Count -ne $expectedGraphGroups.Count) {
            $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/graph.json"; issue = "colorGroups count must be $($expectedGraphGroups.Count)"; actual = $actualGroups.Count })
        }

        $groupCheckLimit = [Math]::Min($actualGroups.Count, $expectedGraphGroups.Count)
        for ($i = 0; $i -lt $groupCheckLimit; $i++) {
            $actual = $actualGroups[$i]
            $expected = $expectedGraphGroups[$i]
            if ([string]$actual.query -ne $expected.query) {
                $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/graph.json"; issue = "colorGroups[$i].query mismatch"; expected = $expected.query; actual = [string]$actual.query })
            }
            if ([int]$actual.color.rgb -ne [int]$expected.rgb) {
                $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/graph.json"; issue = "colorGroups[$i].color.rgb mismatch"; expected = [int]$expected.rgb; actual = [int]$actual.color.rgb })
            }
            if ([double]$actual.color.a -ne 1) {
                $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/graph.json"; issue = "colorGroups[$i].color.a must be 1"; actual = [double]$actual.color.a })
            }
        }
    } catch {
        $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/graph.json"; issue = "invalid graph config json"; error = $_.Exception.Message })
    }
}
if (-not (Test-Path -LiteralPath $graphSnippetPath -PathType Leaf)) {
    $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/snippets/$graphSnippetName.css"; issue = "missing graph attachment color snippet" })
} else {
    $graphSnippetContent = Get-Content -LiteralPath $graphSnippetPath -Raw -Encoding UTF8
    if ($graphSnippetContent -notmatch '--graph-node-attachment\s*:\s*#CC79A7\s*;') {
        $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/snippets/$graphSnippetName.css"; issue = "attachment node color must be #CC79A7" })
    }
}
if (-not (Test-Path -LiteralPath $imageDisplaySnippetPath -PathType Leaf)) {
    $markdownImageDisplayIssues.Add([pscustomobject]@{ file = ".obsidian/snippets/$imageDisplaySnippetName.css"; issue = "missing Markdown image centering snippet" })
} else {
    $imageDisplaySnippetContent = Get-Content -LiteralPath $imageDisplaySnippetPath -Raw -Encoding UTF8
    if ($imageDisplaySnippetContent -notmatch '\.image-embed') {
        $markdownImageDisplayIssues.Add([pscustomobject]@{ file = ".obsidian/snippets/$imageDisplaySnippetName.css"; issue = "snippet must target Obsidian image embeds with .image-embed" })
    }
    if ($imageDisplaySnippetContent -notmatch 'margin-inline\s*:\s*auto' -and $imageDisplaySnippetContent -notmatch 'margin-left\s*:\s*auto[\s\S]*margin-right\s*:\s*auto') {
        $markdownImageDisplayIssues.Add([pscustomobject]@{ file = ".obsidian/snippets/$imageDisplaySnippetName.css"; issue = "snippet must center images with automatic horizontal margins" })
    }
    if ($imageDisplaySnippetContent -notmatch 'img:only-child') {
        $markdownImageDisplayIssues.Add([pscustomobject]@{ file = ".obsidian/snippets/$imageDisplaySnippetName.css"; issue = "snippet must handle standalone Markdown images, not only Obsidian embeds" })
    }
}
if (-not (Test-Path -LiteralPath $appearancePath -PathType Leaf)) {
    $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/appearance.json"; issue = "missing appearance config" })
    $markdownImageDisplayIssues.Add([pscustomobject]@{ file = ".obsidian/appearance.json"; issue = "missing appearance config" })
} else {
    try {
        $appearanceConfig = Get-Content -LiteralPath $appearancePath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
        $enabledSnippets = @($appearanceConfig.enabledCssSnippets)
        if ($graphSnippetName -notin $enabledSnippets) {
            $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/appearance.json"; issue = "enabledCssSnippets must include $graphSnippetName" })
        }
        if ($imageDisplaySnippetName -notin $enabledSnippets) {
            $markdownImageDisplayIssues.Add([pscustomobject]@{ file = ".obsidian/appearance.json"; issue = "enabledCssSnippets must include $imageDisplaySnippetName" })
        }
    } catch {
        $graphConfigIssues.Add([pscustomobject]@{ file = ".obsidian/appearance.json"; issue = "invalid appearance config json"; error = $_.Exception.Message })
        $markdownImageDisplayIssues.Add([pscustomobject]@{ file = ".obsidian/appearance.json"; issue = "invalid appearance config json"; error = $_.Exception.Message })
    }
}

$deadLinks = @($links | Where-Object {
    $rawTargetInfo = Get-RawTargetInfo -Target ([string]$_.target)
    -not $_.target_exists -and -not ($rawTargetInfo.IsCanonical -and (Test-Path -LiteralPath (Join-Path $resolvedRoot $rawTargetInfo.RawPath)))
})
$rootIndexLinkViolations = @($links | Where-Object { $_.source_kind -eq "root-index" -and ($_.target_path -notmatch '^wiki/[^/]+/_index\.md$') })
$domainIndexLinkViolations = @($links | Where-Object { $_.source_kind -eq "domain-index" -and -not ($_.target_path -match '^wiki/[^/]+/[^/]+\.md$' -and $_.target_path -notmatch '/_index\.md$' -and $_.same_domain) })
$dailyLinkViolations = @($links | Where-Object { $_.source_kind -eq "daily" })

$rawLinkBoundaryViolations = New-Object System.Collections.Generic.List[object]
foreach ($link in @($links)) {
    $rawTargetInfo = Get-RawTargetInfo -Target ([string]$link.target)
    if (-not $rawTargetInfo.IsRawLike) {
        if ((Test-LocalAttachmentTarget -Target ([string]$link.target)) -and (Test-ProvenanceContext -LineText ([string]$link.context))) {
            $rawLinkBoundaryViolations.Add([pscustomobject]@{
                source = $link.source
                target = $link.target
                line = $link.line
                context = $link.context
                issue = "source/evidence/provenance attachments must use canonical raw wikilinks such as [[raw/file.ext]], not bare attachment wikilinks or non-canonical embeds"
                link_type = "source-attachment-noncanonical"
            })
        }
        continue
    }

    $isEmbeddedRawReference = ($link.PSObject.Properties.Name -contains "embedded" -and [bool]$link.embedded)
    $isRawImageEmbed = $isEmbeddedRawReference -and (Test-RawImagePath -RawPath $rawTargetInfo.RawPath)

    if ($isEmbeddedRawReference -and -not $isRawImageEmbed) {
        $rawLinkBoundaryViolations.Add([pscustomobject]@{
            source = $link.source
            target = $link.target
            line = $link.line
            context = $link.context
            issue = "raw embeds are allowed only for image files (.png/.jpg/.jpeg/.webp/.gif); cite non-image raw files as plain provenance wikilinks"
            link_type = "raw-nonimage-embed"
        })
    }

    if ($rawTargetInfo.IsBasenameReference) {
        $rawLinkBoundaryViolations.Add([pscustomobject]@{
            source = $link.source
            target = $link.target
            line = $link.line
            context = $link.context
            issue = "raw files must not be linked by bare attachment basename; use canonical [[raw/file.ext]] so the provenance edge is explicit"
            link_type = "raw-basename-target"
        })
    }

    if (-not $rawTargetInfo.IsCanonical) {
        $rawLinkBoundaryViolations.Add([pscustomobject]@{
            source = $link.source
            target = $link.target
            line = $link.line
            context = $link.context
            issue = "raw wikilinks must use canonical vault-root lowercase path syntax [[raw/file.ext]], not relative, absolute, encoded, or differently cased variants"
            link_type = "raw-noncanonical-target"
        })
    }

    if ($rawTargetInfo.RawPath -match '\.md$') {
        $rawLinkBoundaryViolations.Add([pscustomobject]@{
            source = $link.source
            target = $link.target
            line = $link.line
            context = $link.context
            issue = "raw Markdown targets are forbidden; use .txt/.pdf/original attachment or ingest into wiki"
            link_type = "raw-markdown-target"
        })
    }

    if ($link.source_kind -ne "content") {
        $rawLinkBoundaryViolations.Add([pscustomobject]@{
            source = $link.source
            target = $link.target
            line = $link.line
            context = $link.context
            issue = "raw wikilink is allowed only from wiki content page body text"
            link_type = "raw-wikilink"
        })
    } elseif ($link.frontmatter_only) {
        $rawLinkBoundaryViolations.Add([pscustomobject]@{
            source = $link.source
            target = $link.target
            line = $link.line
            context = $link.context
            issue = "raw wikilink must not be in frontmatter; keep it in a body source/evidence sentence"
            link_type = "raw-frontmatter-wikilink"
        })
    } else {
        if ($isRawImageEmbed) {
            $display = if ($link.PSObject.Properties.Name -contains "display") { [string]$link.display } else { $null }
            $widthIssue = Test-RawImageDisplayWidth -RawPath $rawTargetInfo.RawPath -Display $display
            if ($null -ne $widthIssue) {
                $rawLinkBoundaryViolations.Add([pscustomobject]@{
                    source = $link.source
                    target = $link.target
                    line = $link.line
                    context = $link.context
                    issue = $widthIssue
                    link_type = "raw-image-embed-width"
                    display = $display
                })
            }
            $contextIssue = Test-RawForbiddenContext -LineText ([string]$link.context)
            if ($null -ne $contextIssue) {
                $rawLinkBoundaryViolations.Add([pscustomobject]@{
                    source = $link.source
                    target = $link.target
                    line = $link.line
                    context = $link.context
                    issue = $contextIssue
                    link_type = "raw-image-embed-context"
                })
            }
        } else {
            $contextIssue = Test-RawContext -LineText ([string]$link.context)
            if ($null -ne $contextIssue) {
                $rawLinkBoundaryViolations.Add([pscustomobject]@{
                    source = $link.source
                    target = $link.target
                    line = $link.line
                    context = $link.context
                    issue = $contextIssue
                    link_type = "raw-context"
                })
            }
        }
    }
}

$frontmatterOnlyUnsupported = New-Object System.Collections.Generic.List[object]
$frontmatterGroups = $links | Where-Object { $_.source_kind -eq "content" -and $_.frontmatter_only -and $_.target_path } | Group-Object source, target_path
foreach ($group in $frontmatterGroups) {
    $sample = $group.Group[0]
    $hasBodySupport = @($links | Where-Object { $_.source -eq $sample.source -and $_.target_path -eq $sample.target_path -and -not $_.frontmatter_only }).Count -gt 0
    if (-not $hasBodySupport) {
        $frontmatterOnlyUnsupported.Add([pscustomobject]@{ source = $sample.source; target = $sample.target_path; line = $sample.line })
    }
}

$contentPagesWithoutContentInbound = New-Object System.Collections.Generic.List[object]
$contentPagePaths = @($wikiMarkdownFiles |
    Where-Object { (Get-PageKind (Convert-ToVaultPath $_.FullName)) -eq "content" } |
    ForEach-Object { Convert-ToVaultPath $_.FullName })
foreach ($contentPage in $contentPagePaths) {
    $inbound = @($links | Where-Object {
        $_.target_path -eq $contentPage -and
        $_.source -ne $contentPage -and
        $_.source_kind -eq "content"
    })
    if ($inbound.Count -eq 0) {
        $contentPagesWithoutContentInbound.Add([pscustomobject]@{ file = $contentPage; note = "no inbound links from wiki content pages; domain _index.md navigation may still cover it" })
    }
}

$duplicateBasenames = @($allMarkdownFiles |
    ForEach-Object { [pscustomobject]@{ basename = [System.IO.Path]::GetFileNameWithoutExtension($_.Name); path = Convert-ToVaultPath $_.FullName } } |
    Where-Object { $_.basename -ne "_index" } |
    Group-Object basename |
    Where-Object { $_.Count -gt 1 } |
    ForEach-Object { [pscustomobject]@{ basename = $_.Name; paths = @($_.Group.path) } })

$standardInternalMarkdownLinks = New-Object System.Collections.Generic.List[object]
$dailyMarkdownLinkViolations = New-Object System.Collections.Generic.List[object]
$rawMarkdownLinkViolations = New-Object System.Collections.Generic.List[object]
$inlineYamlArrays = New-Object System.Collections.Generic.List[object]
$badCallouts = New-Object System.Collections.Generic.List[object]
$allowedCallouts = @(
    "note", "abstract", "summary", "tldr", "info", "todo", "tip", "hint", "important",
    "success", "check", "done", "question", "help", "faq", "warning", "caution",
    "attention", "failure", "fail", "missing", "danger", "error", "bug", "example",
    "quote", "cite", "contradiction"
)

foreach ($file in $wikiMarkdownFiles) {
    $vaultPath = Convert-ToVaultPath $file.FullName
    $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    $lines = $text -split "`r?`n"
    $visibleLines = Get-VisibleLines $lines

    foreach ($line in $visibleLines) {
        if ($line.Text -match '\[[^\]]+\]\((?!https?://)[^)]*\.md[^)]*\)') {
            $standardInternalMarkdownLinks.Add([pscustomobject]@{ file = $vaultPath; line = $line.Number; text = $line.Text.Trim() })
        }
        $calloutMatch = [regex]::Match($line.Text, '^\s*>\s*\[!([^\]\+\-]+)')
        if ($calloutMatch.Success) {
            $calloutType = $calloutMatch.Groups[1].Value.Trim().ToLowerInvariant()
            if ($allowedCallouts -notcontains $calloutType) {
                $badCallouts.Add([pscustomobject]@{ file = $vaultPath; line = $line.Number; type = $calloutType })
            }
        }
    }

    $scanLimit = [Math]::Min(40, $lines.Count)
    for ($i = 0; $i -lt $scanLimit; $i++) {
        if ($lines[$i] -match '^(tags|aliases|cssclasses|related):\s*\[') {
            $inlineYamlArrays.Add([pscustomobject]@{ file = $vaultPath; line = $i + 1; text = $lines[$i].Trim() })
        }
    }
}

$dailyMarkdownFiles = $allMarkdownFiles |
    Where-Object { (Convert-ToVaultPath $_.FullName) -like "daily/*.md" }

foreach ($file in $dailyMarkdownFiles) {
    $vaultPath = Convert-ToVaultPath $file.FullName
    $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    $lines = $text -split "`r?`n"
    $visibleLines = Get-VisibleLines $lines

    foreach ($line in $visibleLines) {
        if ([regex]::IsMatch($line.Text, '!?\[[^\]]*\]\((?!https?://)[^)]*\)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
            $dailyMarkdownLinkViolations.Add([pscustomobject]@{
                source = $vaultPath
                target = $null
                line = $line.Number
                context = $line.Text.Trim()
                target_path = $null
                link_type = "local-or-relative-markdown"
            })
        }
    }
}

foreach ($file in $allMarkdownFiles) {
    $vaultPath = Convert-ToVaultPath $file.FullName
    $sourceKind = Get-PageKind $vaultPath
    $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    $lines = $text -split "`r?`n"
    $visibleLines = Get-VisibleLines $lines
    $localMarkdownLinkPattern = [regex]::new('!?\[[^\]]*\]\((?!https?://)([^)\s]+)[^)]*\)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)

    foreach ($line in $visibleLines) {
        foreach ($match in $localMarkdownLinkPattern.Matches($line.Text)) {
            $rawTargetInfo = Get-RawTargetInfo -Target $match.Groups[1].Value
            if ($rawTargetInfo.IsRawLike) {
                $rawMarkdownLinkViolations.Add([pscustomobject]@{
                    source = $vaultPath
                    target = $null
                    line = $line.Number
                    context = $line.Text.Trim()
                    issue = "raw files must be referenced as Obsidian wikilinks from wiki content page bodies, not local Markdown links"
                    link_type = "raw-local-markdown-link"
                    source_kind = $sourceKind
                })
            } elseif ((Test-LocalAttachmentTarget -Target $match.Groups[1].Value) -and (Test-ProvenanceContext -LineText $line.Text)) {
                $rawMarkdownLinkViolations.Add([pscustomobject]@{
                    source = $vaultPath
                    target = $match.Groups[1].Value
                    line = $line.Number
            context = $line.Text.Trim()
            issue = "source/evidence/provenance attachments must use canonical raw wikilinks such as [[raw/file.ext]], not local Markdown attachment links"
            link_type = "source-attachment-local-markdown-link"
                    source_kind = $sourceKind
                })
            }
        }
    }
}

$rootIndexDomains = @()
$rootIndexPath = Join-Path -Path $resolvedRoot -ChildPath "index.md"
if (Test-Path -LiteralPath $rootIndexPath -PathType Leaf) {
    $rootIndexLines = Get-Content -LiteralPath $rootIndexPath -Encoding UTF8
    foreach ($line in $rootIndexLines) {
        if ($line -match '^\s*<!--.*-->\s*$') { continue }
        $matches = [regex]::Matches($line, '\[\[wiki/([^/]+)/_index')
        foreach ($match in $matches) {
            $rootIndexDomains += $match.Groups[1].Value
        }
    }
}

$domainDirs = @(Get-ChildItem -LiteralPath (Join-Path $resolvedRoot "wiki") -Directory | ForEach-Object { $_.Name })
$missingRootIndexDomains = @($domainDirs | Where-Object { $rootIndexDomains -notcontains $_ })
$staleRootIndexDomains = @($rootIndexDomains | Where-Object { $domainDirs -notcontains $_ })

$domainIndexCoverageIssues = New-Object System.Collections.Generic.List[object]
$domainSummaryIssues = New-Object System.Collections.Generic.List[object]
foreach ($domain in $domainDirs) {
    $indexPath = Join-Path -Path $resolvedRoot -ChildPath "wiki\$domain\_index.md"
    if (-not (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
        $domainIndexCoverageIssues.Add([pscustomobject]@{ domain = $domain; issue = "missing _index.md" })
        continue
    }
    $indexText = Get-Content -LiteralPath $indexPath -Raw -Encoding UTF8
    $indexLines = $indexText -split "`r?`n"
    $hasScopeSummary = $false
    foreach ($line in $indexLines) {
        $trimmed = $line.Trim()
        if ($trimmed -eq "---") { continue }
        if ($trimmed -match '^[A-Za-z_][A-Za-z0-9_-]*:') { continue }
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        if ($trimmed -match '^#') { continue }
        if ($trimmed -match '^> \S') {
            $hasScopeSummary = $true
            break
        }
        if ($trimmed -match '^- \[\[') { break }
    }
    if (-not $hasScopeSummary) {
        $domainSummaryIssues.Add([pscustomobject]@{ domain = $domain; file = "wiki/$domain/_index.md"; issue = "missing top-level scope summary line starting with >" })
    }
    $contentSlugs = @(Get-ChildItem -LiteralPath (Join-Path $resolvedRoot "wiki\$domain") -Filter "*.md" -File |
        Where-Object { $_.Name -ne "_index.md" } |
        ForEach-Object { [System.IO.Path]::GetFileNameWithoutExtension($_.Name) })
    foreach ($slug in $contentSlugs) {
        if ($indexText -notmatch "\[\[$([regex]::Escape($slug))(\||\]|#)") {
            $domainIndexCoverageIssues.Add([pscustomobject]@{ domain = $domain; issue = "content missing from _index: $slug" })
        }
    }
}

$basicMemoryStatus = $null
if (-not $SkipBasicMemory -and $null -ne (Get-Command basic-memory -ErrorAction SilentlyContinue)) {
    try {
        $statusText = & basic-memory status --project second-brain --json 2>$null
        if (-not [string]::IsNullOrWhiteSpace($statusText)) {
            $basicMemoryStatus = $statusText | ConvertFrom-Json
        }
    } catch {
        $basicMemoryStatus = [pscustomobject]@{ error = $_.Exception.Message }
    }
}

$issueCounts = [ordered]@{
    forbidden_scaffold = (Get-ItemCount $forbiddenScaffold)
    filename_issues = (Get-ItemCount $filenameIssues)
    frontmatter_issues = (Get-ItemCount $frontmatterIssues)
    title_looks_slug = (Get-ItemCount $titleLooksSlug)
    graph_config_issues = (Get-ItemCount $graphConfigIssues)
    markdown_image_display_issues = (Get-ItemCount $markdownImageDisplayIssues)
    raw_markdown_files = (Get-ItemCount $rawMarkdownFiles)
    raw_link_boundary_violations = (Get-ItemCount $rawLinkBoundaryViolations) + (Get-ItemCount $rawMarkdownLinkViolations)
    dead_links = (Get-ItemCount $deadLinks)
    root_index_link_violations = (Get-ItemCount $rootIndexLinkViolations)
    domain_index_link_violations = (Get-ItemCount $domainIndexLinkViolations)
    daily_internal_link_violations = (Get-ItemCount $dailyLinkViolations) + (Get-ItemCount $dailyMarkdownLinkViolations)
    related_without_body_support = (Get-ItemCount $frontmatterOnlyUnsupported)
    duplicate_basenames = (Get-ItemCount $duplicateBasenames)
    standard_internal_markdown_links = (Get-ItemCount $standardInternalMarkdownLinks)
    inline_yaml_arrays = (Get-ItemCount $inlineYamlArrays)
    bad_callouts = (Get-ItemCount $badCallouts)
    missing_root_index_domains = (Get-ItemCount $missingRootIndexDomains)
    stale_root_index_domains = (Get-ItemCount $staleRootIndexDomains)
    domain_index_coverage_issues = (Get-ItemCount $domainIndexCoverageIssues)
    domain_summary_issues = (Get-ItemCount $domainSummaryIssues)
}

$basicMemoryClean = $true
if ($null -ne $basicMemoryStatus -and $basicMemoryStatus.PSObject.Properties.Name -contains "modified") {
    $basicMemoryClean = @($basicMemoryStatus.new).Count -eq 0 -and
        @($basicMemoryStatus.modified).Count -eq 0 -and
        @($basicMemoryStatus.deleted).Count -eq 0 -and
        (Get-ItemCount $basicMemoryStatus.moves.PSObject.Properties) -eq 0
}

$deterministicIssueTotal = 0
foreach ($count in $issueCounts.Values) {
    $deterministicIssueTotal += [int]$count
}

[pscustomobject]@{
    status = if ($deterministicIssueTotal -eq 0 -and $basicMemoryClean) { "clean" } else { "issues" }
    counts = [ordered]@{
        all_md = $allMarkdownFiles.Count
        wiki_md = $wikiMarkdownFiles.Count
        content_pages = @($wikiMarkdownFiles | Where-Object { (Get-PageKind (Convert-ToVaultPath $_.FullName)) -eq "content" }).Count
        domain_indexes = @($wikiMarkdownFiles | Where-Object { (Get-PageKind (Convert-ToVaultPath $_.FullName)) -eq "domain-index" }).Count
        daily = @($allMarkdownFiles | Where-Object { (Convert-ToVaultPath $_.FullName) -like "daily/*.md" }).Count
        extracted_links = $links.Count
    }
    issue_counts = $issueCounts
    informational_counts = [ordered]@{
        content_pages_without_content_inbound = (Get-ItemCount $contentPagesWithoutContentInbound)
    }
    basic_memory_clean = $basicMemoryClean
    basic_memory_status = $basicMemoryStatus
    forbidden_scaffold = $forbiddenScaffold
    filename_issues = $filenameIssues
    frontmatter_issues = $frontmatterIssues
    title_looks_slug = $titleLooksSlug
    graph_config_issues = $graphConfigIssues
    markdown_image_display_issues = $markdownImageDisplayIssues
    raw_markdown_files = $rawMarkdownFiles
    raw_link_boundary_violations = @(
        $rawLinkBoundaryViolations
        $rawMarkdownLinkViolations
    )
    dead_links = $deadLinks | Select-Object source, target, line, context, target_path
    root_index_link_violations = $rootIndexLinkViolations | Select-Object source, target, line, context, target_path
    domain_index_link_violations = $domainIndexLinkViolations | Select-Object source, target, line, context, target_path
    daily_internal_link_violations = @(
        $dailyLinkViolations | Select-Object source, target, line, context, target_path, @{Name = "link_type"; Expression = { "wikilink" }}
        $dailyMarkdownLinkViolations
    )
    related_without_body_support = $frontmatterOnlyUnsupported
    content_pages_without_content_inbound = $contentPagesWithoutContentInbound
    duplicate_basenames = $duplicateBasenames
    standard_internal_markdown_links = $standardInternalMarkdownLinks
    inline_yaml_arrays = $inlineYamlArrays
    bad_callouts = $badCallouts
    missing_root_index_domains = $missingRootIndexDomains
    stale_root_index_domains = $staleRootIndexDomains
    domain_index_coverage_issues = $domainIndexCoverageIssues
    domain_summary_issues = $domainSummaryIssues
} | ConvertTo-Json -Depth 8
