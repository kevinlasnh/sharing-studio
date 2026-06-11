# 找到 .workflows/ 下最新时间戳目录里的 deployment-plan.md
# 输出 SESSION_DIR 和 PLAN_PATH

$workflowsDir = ".workflows"

if (-not (Test-Path $workflowsDir)) {
    Write-Error "未找到 .workflows/ 目录。请先用 heavy-research 生成 deployment-plan。"
    exit 1
}

$latest = Get-ChildItem $workflowsDir -Directory `
    | Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}-\d{4}$' } `
    | Sort-Object Name -Descending `
    | Select-Object -First 1

if ($null -eq $latest) {
    Write-Error "未找到符合 YYYY-MM-DD-HHmm 命名的 session 目录。"
    exit 1
}

$planPath = Join-Path $latest.FullName "deployment-plan.md"

if (-not (Test-Path $planPath)) {
    Write-Error "在 $($latest.FullName) 中未找到 deployment-plan.md。"
    exit 1
}

Write-Output "SESSION_DIR=$($latest.FullName)"
Write-Output "PLAN_PATH=$planPath"
