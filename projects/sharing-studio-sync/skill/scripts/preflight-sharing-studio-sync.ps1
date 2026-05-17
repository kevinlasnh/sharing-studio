param(
    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

function Write-Result {
    param([string]$Status, [string]$Message)
    Write-Output "$Status`t$Message"
}

function Test-PortablePathLiteral {
    param([string]$Value)
    return $Value -match '^[A-Za-z]:\\' -or $Value -match '^\\\\' -or $Value -match '^/'
}

function Get-SecondBrainPath {
    if ($env:SHARING_STUDIO_SECOND_BRAIN_PATH) {
        return $env:SHARING_STUDIO_SECOND_BRAIN_PATH
    }

    $routerCandidates = @(
        (Join-Path $HOME ".codex\AGENTS.md"),
        (Join-Path $HOME ".claude\CLAUDE.md"),
        (Join-Path $HOME ".gemini\GEMINI.md")
    )

    foreach ($candidate in $routerCandidates) {
        if (-not (Test-Path -LiteralPath $candidate)) {
            continue
        }

        $matches = Get-Content -Encoding UTF8 -LiteralPath $candidate |
            Select-String -Pattern '^\s*-\s+\*\*vault 路径\*\*.*`([^`]+)`'

        foreach ($match in $matches) {
            $value = $match.Matches[0].Groups[1].Value
            if (Test-PortablePathLiteral -Value $value) {
                return $value
            }
        }
    }

    return $null
}

$resolvedRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
if (-not (Test-Path -LiteralPath (Join-Path $resolvedRoot ".git") -PathType Container)) {
    Write-Result "FAIL" "RepoRoot is not a git repository root: $resolvedRoot"
    exit 1
}

$expected = @(
    "README.md",
    "README.zh-CN.md",
    "projects\agent-memory-stack",
    "projects\second-brain-scaffold",
    "projects\gtd-todoist",
    "projects\agent-workflows",
    "projects\sharing-studio-sync"
)

foreach ($item in $expected) {
    $path = Join-Path $resolvedRoot $item
    if (Test-Path -LiteralPath $path) {
        Write-Result "PASS" "Found $item"
    } else {
        Write-Result "WARN" "Missing $item"
    }
}

$sources = [ordered]@{
    "global Claude router" = Join-Path $HOME ".claude\CLAUDE.md"
    "global Codex router" = Join-Path $HOME ".codex\AGENTS.md"
    "global Gemini router" = Join-Path $HOME ".gemini\GEMINI.md"
    "heavy-research" = Join-Path $HOME ".agents\skills\heavy-research"
    "heavy-review" = Join-Path $HOME ".agents\skills\heavy-review"
}

foreach ($entry in $sources.GetEnumerator()) {
    if (Test-Path -LiteralPath $entry.Value) {
        Write-Result "PASS" "Source available: $($entry.Key) -> $($entry.Value)"
    } else {
        Write-Result "WARN" "Source missing: $($entry.Key) -> $($entry.Value)"
    }
}

$secondBrainPath = Get-SecondBrainPath
if ($secondBrainPath -and (Test-Path -LiteralPath $secondBrainPath)) {
    Write-Result "PASS" "Source available: second-brain vault -> $secondBrainPath"
} elseif ($secondBrainPath) {
    Write-Result "WARN" "Configured second-brain vault path does not exist -> $secondBrainPath"
} else {
    Write-Result "WARN" "Second-brain vault path not found. Set SHARING_STUDIO_SECOND_BRAIN_PATH or record a vault path in a global router file."
}

$protected = @(
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "task_plan.md",
    "progress.md",
    "findings.md",
    ".claude/",
    ".agents/",
    ".codex/",
    ".gemini/",
    ".workflows/",
    ".brv/",
    ".brv"
)

Write-Result "INFO" ("Protected push paths: " + ($protected -join ", "))

$protectedPattern = '^(AGENTS\.md|CLAUDE\.md|GEMINI\.md|task_plan\.md|progress\.md|findings\.md|\.claude/|\.agents/|\.codex/|\.gemini/|\.workflows/|\.brv/|\.brv$)'
$staged = git -C $resolvedRoot diff --cached --name-only
$badStaged = @($staged | Where-Object { $_ -match $protectedPattern })
if ($badStaged.Count -gt 0) {
    Write-Result "FAIL" ("Protected paths are staged: " + ($badStaged -join ", "))
    exit 1
}

Write-Result "PASS" "No protected repo-root paths are staged."
