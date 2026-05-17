# 找到 .workflows/ 下最近一个包含研究或计划产物的 session 目录
# 输出 SESSION_DIR；若没有可复用目录则返回非零退出码

$workflowsDir = ".workflows"
$activeSessionFile = Join-Path $workflowsDir ".active-session"

if (-not (Test-Path $workflowsDir)) {
    Write-Error "未找到 .workflows/ 目录。"
    exit 1
}

if (Test-Path $activeSessionFile) {
    $active = (Get-Content -LiteralPath $activeSessionFile -Encoding UTF8 | Select-Object -First 1).Trim()
    $workflowsRoot = (Resolve-Path $workflowsDir).Path.TrimEnd('\', '/')
    if ($active -and (Test-Path -LiteralPath $active)) {
        $activeItem = Get-Item -LiteralPath $active
        $activePath = $activeItem.FullName.TrimEnd('\', '/')
        $insideWorkflows = $activePath.StartsWith("$workflowsRoot\", [System.StringComparison]::OrdinalIgnoreCase)
        $isTimestampSession = $activeItem.Name -match '^(\d{4}-\d{2}-\d{2}-\d{4}(\d{2})?)(?:-(\d+))?$'
        $hasSessionArtifact = (Test-Path (Join-Path $activePath "deployment-plan.md")) -or (Test-Path (Join-Path $activePath "research"))
        if (-not $activeItem.PSIsContainer -or -not $insideWorkflows -or -not $isTimestampSession -or -not $hasSessionArtifact) {
            Write-Warning ".active-session 指向的路径不是当前仓库 .workflows/ 下的 session 目录，已忽略。"
        } else {
            Write-Output "SESSION_DIR=$active"
            exit 0
        }
    }
}

$latest = Get-ChildItem $workflowsDir -Directory `
    | Where-Object { $_.Name -match '^(\d{4}-\d{2}-\d{2}-\d{4}(\d{2})?)(?:-(\d+))?$' } `
    | ForEach-Object {
        $match = [regex]::Match($_.Name, '^(\d{4}-\d{2}-\d{2}-\d{4}(\d{2})?)(?:-(\d+))?$')
        [pscustomobject]@{
            Directory = $_
            BaseName = $match.Groups[1].Value
            Suffix = if ($match.Groups[3].Success) { [int]$match.Groups[3].Value } else { 0 }
        }
    } `
    | Sort-Object BaseName, Suffix -Descending `
    | Where-Object {
        $_ = $_.Directory
        (Test-Path (Join-Path $_.FullName "deployment-plan.md")) -or
        (Test-Path (Join-Path $_.FullName "research"))
    } `
    | Select-Object -First 1

if ($null -eq $latest) {
    Write-Error "未找到可复用的 session 目录。"
    exit 1
}

Write-Output "SESSION_DIR=$($latest.Directory.FullName)"
