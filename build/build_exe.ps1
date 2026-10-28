<#
.SYNOPSIS
    Builds the standalone GameSorter.exe application into the app/ directory using .venv.
#>

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$specFile = Join-Path $scriptDir "GameSorter.spec"
$distDir = Join-Path $projectRoot "app"
$workDir = Join-Path $scriptDir "temp"

if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment not found at '$venvPython'. Please run: python -m venv .venv"
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Building GameSorter.exe into app/ using PyInstaller" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Ensure app directory exists
if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir -Force | Out-Null
}

# Run PyInstaller via virtual environment python
Set-Location $projectRoot
& $venvPython -m PyInstaller $specFile --distpath $distDir --workpath $workDir --noconfirm

# Clean up temporary build artifacts
if (Test-Path $workDir) {
    Remove-Item -Recurse -Force $workDir -ErrorAction SilentlyContinue
}

$outputExe = Join-Path $distDir "GameSorter.exe"
if (Test-Path $outputExe) {
    Write-Host "`n[SUCCESS] Standalone executable created at:" -ForegroundColor Green
    Write-Host "  $outputExe" -ForegroundColor Yellow
} else {
    Write-Error "Build failed: GameSorter.exe was not created."
}
