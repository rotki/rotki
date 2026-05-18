#Requires -Version 5.1

<#
.SYNOPSIS
    Step-by-step signed-release workflow for the Windows installer.

.DESCRIPTION
    Automates the procedure documented in packaging/SIGNING.md:
      1. Download the unsigned installer and its published SHA512, verify the hash.
      2. Sign the binary via packaging/simple-sign.ps1.
      3. Upload signed artifacts (exe, sha512, latest.yml) to the GitHub release.
      4. Clean up local files.

    Each step is executed by Invoke-Step which prints a header, runs the step,
    runs its verification block, and halts on the first failure.

.PARAMETER Version
    Release tag, e.g. v1.42.0. Defaults to the tag of the most recent draft release
    on GitHub (ordered by createdAt).

.PARAMETER DownloadDir
    Directory to download the installer into. Defaults to $HOME\Downloads.

.PARAMETER SkipCleanup
    If set, the final cleanup step is skipped.

.EXAMPLE
    .\packaging\sign-release.ps1

.EXAMPLE
    .\packaging\sign-release.ps1 -Version v1.42.0
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$Version,

    [Parameter(Mandatory = $false)]
    [string]$DownloadDir = (Join-Path $HOME 'Downloads'),

    [Parameter(Mandatory = $false)]
    [switch]$SkipCleanup,

    [Parameter(Mandatory = $false)]
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message, [string]$Level = 'INFO')
    $ts = Get-Date -Format 'HH:mm:ss'
    $color = switch ($Level) {
        'OK'    { 'Green' }
        'ERROR' { 'Red' }
        'WARN'  { 'Yellow' }
        default { 'Cyan' }
    }
    Write-Host "[$ts] [$Level] $Message" -ForegroundColor $color
}

function Confirm-Continue {
    param([Parameter(Mandatory = $true)][string]$Prompt)
    if ($Yes) {
        Write-Step "$Prompt -> auto-confirmed (-Yes)." 'WARN'
        return
    }
    $resp = Read-Host "$Prompt [y/N]"
    if ($resp -notmatch '^(y|Y|yes|YES)$') {
        Write-Step 'Aborted by user.' 'WARN'
        # Exit 2 so CI/automation can distinguish a user-cancelled run from a
        # successful one (exit 0) or a failure (exit 1).
        exit 2
    }
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action,
        [Parameter(Mandatory = $true)][scriptblock]$Verify
    )

    Write-Host ''
    Write-Host ('=' * 72) -ForegroundColor DarkGray
    Write-Step "STEP: $Name"
    Write-Host ('=' * 72) -ForegroundColor DarkGray

    try {
        & $Action
    }
    catch {
        Write-Step "Step '$Name' failed during execution: $($_.Exception.Message)" 'ERROR'
        exit 1
    }

    try {
        $ok = & $Verify
        if (-not $ok) {
            Write-Step "Verification failed for step '$Name'." 'ERROR'
            exit 1
        }
        Write-Step "Verified: $Name" 'OK'
    }
    catch {
        Write-Step "Verification threw for step '$Name': $($_.Exception.Message)" 'ERROR'
        exit 1
    }
}

# ---- Resolve version --------------------------------------------------------

if (-not $Version) {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Step "'gh' not found; cannot auto-detect latest draft release. Pass -Version explicitly." 'ERROR'
        exit 1
    }
    try {
        # Do the filter/sort/pick inside gh via --jq so we get exactly one
        # tagName string back. Avoids PS 5.1 pipeline quirks where the
        # parsed array was re-expanding into all tagNames. No inner quotes
        # in the jq expression -- PS 5.1's native-arg quoting mangles them.
        $jq = '[.[] | select(.isDraft)] | sort_by(.createdAt) | last | .tagName'
        $tag = & gh release list --limit 50 --json tagName,isDraft,createdAt --jq $jq 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "gh release list failed (exit $LASTEXITCODE)."
        }
        $Version = (($tag -join "`n").Trim())
        # jq emits the literal string "null" when no draft matched.
        if (-not $Version -or $Version -eq 'null') {
            throw 'No draft release found on GitHub.'
        }
        Write-Step "Auto-detected most recent draft release: $Version"
    }
    catch {
        Write-Step "Could not resolve version from GitHub drafts: $($_.Exception.Message). Pass -Version explicitly." 'ERROR'
        exit 1
    }
}

