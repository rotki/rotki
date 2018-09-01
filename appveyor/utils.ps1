# Appveyor utils borrowed from excellent https://github.com/micbou/vim-for-windows

# Download a file if not already existing.
Function Invoke-Download {
    Param (
        [Parameter(Mandatory=$TRUE)]
        [System.Uri] $url,
        [Parameter(Mandatory=$TRUE)]
        [string] $filepath
    )

    # Make sure the destination directory exists.
    # System.IO.FileInfo works even if the file/dir doesn't exist, which is better
    # than get-item which requires the file to exist.
    If (!(Test-Path ([System.IO.FileInfo]$filepath).DirectoryName)) {
        [void](New-Item ([System.IO.FileInfo]$filepath).DirectoryName -force -type directory)
    }

    # Download if the file does not exist.
    If (-not (Test-Path $filepath)) {
        Write-Host "Downloading $url to $filepath..."
        [void] (New-Object System.Net.WebClient).DownloadFile($url.ToString(), $filepath)
        Write-Host "Downloaded."
    }
}

# Clone a repository to a specific branch or checkout to this branch if already existing.
Function Invoke-GitClone {
    Param (
        [Parameter(Mandatory=$TRUE)]
        [System.Uri] $repository,
        [Parameter(Mandatory=$TRUE)]
        [string] $directory,
        [Parameter(Mandatory=$TRUE)]
        [string] $branch
    )

    If (-not (Test-Path $directory)) {
        Invoke-Expression "git clone $repository -b $branch --depth 1 -q $directory"
        Return
    }

    Push-Location -Path $directory
    Invoke-Expression "git fetch"
    Invoke-Expression "git checkout -b $branch"
    Pop-Location
}

# Invokes a Cmd.exe shell script and updates the environment.
function Invoke-CmdScript {
    param(
        [String] $scriptName
    )
    $cmdLine = """$scriptName"" $args & set"
    & $Env:SystemRoot\system32\cmd.exe /c $cmdLine |
    Select-String '^([^=]*)=(.*)$' | Foreach-Object {
        $varName = $_.Matches[0].Groups[1].Value
            $varValue = $_.Matches[0].Groups[2].Value
            Set-Item Env:$varName $varValue
    }
}

# Returns the current environment.
function Get-Environment {
    Get-Childitem Env:
}

# Restores the environment to a previous state.
function Restore-Environment {
    param(
        [parameter(Mandatory=$TRUE)]
        [System.Collections.DictionaryEntry[]] $oldEnv
    )
    # Remove any added variables.
    Compare-Object $oldEnv $(Get-Environment) -property Key -passthru |
    Where-Object { $_.SideIndicator -eq "=>" } |
    Foreach-Object { Remove-Item Env:$($_.Name) }
    # Revert any changed variables to original values.
    Compare-Object $oldEnv $(Get-Environment) -property Value -passthru |
    Where-Object { $_.SideIndicator -eq "<=" } |
    Foreach-Object { Set-Item Env:$($_.Name) $_.Value }
}

Function Retry-Command
{
    Param (
        [Parameter(Mandatory=$true)]
        [string] $command,
        [Parameter(Mandatory=$true)]
        [hashtable] $args,
        [Parameter(Mandatory=$false)]
        [int] $retries = 5,
        [Parameter(Mandatory=$false)]
        [int] $secondsDelay = 2
    )

    # Setting ErrorAction to Stop is important. This ensures any errors that
    # occur in the command are treated as terminating errors, and will be
    # caught by the catch block.
    $args.ErrorAction = "Stop"

    $retrycount = 0
    $completed = $false

    While (-not $completed) {
        Try {
            & $command @args
            $completed = $true
        } Catch {
            If ($retrycount -ge $retries) {
                Throw
            } Else {
                Start-Sleep $secondsDelay
                $retrycount++
            }
        }
    }
}
