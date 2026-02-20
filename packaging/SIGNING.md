# Windows Binary Signing

Instructions for signing the Windows installer using `simple-sign.ps1` and uploading to a GitHub release.

## Prerequisites

- Windows SDK installed (provides `signtool.exe`)
- Yubikey with code signing certificate inserted
- GitHub CLI (`gh`) authenticated

## Steps

First, set the version variable. Either extract it from the latest git tag:

```powershell
$VERSION = git describe --tags --abbrev=0
```

Or set it manually:

```powershell
$VERSION = "v1.42.0"
```

Verify it looks correct:

```powershell
echo $VERSION
```

### 1. Download the unsigned installer

```powershell
gh release download $VERSION -D "$HOME\Downloads\" -p "rotki-win32*.exe"
```

### 2. Sign the binary

```powershell
.\packaging\simple-sign.ps1 -FilePath "$HOME\Downloads\rotki-win32_x64-$VERSION.exe"
```

This will create a `rotki-<version>-signed\` directory under `Downloads` containing the signed executable, its SHA512 hash, and `latest.yml` for the auto-updater.

### 3. Upload the signed artifacts

```powershell
$SIGNED = "$HOME\Downloads\rotki-$($VERSION.TrimStart('v'))-signed"
gh release upload $VERSION "$SIGNED\rotki-win32_x64-$VERSION.exe" --clobber
gh release upload $VERSION "$SIGNED\rotki-win32_x64-$VERSION.exe.sha512" --clobber
gh release upload $VERSION "$SIGNED\latest.yml" --clobber
```

### 4. Cleanup

Remove the downloaded installer, its backup, and the signed output directory:

```powershell
Remove-Item "$HOME\Downloads\rotki-win32_x64-$VERSION.exe" -Force
Remove-Item "$HOME\Downloads\rotki-win32_x64-$VERSION.exe.backup" -Force
Remove-Item $SIGNED -Recurse -Force
```