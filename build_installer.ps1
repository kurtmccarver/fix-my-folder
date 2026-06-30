param(
    [switch]$InstallInno
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

& "$projectRoot\build_exe.ps1"

$isccCandidates = @(@(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) })

if (-not $isccCandidates) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        $isccCandidates = @($command.Source)
    }
}

if (-not $isccCandidates) {
    if ($InstallInno) {
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $winget) {
            Write-Host ""
            Write-Host "Windows Package Manager was not found."
            Write-Host "Install Inno Setup 6 from https://jrsoftware.org/isinfo.php, then run this script again."
            exit 1
        }

        Write-Host "Installing Inno Setup 6..."
        & $winget.Source install --id JRSoftware.InnoSetup --exact --silent --accept-package-agreements --accept-source-agreements

        $isccCandidates = @(@(
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
        ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) })
    }
}

if (-not $isccCandidates) {
    Write-Host ""
    Write-Host "Inno Setup 6 is required to build the installer."
    Write-Host "Install it from https://jrsoftware.org/isinfo.php or run:"
    Write-Host "winget install JRSoftware.InnoSetup"
    Write-Host ""
    Write-Host "Or let this script install it:"
    Write-Host ".\build_installer.ps1 -InstallInno"
    exit 1
}

& $isccCandidates[0] "$projectRoot\installer.iss"
Copy-Item -Force -Path "$projectRoot\installer\FixMyFolderSetup.exe" -Destination "$projectRoot\FixMyFolderSetup.exe"

Write-Host ""
Write-Host "Built installer:"
Write-Host "$projectRoot\installer\FixMyFolderSetup.exe"
Write-Host "$projectRoot\FixMyFolderSetup.exe"