if ($Version -notmatch '^v\d+\.\d+\.\d+') {
    Write-Step "Version '$Version' does not look like a release tag (expected like v1.42.0)." 'ERROR'
    exit 1
}

$versionNoV   = $Version.TrimStart('v')
$installerName = "rotki-win32_x64-$Version.exe"
$installerPath = Join-Path $DownloadDir $installerName
$shaName       = "$installerName.sha512"
$shaPath       = Join-Path $DownloadDir $shaName
$signedDir     = Join-Path $DownloadDir "rotki-$versionNoV-signed"
$signedExe     = Join-Path $signedDir $installerName
$signedSha     = Join-Path $signedDir "$installerName.sha512"
$signedYml     = Join-Path $signedDir 'latest.yml'
$backupPath    = "$installerPath.backup"

Write-Step "Version:        $Version"
Write-Step "Installer:      $installerPath"
Write-Step "Signed output:  $signedDir"

# ---- Preflight: surface anything that already exists -----------------------

$preexisting = @()
foreach ($p in @($installerPath, $backupPath, $shaPath, $signedDir)) {
    if (Test-Path $p) { $preexisting += $p }
}
if ($preexisting.Count -gt 0) {
    Write-Host ''
    Write-Step 'The following paths already exist from a previous run:' 'WARN'
    foreach ($p in $preexisting) { Write-Step "  - $p" }
    Confirm-Continue -Prompt 'Overwrite/remove them and continue?'
    foreach ($p in $preexisting) {
        if (Test-Path $p) {
            if ((Get-Item $p).PSIsContainer) { Remove-Item $p -Recurse -Force }
            else { Remove-Item $p -Force }
        }
    }
    Write-Step 'Cleaned pre-existing paths.' 'OK'
}

# ---- Preflight --------------------------------------------------------------

Invoke-Step -Name 'Preflight: required tools available' -Action {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw "'gh' (GitHub CLI) not found in PATH."
    }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "'git' not found in PATH."
    }
    & gh auth status 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "'gh' is not authenticated. Run 'gh auth login' first."
    }
    if (-not (Test-Path $DownloadDir)) {
        New-Item -ItemType Directory -Path $DownloadDir -Force | Out-Null
    }
} -Verify {
    (Test-Path $DownloadDir) -and (Get-Command gh -ErrorAction SilentlyContinue) -ne $null
}

Invoke-Step -Name "Preflight: release $Version exists" -Action {
    & gh release view $Version --json tagName 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub release '$Version' not found."
    }
} -Verify {
    & gh release view $Version --json tagName 2>&1 | Out-Null
    return $LASTEXITCODE -eq 0
}

# ---- Step 1: download installer + sha and verify ---------------------------

Write-Host ''
Write-Step "About to download release artifacts for ${Version}:" 'WARN'
Write-Step "  - $installerName"
Write-Step "  - $shaName"
Write-Step "Target directory: $DownloadDir"
Confirm-Continue -Prompt "Proceed with download of $Version?"

Invoke-Step -Name '1a. Download unsigned installer' -Action {
    & gh release download $Version -D $DownloadDir -p $installerName --clobber
    if ($LASTEXITCODE -ne 0) { throw "gh release download failed for $installerName" }
} -Verify {
    (Test-Path $installerPath) -and ((Get-Item $installerPath).Length -gt 0)
}

