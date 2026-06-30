$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python scripts/generate_assets.py
python -m pytest
python -m PyInstaller --noconfirm --clean packaging/windows/AttackSharkX11.spec

# Locate the Inno Setup compiler robustly on developer machines and CI runners.
$IsccCandidates = @()

if ($env:INNO_SETUP_COMPILER) {
    $IsccCandidates += $env:INNO_SETUP_COMPILER
}

$IsccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if ($IsccCommand) {
    $IsccCandidates += $IsccCommand.Source
}

if (${env:ProgramFiles(x86)}) {
    $IsccCandidates += Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
}

if ($env:ProgramFiles) {
    $IsccCandidates += Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
}

$Iscc = $IsccCandidates |
    Where-Object { $_ -and (Test-Path $_) } |
    Select-Object -Unique -First 1

if (-not $Iscc) {
    $Checked = ($IsccCandidates | Where-Object { $_ } | Select-Object -Unique) -join "`n - "
    throw "Inno Setup 6 was not found. Checked:`n - $Checked"
}

Write-Host "Using Inno Setup compiler: $Iscc"
& $Iscc packaging/windows/AttackSharkX11.iss

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed with exit code $LASTEXITCODE."
}

Write-Host "Installer created in dist/installer"
