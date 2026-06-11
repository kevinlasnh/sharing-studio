param(
    [string]$VaultRoot = ".",
    [string]$Remote = "hf",
    [string]$Branch = "main",
    [string]$MessagePrefix = "second-brain: hf backup",
    [bool]$AllowInitialForceWithLease = $true
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

function Stop-WithMessage {
    param([string]$Message)
    throw $Message
}

function Test-AllowedPrivateHfRemote {
    param(
        [string]$RemoteName,
        [string]$RemoteUrl
    )

    return (
        $RemoteName -eq "hf" -and
        $RemoteUrl -eq "<hf-private-dataset-url>"
    )
}

function Test-GitHead {
    $oldErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & git rev-parse --verify HEAD 1>$null 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }
}

function Test-SingleRootHead {
    $oldErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $countText = & git rev-list --count HEAD 2>$null | Select-Object -First 1
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($countText)) {
            return $false
        }
        return ([int]$countText -eq 1)
    }
    finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }
}

function Push-LfsObjects {
    param([string]$RemoteName)

    $oldErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $lfsTracked = & git lfs ls-files 2>$null | Select-Object -First 1
        $lfsListExit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }

    if ($lfsListExit -eq 0 -and -not [string]::IsNullOrWhiteSpace($lfsTracked)) {
        & git lfs push $RemoteName HEAD
        if ($LASTEXITCODE -ne 0) {
            Stop-WithMessage "git lfs push failed."
        }
    }
}

$root = (Resolve-Path -LiteralPath $VaultRoot).Path

Push-Location -LiteralPath $root
try {
    & git rev-parse --is-inside-work-tree *> $null
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage "Not inside a Git worktree: $root"
    }

    $remoteUrlOutput = & git remote get-url $Remote 2>$null
    if ($LASTEXITCODE -ne 0 -or $null -eq $remoteUrlOutput) {
        Stop-WithMessage "Git remote '$Remote' is not configured."
    }
    $remoteUrl = ($remoteUrlOutput | Select-Object -First 1).ToString().Trim()
    if (-not (Test-AllowedPrivateHfRemote -RemoteName $Remote -RemoteUrl $remoteUrl)) {
        Stop-WithMessage "Refusing backup: remote '$Remote' must be the private Second Brain Hugging Face dataset URL."
    }
    $remoteRef = "refs/heads/$Branch"
    $remoteHeadBefore = ""
    $remoteHeadOutput = & git ls-remote $Remote $remoteRef 2>$null
    if ($LASTEXITCODE -eq 0 -and $null -ne $remoteHeadOutput) {
        $remoteHeadBefore = (($remoteHeadOutput | Select-Object -First 1).ToString().Trim() -split "\s+")[0]
    }

    & git add -A
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage "git add -A failed."
    }

    & git diff --cached --quiet
    $diffExit = $LASTEXITCODE

    if ($diffExit -eq 0) {
        $headExists = Test-GitHead
        if (-not $headExists) {
            $result = [ordered]@{
                status = "skipped"
                reason = "no staged changes and no local HEAD"
                remote = $Remote
                branch = $Branch
                remote_url = $remoteUrl
            }
            $result | ConvertTo-Json -Compress
            exit 0
        }

        Push-LfsObjects -RemoteName $Remote
        & git push $Remote "HEAD:$Branch"
        if ($LASTEXITCODE -ne 0) {
            if ($AllowInitialForceWithLease -and (Test-SingleRootHead) -and -not [string]::IsNullOrWhiteSpace($remoteHeadBefore)) {
                & git push "--force-with-lease=$remoteRef`:$remoteHeadBefore" $Remote "HEAD:$Branch"
                if ($LASTEXITCODE -ne 0) {
                    Stop-WithMessage "git push failed, and initial existing-HEAD force-with-lease bootstrap also failed."
                }

                $commit = (& git rev-parse --short HEAD).ToString().Trim()
                $remoteHeadAfterBootstrap = & git ls-remote $Remote $remoteRef 2>$null
                $remoteHeadText = ""
                if ($LASTEXITCODE -eq 0 -and $null -ne $remoteHeadAfterBootstrap) {
                    $remoteHeadText = ($remoteHeadAfterBootstrap | Select-Object -First 1).ToString().Trim()
                }

                $result = [ordered]@{
                    status = "pushed"
                    action = "initial_existing_head_force_with_lease_bootstrap"
                    commit = $commit
                    remote = $Remote
                    branch = $Branch
                    remote_url = $remoteUrl
                    remote_head = $remoteHeadText
                    overwritten_remote_head = $remoteHeadBefore
                }
                $result | ConvertTo-Json -Compress
                exit 0
            }

            Stop-WithMessage "git push failed."
        }

        $commit = (& git rev-parse --short HEAD).ToString().Trim()
        $result = [ordered]@{
            status = "pushed"
            action = "push_existing_head"
            commit = $commit
            remote = $Remote
            branch = $Branch
            remote_url = $remoteUrl
        }
        $result | ConvertTo-Json -Compress
        exit 0
    }

    if ($diffExit -ne 1) {
        Stop-WithMessage "git diff --cached --quiet failed."
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $message = "$MessagePrefix $timestamp"

    $headExistedBeforeCommit = Test-GitHead

    & git commit -m $message
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage "git commit failed."
    }

    $commit = (& git rev-parse --short HEAD).ToString().Trim()

    Push-LfsObjects -RemoteName $Remote
    & git push $Remote "HEAD:$Branch"
    if ($LASTEXITCODE -ne 0) {
        if ($AllowInitialForceWithLease -and -not $headExistedBeforeCommit -and -not [string]::IsNullOrWhiteSpace($remoteHeadBefore)) {
            & git push "--force-with-lease=$remoteRef`:$remoteHeadBefore" $Remote "HEAD:$Branch"
            if ($LASTEXITCODE -ne 0) {
                Stop-WithMessage "git push failed, and initial force-with-lease bootstrap also failed."
            }

            $remoteHeadAfterBootstrap = & git ls-remote $Remote $remoteRef 2>$null
            $remoteHeadText = ""
            if ($LASTEXITCODE -eq 0 -and $null -ne $remoteHeadAfterBootstrap) {
                $remoteHeadText = ($remoteHeadAfterBootstrap | Select-Object -First 1).ToString().Trim()
            }

            $result = [ordered]@{
                status = "pushed"
                action = "initial_force_with_lease_bootstrap"
                commit = $commit
                remote = $Remote
                branch = $Branch
                remote_url = $remoteUrl
                message = $message
                remote_head = $remoteHeadText
                overwritten_remote_head = $remoteHeadBefore
            }
            $result | ConvertTo-Json -Compress
            exit 0
        }

        Stop-WithMessage "git push failed."
    }

    $remoteHeadOutput = & git ls-remote $Remote $remoteRef 2>$null
    $remoteHead = ""
    if ($LASTEXITCODE -eq 0 -and $null -ne $remoteHeadOutput) {
        $remoteHead = ($remoteHeadOutput | Select-Object -First 1).ToString().Trim()
    }

    $result = [ordered]@{
        status = "pushed"
        action = "commit_and_push"
        commit = $commit
        remote = $Remote
        branch = $Branch
        remote_url = $remoteUrl
        message = $message
        remote_head = $remoteHead
    }
    $result | ConvertTo-Json -Compress
}
finally {
    Pop-Location
}
