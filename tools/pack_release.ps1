<#
.SYNOPSIS
    ZBridge Release Packager
    Packages the ZBridge plugin for distribution as a ZBrush plugin.
    
.DESCRIPTION
    Creates a release package containing:
    - ZBridge.txt (main plugin script)
    - ZBridgeData/ (DLL files, ZBridgePacker.exe, and resources)
    
.PARAMETER Version
    The version string (e.g. "0.5.0")
    
.PARAMETER OutputDir
    The output directory for the release package (default: ./releases/)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

# Resolve paths
$projectRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $projectRoot

if (-not $OutputDir) {
    $OutputDir = Join-Path $projectRoot "releases\$Version"
}

Write-Host "=== ZBridge Release Packager ===" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor White
Write-Host "Output: $OutputDir" -ForegroundColor White
Write-Host ""

# Create output directory
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# Create clean plugin structure
$releasePluginDir = Join-Path $OutputDir "ZBridge"
New-Item -ItemType Directory -Path $releasePluginDir -Force | Out-Null

# Copy main plugin script
Write-Host "Copying ZBridge.txt..." -ForegroundColor Yellow
$zscriptDir = Join-Path $projectRoot "src\zscript"
Copy-Item (Join-Path $zscriptDir "ZBridge.txt") $releasePluginDir -Force

# Create ZBridgeData directory and copy dependencies
Write-Host "Copying ZBridgeData/..." -ForegroundColor Yellow
$dataDestDir = Join-Path $releasePluginDir "ZBridgeData"
New-Item -ItemType Directory -Path $dataDestDir -Force | Out-Null

# Copy ZFileUtils DLLs
$refDir = Join-Path $projectRoot "refrenece\ZFileUtils_2021_01A\MyPluginData"
Copy-Item (Join-Path $refDir "ZFileUtils64.dll") $dataDestDir -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $refDir "ZFileUtils.lib") $dataDestDir -Force -ErrorAction SilentlyContinue

# Copy C++ pack/unpack tool
$toolsDir = Join-Path $projectRoot "src\tools"
Copy-Item (Join-Path $toolsDir "ZBridgePacker.exe") $dataDestDir -Force

# Create version info file
$versionInfo = @"
ZBridge Plugin
Version: $Version
Release Date: $(Get-Date -Format 'yyyy-MM-dd')
ZBrush Compatibility: 2021+

Plugin Structure:
  ZBridge.txt          - Main plugin entry point
  ZBridgeData/         - Plugin data folder
    ZFileUtils64.dll   - Folder rename support (Windows)
    ZFileUtils.lib     - Folder rename support (Mac)
    ZBridgePacker.exe  - .zbridge pack/unpack tool

Features:
  - Single-file .zbridge packaging (Store mode, Zip64)
  - Folder structure reconstruction
  - Visibility recovery
  - Subdivision level restoration

Installation:
  1. Copy the entire "ZBridge" folder to:
     <ZBrush Installation>/ZStartup/ZPlugs64/
  2. Restart ZBrush
  3. Find ZBridge under the ZPlugin palette

"@
$versionInfo | Out-File -FilePath (Join-Path $dataDestDir "VERSION.txt") -Encoding ASCII

# Calculate sizes
$dirSize = (Get-ChildItem -Path $releasePluginDir -Recurse | Measure-Object -Property Length -Sum).Sum

Write-Host ""
Write-Host "=== Release packaged successfully ===" -ForegroundColor Green
Write-Host "Directory: $releasePluginDir" -ForegroundColor White
Write-Host "Total Size: $([math]::Round($dirSize/1KB, 1)) KB" -ForegroundColor White
Write-Host "Files: $((Get-ChildItem -Path $releasePluginDir -Recurse -File).Count)" -ForegroundColor White
Write-Host ""
Write-Host "Structure:" -ForegroundColor Cyan
Get-ChildItem -Path $releasePluginDir -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Replace($releasePluginDir, "ZBridge")
    Write-Host "  $rel"
}
Write-Host ""
Write-Host "To install, copy the ZBridge folder to ZStartup/ZPlugs64/ in your ZBrush installation." -ForegroundColor Cyan