Invoke-Step -Name '1b. Download published SHA512 sidecar' -Action {
    & gh release download $Version -D $DownloadDir -p $shaName --clobber
    if ($LASTEXITCODE -ne 0) { throw "gh release download failed for $shaName" }
} -Verify {
    (Test-Path $shaPath) -and ((Get-Item $shaPath).Length -gt 0)
}

Invoke-Step -Name '1c. Verify downloaded installer matches published SHA512' -Action {
    $expectedRaw = (Get-Content -Path $shaPath -Raw).Trim()
    # File may be "<hash>" or "<hash>  filename"; take the first whitespace-separated token.
    $expected = ($expectedRaw -split '\s+')[0].ToUpper()
    if ($expected.Length -ne 128) {
        throw "Expected SHA512 hex of length 128, got length $($expected.Length): '$expected'"
    }
    $actual = (Get-FileHash -Path $installerPath -Algorithm SHA512).Hash.ToUpper()
    Write-Step "Expected: $expected"
    Write-Step "Actual:   $actual"
    if ($expected -ne $actual) {
        throw "SHA512 mismatch -- downloaded installer does NOT match published hash. Aborting."
    }
    $script:OriginalSha512 = $actual
} -Verify {
    return $script:OriginalSha512 -and $script:OriginalSha512.Length -eq 128
}

# ---- Step 2: sign -----------------------------------------------------------

Invoke-Step -Name '2. Sign the binary via simple-sign.ps1' -Action {
    $signScript = Join-Path $PSScriptRoot 'simple-sign.ps1'
    if (-not (Test-Path $signScript)) {
        throw "simple-sign.ps1 not found at $signScript"
    }
    & $signScript -FilePath $installerPath
    if ($LASTEXITCODE -ne 0) { throw "simple-sign.ps1 exited with code $LASTEXITCODE" }
} -Verify {
    (Test-Path $signedExe) -and (Test-Path $signedSha) -and (Test-Path $signedYml)
}

Invoke-Step -Name '2b. Confirm signed binary differs from original (signature applied)' -Action {
    $signedHash = (Get-FileHash -Path $signedExe -Algorithm SHA512).Hash.ToUpper()
    Write-Step "Original SHA512: $script:OriginalSha512"
    Write-Step "Signed SHA512:   $signedHash"
    if ($signedHash -eq $script:OriginalSha512) {
        throw 'Signed file hash equals original -- signing apparently had no effect.'
    }
    $script:SignedSha512 = $signedHash
    # Also compute base64(SHA512) for the latest.yml cross-check below.
    $hashBytes = New-Object byte[] ($signedHash.Length / 2)
    for ($i = 0; $i -lt $signedHash.Length; $i += 2) {
        $hashBytes[$i / 2] = [System.Convert]::ToByte($signedHash.Substring($i, 2), 16)
    }
    $script:SignedSha512Base64 = [System.Convert]::ToBase64String($hashBytes)
} -Verify {
    $script:SignedSha512 -and $script:SignedSha512 -ne $script:OriginalSha512
}

Invoke-Step -Name '2c. Verify latest.yml content matches signed file' -Action {
    $yml = Get-Content -Path $signedYml -Raw
    # Pull the top-level path/sha512/size; the file also contains the same
    # values under files[0], but the top-level keys are what electron-updater
    # consults for the primary asset.
    if ($yml -notmatch '(?m)^path:\s*(.+)$') { throw "latest.yml missing 'path:'" }
    $ymlPath = $Matches[1].Trim()
    if ($yml -notmatch '(?ms)^sha512:\s*(\S+)\s*$') { throw "latest.yml missing top-level 'sha512:'" }
    $ymlSha = $Matches[1].Trim()

    $signedSize = (Get-Item $signedExe).Length
    if ($yml -notmatch '(?m)^\s+size:\s*(\d+)\s*$') { throw "latest.yml missing 'size:'" }
    $ymlSize = [int64]$Matches[1]

    Write-Step "latest.yml path:   $ymlPath"
    Write-Step "latest.yml sha512: $ymlSha"
    Write-Step "latest.yml size:   $ymlSize"

    if ($ymlPath -ne $installerName) {
        throw "latest.yml path '$ymlPath' does not match installer filename '$installerName'."
    }
    if ($ymlSha -ne $script:SignedSha512Base64) {
        throw "latest.yml sha512 does not match recomputed base64(SHA512) of the signed exe."
    }
    if ($ymlSize -ne $signedSize) {
        throw "latest.yml size ($ymlSize) does not match signed exe size ($signedSize)."
    }
} -Verify {
    Test-Path $signedYml
}

