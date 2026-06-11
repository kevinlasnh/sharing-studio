# 创建本次调研 session 目录并返回路径
# 调用方式：在仓库根目录运行此脚本，输出 SESSION_DIR 路径

$timestamp = Get-Date -Format "yyyy-MM-dd-HHmm"
$sessionDir = ".workflows\$timestamp"
$researchDir = "$sessionDir\research"

if (-not (Test-Path $researchDir)) {
    New-Item -ItemType Directory -Path $researchDir -Force | Out-Null
}

Write-Output (Resolve-Path $sessionDir).Path
