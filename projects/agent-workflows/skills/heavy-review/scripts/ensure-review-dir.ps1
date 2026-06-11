# 在指定 SESSION_DIR 下创建 review/ 子目录
# 调用方式：传入 SESSION_DIR 路径

param(
    [Parameter(Mandatory=$true)]
    [string]$SessionDir
)

$reviewDir = Join-Path $SessionDir "review"

if (-not (Test-Path $reviewDir)) {
    New-Item -ItemType Directory -Path $reviewDir -Force | Out-Null
}

Write-Output (Resolve-Path $reviewDir).Path
