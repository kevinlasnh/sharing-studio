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

function Get-PageKind {
    param([string]$VaultPath)

    if ($VaultPath -eq "index.md") { return "root-index" }
    if ($VaultPath -like "daily/*.md") { return "daily" }
    if ($VaultPath -like "wiki/*/_index.md") { return "domain-index" }
    if ($VaultPath -match '^wiki/[^/]+/[^/]+\.md$') { return "content" }
    if ($VaultPath -match '^raw/.+\.md$') { return "raw-markdown" }
    return "other"
}

function Remove-InlineCode {
    param([string]$Line)
    return ([regex]::Replace($Line, '`[^`]*`', ''))
}

function Get-ScanLines {
    param(
        [string[]]$Lines,
        [bool]$TrackFrontmatter
    )

    $inFence = $false
    $inFrontmatter = $false
    $frontmatterDone = $false
    $result = New-Object System.Collections.Generic.List[object]

    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $line = $Lines[$i]
        $lineNumber = $i + 1

        if ($TrackFrontmatter -and $lineNumber -eq 1 -and $line.Trim() -eq "---") {
            $inFrontmatter = $true
            $result.Add([pscustomobject]@{ Number = $lineNumber; Text = $line; Frontmatter = $true })
            continue
        }

        if ($TrackFrontmatter -and $inFrontmatter) {
            $result.Add([pscustomobject]@{ Number = $lineNumber; Text = $line; Frontmatter = $true })
            if ($line.Trim() -eq "---") {
                $inFrontmatter = $false
                $frontmatterDone = $true
            }
            continue
        }

        if ($TrackFrontmatter -and -not $frontmatterDone -and $line.Trim() -eq "---") {
            $frontmatterDone = $true
        }

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

        $result.Add([pscustomobject]@{ Number = $lineNumber; Text = (Remove-InlineCode $line); Frontmatter = $false })
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

function Get-VaultRoot {
    $basePath = $env:CLAUDE_PROJECT_DIR
    if ([string]::IsNullOrWhiteSpace($basePath)) {
        $basePath = (Get-Location).Path
    }
    return $basePath
}

$script:RawFileBasenameMap = $null
function Get-RawFileBasenameMap {
    if ($null -ne $script:RawFileBasenameMap) {
        return $script:RawFileBasenameMap
    }

    $script:RawFileBasenameMap = @{}
    $rawRoot = Join-Path -Path (Get-VaultRoot) -ChildPath "raw"
    if (Test-Path -LiteralPath $rawRoot -PathType Container) {
        foreach ($file in Get-ChildItem -LiteralPath $rawRoot -Recurse -File -ErrorAction SilentlyContinue) {
            $key = $file.Name.ToLowerInvariant()
            if (-not $script:RawFileBasenameMap.ContainsKey($key)) {
                $script:RawFileBasenameMap[$key] = Normalize-VaultPath -PathText $file.FullName
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

    $fullPath = Join-Path -Path (Get-VaultRoot) -ChildPath $cleanPath
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

function Test-RawLinks {
    param(
        [string]$Text,
        [string]$Kind,
        [string]$SourceKind
    )

    $violations = New-Object System.Collections.Generic.List[string]
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $violations
    }

    $lines = $Text -split "`r?`n"
    $scanLines = Get-ScanLines -Lines $lines -TrackFrontmatter ($Kind -eq "full-file")
    $wikilinkPattern = [regex]::new('(!?)\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|([^\]]+))?\]\]', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $localMarkdownLinkPattern = [regex]::new('!?\[[^\]]*\]\((?!https?://)([^)\s]+)[^)]*\)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)

    foreach ($line in $scanLines) {
        foreach ($match in $wikilinkPattern.Matches($line.Text)) {
            $isEmbed = $match.Groups[1].Value -eq "!"
            $rawTargetInfo = Get-RawTargetInfo -Target $match.Groups[2].Value
            if (-not $rawTargetInfo.IsRawLike) {
                if ((Test-LocalAttachmentTarget -Target $match.Groups[2].Value) -and (Test-ProvenanceContext -LineText $line.Text)) {
                    $violations.Add(("{0}: source/evidence/provenance attachments must use canonical raw wikilinks such as [[raw/file.ext]], not bare attachment wikilinks or non-canonical embeds: {1}" -f $line.Number, $line.Text.Trim()))
                }
                continue
            }

            $isRawImageEmbed = $isEmbed -and (Test-RawImagePath -RawPath $rawTargetInfo.RawPath)
            if ($isEmbed -and -not $isRawImageEmbed) {
                $violations.Add(("{0}: raw embeds are allowed only for image files (.png/.jpg/.jpeg/.webp/.gif); cite non-image raw files as plain provenance wikilinks: {1}" -f $line.Number, $line.Text.Trim()))
            }
            if ($rawTargetInfo.IsBasenameReference) {
                $violations.Add(("{0}: raw files must not be linked by bare attachment basename; use canonical [[raw/file.ext]] so the provenance edge is explicit: {1}" -f $line.Number, $line.Text.Trim()))
            }
            if (-not $rawTargetInfo.IsCanonical) {
                $violations.Add(("{0}: raw wikilinks must use canonical vault-root lowercase path syntax [[raw/file.ext]], not relative, absolute, encoded, or differently cased variants: {1}" -f $line.Number, $line.Text.Trim()))
            }
            if ($rawTargetInfo.RawPath -match '\.md$') {
                $violations.Add(("{0}: raw Markdown targets are forbidden because they create unintended graph nodes; use .txt/.pdf/attachment or ingest into wiki: {1}" -f $line.Number, $line.Text.Trim()))
            }
            if ($SourceKind -ne "content") {
                $violations.Add(("{0}: raw wikilinks are allowed only from wiki content pages: {1}" -f $line.Number, $line.Text.Trim()))
            } elseif ($line.Frontmatter) {
                $violations.Add(("{0}: raw wikilinks must stay in body source/evidence sentences, not frontmatter: {1}" -f $line.Number, $line.Text.Trim()))
            } else {
                if ($isRawImageEmbed) {
                    $display = if ($match.Groups[3].Success) { $match.Groups[3].Value } else { $null }
                    $widthIssue = Test-RawImageDisplayWidth -RawPath $rawTargetInfo.RawPath -Display $display
                    if ($null -ne $widthIssue) {
                        $violations.Add(("{0}: {1}: {2}" -f $line.Number, $widthIssue, $line.Text.Trim()))
                    }
                    $contextIssue = Test-RawForbiddenContext -LineText $line.Text
                    if ($null -ne $contextIssue) {
                        $violations.Add(("{0}: {1}: {2}" -f $line.Number, $contextIssue, $line.Text.Trim()))
                    }
                } else {
                    $contextIssue = Test-RawContext -LineText $line.Text
                    if ($null -ne $contextIssue) {
                        $violations.Add(("{0}: {1}: {2}" -f $line.Number, $contextIssue, $line.Text.Trim()))
                    }
                }
            }
        }

        foreach ($match in $localMarkdownLinkPattern.Matches($line.Text)) {
            $rawTargetInfo = Get-RawTargetInfo -Target $match.Groups[1].Value
            if ($rawTargetInfo.IsRawLike) {
                $violations.Add(("{0}: raw files must be referenced as Obsidian wikilinks from wiki content pages, not local Markdown links: {1}" -f $line.Number, $line.Text.Trim()))
            } elseif ((Test-LocalAttachmentTarget -Target $match.Groups[1].Value) -and (Test-ProvenanceContext -LineText $line.Text)) {
                $violations.Add(("{0}: source/evidence/provenance attachments must use canonical raw wikilinks such as [[raw/file.ext]], not local Markdown attachment links: {1}" -f $line.Number, $line.Text.Trim()))
            }
        }
    }

    return $violations
}

$filePath = Get-HookFilePath -Hook $hook
$vaultPath = Normalize-VaultPath -PathText $filePath
$sourceKind = Get-PageKind -VaultPath $vaultPath
$hookEventName = "PreToolUse"
if ($hook.PSObject.Properties.Name -contains "hook_event_name") {
    $hookEventName = [string]$hook.hook_event_name
} elseif ($hook.PSObject.Properties.Name -contains "hookEventName") {
    $hookEventName = [string]$hook.hookEventName
}

if ([string]::IsNullOrWhiteSpace($vaultPath)) {
    exit 0
}

$allViolations = New-Object System.Collections.Generic.List[string]

if ($sourceKind -eq "raw-markdown") {
    $allViolations.Add("path: raw/ must not store Markdown notes because raw Markdown can create Obsidian graph edges; store the original as .txt/.pdf/attachment or ingest it into wiki instead")
}

$snippets = Get-ProposedSnippets -Hook $hook
foreach ($snippet in $snippets) {
    $violations = Test-RawLinks -Text $snippet.Text -Kind $snippet.Kind -SourceKind $sourceKind
    foreach ($violation in $violations) {
        $allViolations.Add("$($snippet.Kind): $violation")
    }
}

$shouldScanCurrentFile = ($hookEventName -eq "PostToolUse" -or $snippets.Count -eq 0)
$resolvedPath = Resolve-HookFilePath -PathText $filePath -Hook $hook
if ($shouldScanCurrentFile -and (Test-Path -LiteralPath $resolvedPath -PathType Leaf) -and $vaultPath -match '\.md$') {
    try {
        $content = Get-Content -LiteralPath $resolvedPath -Raw -Encoding UTF8 -ErrorAction Stop
        $violations = Test-RawLinks -Text $content -Kind "full-file" -SourceKind $sourceKind
        foreach ($violation in $violations) {
            $allViolations.Add("file: $violation")
        }
    } catch {
        exit 0
    }
}

if ($allViolations.Count -gt 0) {
    $reason = "Second Brain raw reference policy blocked '$filePath': raw files are immutable source/provenance or instructional visual assets, not concept/navigation nodes. " + (($allViolations | Select-Object -First 20) -join " ; ")
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
