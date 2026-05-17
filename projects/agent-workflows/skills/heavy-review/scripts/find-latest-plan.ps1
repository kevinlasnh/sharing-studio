# 找到 .workflows/ 下最近一个包含 deployment-plan.md 的时间戳目录
# 输出 SESSION_DIR 和 PLAN_PATH

$workflowsDir = ".workflows"

if (-not (Test-Path $workflowsDir)) {
    Write-Error "未找到 .workflows/ 目录。请先用 heavy-research 生成 deployment-plan。"
    exit 1
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
    | Where-Object { Test-Path (Join-Path $_.Directory.FullName "deployment-plan.md") } `
    | Select-Object -First 1

if ($null -eq $latest) {
    Write-Error "未找到包含 deployment-plan.md 的 session 目录。请先用 heavy-research 生成 deployment-plan。"
    exit 1
}

$planPath = Join-Path $latest.Directory.FullName "deployment-plan.md"

Write-Output "SESSION_DIR=$($latest.Directory.FullName)"
Write-Output "PLAN_PATH=$planPath"
