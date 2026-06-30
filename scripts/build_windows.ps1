$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python scripts/generate_assets.py
python -m pytest
python -m PyInstaller --noconfirm --clean packaging/windows/AttackSharkX11.spec

$IsccCandidates = @(
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) {
    throw "Inno Setup 6 was not found. Install it, then run this script again."
}

& $Iscc packaging/windows/AttackSharkX11.iss
Write-Host "Installer created in dist/installer"
