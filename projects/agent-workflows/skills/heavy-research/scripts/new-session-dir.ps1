# 创建本次调研 session 目录并返回路径
# 调用方式：在仓库根目录运行此脚本，输出 SESSION_DIR=<绝对路径>

$timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
$sessionDir = ".workflows\$timestamp"
$researchDir = "$sessionDir\research"
$activeSessionFile = ".workflows\.active-session"
$suffix = 1

while (Test-Path $sessionDir) {
    $sessionDir = ".workflows\$timestamp-$suffix"
    $researchDir = "$sessionDir\research"
    $suffix++
}

if (-not (Test-Path $researchDir)) {
    New-Item -ItemType Directory -Path $researchDir -Force | Out-Null
}

$resolved = (Resolve-Path $sessionDir).Path
Set-Content -LiteralPath $activeSessionFile -Value $resolved -Encoding UTF8

Write-Output "SESSION_DIR=$resolved"
