$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()

$inputText = [Console]::In.ReadToEnd()

try {
    $hook = $inputText | ConvertFrom-Json -ErrorAction Stop
} catch {
    exit 0
}

function Get-ShellCommandText {
    param($Hook)

    if ($null -eq $Hook.tool_input) {
        return ""
    }
    if ($Hook.tool_input.PSObject.Properties.Name -contains "command") {
        return [string]$Hook.tool_input.command
    }
    return ""
}

function Deny-Command {
    param([string]$Reason)

    $payload = @{
        hookSpecificOutput = @{
            hookEventName = "PreToolUse"
            permissionDecision = "deny"
            permissionDecisionReason = "Second Brain shell write policy blocked command: $Reason"
        }
    } | ConvertTo-Json -Compress

    Write-Output $payload
}

$commandText = Get-ShellCommandText -Hook $hook
if ([string]::IsNullOrWhiteSpace($commandText)) {
    exit 0
}

$normalized = $commandText -replace "\\", "/"
$normalizedLower = $normalized.ToLowerInvariant()
$writeVerbPattern = '\b(set-content|add-content|out-file|new-item|copy-item|move-item|remove-item|rename-item|del|erase|rm|mv|cp|cat|tee|echo|printf|python|node|powershell|pwsh)\b'
$redirectPattern = '(^|[^>])>{1,2}\s*["'']?[^"'']*(wiki|daily|raw|\.raw)/'
$protectedPathPattern = '(wiki/log\.md|wiki/hot\.md|wiki/ingest-log\.md|wiki/sources/|\.raw/|raw/[^ \t\r\n"'']+\.md|wiki/overview\.md|wiki/index\.md|wiki/meta/dashboard\.md|wiki/meta/overview\.canvas|wiki/[^ \t\r\n"'']+\.canvas|daily/[^ \t\r\n"'']+\.md|wiki/[^ \t\r\n"'']+\.md)'

if ($normalizedLower -match $protectedPathPattern -and ($normalizedLower -match $writeVerbPattern -or $normalizedLower -match $redirectPattern)) {
    Deny-Command -Reason "use Write/Edit/MultiEdit and vault hooks for wiki/daily/raw Markdown or forbidden scaffold paths; shell writes can bypass schema and link checks"
    exit 0
}

exit 0
