$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
& ".\.venv\Scripts\python.exe" tools\build_icon.py
& ".\.venv\Scripts\pyinstaller.exe" --clean --noconfirm FixMyFolder.spec
Copy-Item -Force -Path ".\dist\FixMyFolder.exe" -Destination ".\fixmyfolder-portable.exe"

Write-Host ""
Write-Host "Built executable:"
Write-Host "$projectRoot\fixmyfolder-portable.exe"
