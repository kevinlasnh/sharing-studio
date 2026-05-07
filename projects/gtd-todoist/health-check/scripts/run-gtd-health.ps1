param(
    [Parameter(Mandatory=$true)]
    [string]$HostName,                     # e.g. "user@host" or "user@1.2.3.4"
    [switch]$IncludeTodoistScaffold,
    [string]$StateDir = "",                # default on remote: ~/.openclaw
    [string]$ConfigPath = "",              # default on remote: <state>/openclaw.json
    [string]$WorkspaceDir = "",            # default on remote: <state>/workspace
    [string]$AgentId = "main",
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()

function Quote-RemoteSingle {
    param([string]$Value)
    return "'" + ($Value -replace "'", "'\''") + "'"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$healthScript = Join-Path $scriptDir "gtd_health_check.sh"

if (-not (Test-Path -LiteralPath $healthScript -PathType Leaf)) {
    throw "Cannot find gtd_health_check.sh at $healthScript"
}

$bytes = [System.IO.File]::ReadAllBytes($healthScript)
if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    $trimmed = New-Object byte[] ($bytes.Length - 3)
    [System.Array]::Copy($bytes, 3, $trimmed, 0, $trimmed.Length)
    $bytes = $trimmed
}

$encoded = [System.Convert]::ToBase64String($bytes)

$envParts = @(
    "INCLUDE_TODOIST_SCAFFOLD=$(if ($IncludeTodoistScaffold) { '1' } else { '0' })",
    "OPENCLAW_AGENT_ID=$(Quote-RemoteSingle $AgentId)"
)

if (-not [string]::IsNullOrWhiteSpace($StateDir)) {
    $envParts += "OPENCLAW_STATE_DIR=$(Quote-RemoteSingle $StateDir)"
}

if (-not [string]::IsNullOrWhiteSpace($ConfigPath)) {
    $envParts += "OPENCLAW_CONFIG_PATH=$(Quote-RemoteSingle $ConfigPath)"
}

if (-not [string]::IsNullOrWhiteSpace($WorkspaceDir)) {
    $envParts += "OPENCLAW_WORKSPACE_DIR=$(Quote-RemoteSingle $WorkspaceDir)"
}

$remoteEnv = $envParts -join " "
$remoteCommand = "printf '%s' '$encoded' | base64 -d | tr -d '\r' | env $remoteEnv bash -s"

if ($OutputPath) {
    $outputDir = Split-Path -Parent $OutputPath
    if ($outputDir -and -not (Test-Path -LiteralPath $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir | Out-Null
    }
    & ssh $HostName $remoteCommand 2>&1 | Tee-Object -FilePath $OutputPath
} else {
    & ssh $HostName $remoteCommand
}

exit $LASTEXITCODE