# ---- Step 3: upload ---------------------------------------------------------

Write-Host ''
Write-Step "About to upload signed artifacts to release ${Version}:" 'WARN'
Write-Step "  - $signedExe"
Write-Step "  - $signedSha"
Write-Step "  - $signedYml"
Confirm-Continue -Prompt "Proceed with uploading these to GitHub release $Version?"

function Assert-UploadedAsset {
    param(
        [Parameter(Mandatory = $true)][string]$AssetName,
        [Parameter(Mandatory = $true)][string]$LocalPath
    )
    $assetsJson = & gh release view $Version --json assets
    if ($LASTEXITCODE -ne 0) { throw "Could not list assets on release $Version." }
    $asset = ($assetsJson | ConvertFrom-Json).assets | Where-Object { $_.name -eq $AssetName } | Select-Object -First 1
    if (-not $asset) { throw "Asset '$AssetName' not present on release after upload." }
    $localSize = (Get-Item $LocalPath).Length
    if ([int64]$asset.size -ne [int64]$localSize) {
        throw "Uploaded '$AssetName' size $($asset.size) does not match local size $localSize. Re-run the upload."
    }
    Write-Step "Confirmed '$AssetName' present on release with matching size ($localSize bytes)."
}

Invoke-Step -Name '3a. Upload signed installer' -Action {
    & gh release upload $Version $signedExe --clobber
    if ($LASTEXITCODE -ne 0) { throw "Upload of signed exe failed." }
} -Verify {
    Assert-UploadedAsset -AssetName $installerName -LocalPath $signedExe
    return $true
}

Invoke-Step -Name '3b. Upload signed SHA512' -Action {
    & gh release upload $Version $signedSha --clobber
    if ($LASTEXITCODE -ne 0) { throw "Upload of signed sha512 failed." }
} -Verify {
    Assert-UploadedAsset -AssetName "$installerName.sha512" -LocalPath $signedSha
    return $true
}

Invoke-Step -Name '3c. Upload latest.yml for auto-updater' -Action {
    & gh release upload $Version $signedYml --clobber
    if ($LASTEXITCODE -ne 0) { throw "Upload of latest.yml failed." }
} -Verify {
    Assert-UploadedAsset -AssetName 'latest.yml' -LocalPath $signedYml
    return $true
}

# ---- Step 4: cleanup --------------------------------------------------------

if ($SkipCleanup) {
    Write-Step 'Skipping cleanup (-SkipCleanup set).' 'WARN'
}
else {
    Write-Host ''
    Write-Step 'About to remove these local files/folders:' 'WARN'
    foreach ($p in @($installerPath, $backupPath, $shaPath, $signedDir)) {
        if (Test-Path $p) { Write-Step "  - $p" }
    }
    Confirm-Continue -Prompt 'Proceed with cleanup?'

    Invoke-Step -Name '4. Cleanup local artifacts' -Action {
        foreach ($p in @($installerPath, $backupPath, $shaPath)) {
            if (Test-Path $p) { Remove-Item $p -Force }
        }
        if (Test-Path $signedDir) { Remove-Item $signedDir -Recurse -Force }
    } -Verify {
        -not (Test-Path $installerPath) `
            -and -not (Test-Path $backupPath) `
            -and -not (Test-Path $shaPath) `
            -and -not (Test-Path $signedDir)
    }
}

Write-Host ''
Write-Step "All steps completed for release $Version." 'OK'