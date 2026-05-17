# 在指定 SESSION_DIR 下创建 review/ 子目录
# 调用方式：传入 SESSION_DIR 路径；路径含空格时调用方必须加引号

param(
    [Parameter(Mandatory=$true)]
    [string]$SessionDir
)

if (-not (Test-Path -LiteralPath $SessionDir -PathType Container)) {
    Write-Error "SESSION_DIR 不存在或不是目录：$SessionDir"
    exit 1
}

$reviewDir = Join-Path $SessionDir "review"

if (-not (Test-Path $reviewDir)) {
    New-Item -ItemType Directory -Path $reviewDir -Force | Out-Null
}

Write-Output (Resolve-Path $reviewDir).Path
