#Requires -Version 5.1

<#
.SYNOPSIS
    Simple dual-signing script for NSIS executables using signtool and Yubikey

.DESCRIPTION
    This script dual-signs an executable with SHA1 and SHA256 using signtool and a Yubikey,
    then generates a SHA512 hash file.

.PARAMETER FilePath
    Path to the executable file to sign

.PARAMETER CertificateThumbprint
    Certificate thumbprint (optional - will auto-detect if not provided)

.EXAMPLE
    .\simple-sign.ps1 -FilePath "rotki-installer.exe"

.EXAMPLE
    .\simple-sign.ps1 -FilePath "rotki-installer.exe" -CertificateThumbprint "ABC123..."
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,
    
    [Parameter(Mandatory = $false)]
    [string]$CertificateThumbprint
)

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}

function Find-SignTool {
    # Find signtool.exe in common locations
    $signToolPaths = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe",
        "${env:ProgramFiles}\Windows Kits\10\bin\*\x64\signtool.exe",
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x86\signtool.exe",
        "${env:ProgramFiles}\Windows Kits\10\bin\*\x86\signtool.exe"
    )
    
    foreach ($pattern in $signToolPaths) {
        $found = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
        if ($found) {
            return $found.FullName
        }
    }
    
    throw "signtool.exe not found. Please install Windows SDK."
}

function Get-CodeSigningCertificate {
    param([string]$Thumbprint)
    
    # Look in both certificate stores
    $stores = @("Cert:\CurrentUser\My", "Cert:\LocalMachine\My")
    $certificates = @()
    
    foreach ($store in $stores) {
        try {
            $certs = Get-ChildItem -Path $store -CodeSigningCert -ErrorAction SilentlyContinue
            $certificates += $certs
        }
        catch {
            Write-Verbose "Could not access store: $store"
        }
    }
    
    if ($Thumbprint) {
        $cert = $certificates | Where-Object { $_.Thumbprint -eq $Thumbprint }
        if (-not $cert) {
            throw "Certificate with thumbprint '$Thumbprint' not found"
        }
        return $cert
    }
    
    if ($certificates.Count -eq 0) {
        throw "No code signing certificates found. Please ensure your Yubikey is inserted."
    }
    
    if ($certificates.Count -eq 1) {
        return $certificates[0]
    }
    
    # Multiple certificates - let user choose
    Write-Host "Multiple certificates found:"
    for ($i = 0; $i -lt $certificates.Count; $i++) {
        Write-Host "[$($i + 1)] $($certificates[$i].Subject) (Thumbprint: $($certificates[$i].Thumbprint))"
    }
    
    do {
        $choice = Read-Host "Select certificate (1-$($certificates.Count))"
        $index = [int]$choice - 1
    } while ($index -lt 0 -or $index -ge $certificates.Count)
    
    return $certificates[$index]
}

try {
    Write-Log "Starting simple signing process..."
    
    # Validate input file
    if (-not (Test-Path $FilePath)) {
        throw "File not found: $FilePath"
    }
    
    $file = Get-Item $FilePath
    Write-Log "Signing file: $($file.FullName) ($([math]::Round($file.Length / 1MB, 2)) MB)"
    
    # Find signtool
    $signTool = Find-SignTool
    Write-Log "Using signtool: $signTool"
    
    # Get certificate
    $certificate = Get-CodeSigningCertificate -Thumbprint $CertificateThumbprint
    Write-Log "Using certificate: $($certificate.Subject)"
    Write-Log "Certificate thumbprint: $($certificate.Thumbprint)"
    
    # First signature: SHA1 for legacy compatibility
    Write-Log "Applying SHA1 signature..."
    $sha1Args = @(
        "sign"
        "/sha1", $certificate.Thumbprint
        "/fd", "SHA1"
        "/t", "http://timestamp.digicert.com"
        "/v"
        $file.FullName
    )
    
    Write-Verbose "SHA1 command: `"$signTool`" $($sha1Args -join ' ')"
    & $signTool @sha1Args
    
    if ($LASTEXITCODE -ne 0) {
        throw "SHA1 signing failed with exit code: $LASTEXITCODE"
    }
    
    Write-Log "SHA1 signature applied successfully"
    
    # Second signature: SHA256 (dual signing)
    Write-Log "Applying SHA256 signature..."
    $sha256Args = @(
        "sign"
        "/sha1", $certificate.Thumbprint
        "/fd", "SHA256"
        "/tr", "http://timestamp.digicert.com"
        "/td", "SHA256"
        "/as"  # Append signature (dual signing)
        "/v"
        $file.FullName
    )
    
    Write-Verbose "SHA256 command: `"$signTool`" $($sha256Args -join ' ')"
    & $signTool @sha256Args
    
    if ($LASTEXITCODE -ne 0) {
        throw "SHA256 signing failed with exit code: $LASTEXITCODE"
    }
    
    Write-Log "SHA256 signature applied successfully"
    
    # Verify signatures
    Write-Log "Verifying signatures..."
    & $signTool verify /pa /v $file.FullName
    
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Signature verification failed"
    } else {
        Write-Log "Signatures verified successfully"
    }
    
    # Generate SHA512 hash
    Write-Log "Generating SHA512 hash..."
    $hash = Get-FileHash -Path $file.FullName -Algorithm SHA512
    $hashFileName = "$($file.FullName).sha512"
    
    # Format: hash *filename (compatible with sha512sum)
    $hashContent = "$($hash.Hash.ToLower()) *$($file.Name)"
    $hashContent | Out-File -FilePath $hashFileName -Encoding ASCII
    
    Write-Log "Process completed successfully!"
    Write-Log "Signed file: $($file.FullName)"
    Write-Log "SHA512 hash: $hashFileName"
    
    # Display file info
    $signedSize = [math]::Round((Get-Item $file.FullName).Length / 1MB, 2)
    Write-Log "Final size: $signedSize MB"
}
catch {
    Write-Log "Error: $($_.Exception.Message)" -Level "ERROR"
    exit 1
}