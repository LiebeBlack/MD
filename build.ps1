<#
.SYNOPSIS
    Compila AZeroCraft Launcher: ejecutable (PyInstaller) e instalador (Inno Setup).

.DESCRIPTION
    Uso:
        .\build.ps1                 # solo el ejecutable en dist\AZeroCraft\
        .\build.ps1 -Installer      # ejecutable + instalador setup.exe
        .\build.ps1 -Clean          # limpia dist/ y build/ antes de compilar
#>
param(
    [switch]$Installer,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Invoke-Step($name, [scriptblock]$block) {
    Write-Host "`n== $name ==" -ForegroundColor Cyan
    & $block
    if ($LASTEXITCODE -ne 0) { throw "$name fallo (exit $LASTEXITCODE)" }
}

if ($Clean) {
    Invoke-Step "Limpieza" {
        Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
    }
}

# 1. Entorno virtual de build (no toca el Python del sistema)
if (-not (Test-Path ".venv-build")) {
    Invoke-Step "Creando .venv-build" { python -m venv .venv-build }
}
$venvPython = Join-Path $root ".venv-build\Scripts\python.exe"

Invoke-Step "Dependencias" {
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt -r requirements-build.txt
}

# 2. Icono del ejecutable
Invoke-Step "Icono" { & $venvPython packaging\make_icon.py }

# 3. Ejecutable con PyInstaller
Invoke-Step "PyInstaller" {
    & $venvPython -m PyInstaller azero.spec --noconfirm --clean
}

Write-Host "`nEjecutable generado en: $root\dist\AZeroCraft\AZeroCraft.exe" -ForegroundColor Green

# 4. Instalador Inno Setup (opcional)
if ($Installer) {
    # La version del instalador debe seguir a APP_VERSION; si no, el
    # setup se generaria con un nombre y una ficha obsoletos.
    $appVersion = (& $venvPython -c "from azero.constants import APP_VERSION; print(APP_VERSION)").Trim()
    if (-not $appVersion) {
        throw "No se pudo leer APP_VERSION de azero.constants."
    }
    $issText = Get-Content -Raw "installer\setup.iss"
    if ($issText -notmatch ('#define AppVersion "' + [regex]::Escape($appVersion) + '"')) {
        throw "APP_VERSION ($appVersion) no coincide con installer\setup.iss."
    }
    $iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if (-not $iscc) {
        $candidates = @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
        ) | Where-Object { Test-Path $_ }
        if ($candidates) { $iscc = $candidates[0] }
    }
    if (-not $iscc) {
        # Intentar instalar Inno Setup 6 via Chocolatey
        if (Get-Command choco.exe -ErrorAction SilentlyContinue) {
            Write-Host "Inno Setup no encontrado; instalando via Chocolatey..." -ForegroundColor Yellow
            choco install innosetup -y --no-progress
            $candidates = @(
                "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
                "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
            ) | Where-Object { Test-Path $_ }
            if ($candidates) { $iscc = $candidates[0] }
        }
    }
    if (-not $iscc) {
        throw "Inno Setup 6 no esta instalado. Instalalo desde https://jrsoftware.org/isinfo.php o con: choco install innosetup"
    }
    Invoke-Step "Inno Setup" { & $iscc installer\setup.iss }
    Write-Host "`nInstalador generado en: $root\dist\AZeroCraft-Setup-*.exe" -ForegroundColor Green
}

Write-Host "`nListo." -ForegroundColor Green
