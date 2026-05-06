# Usa apenas o PyPI (ignora Nexus/extra-index do pip global).
# Ex.: .\scripts\pip-pypi.ps1 install -r requirements.txt
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$pipIni = Join-Path $ProjectRoot "pip.ini"
if (-not (Test-Path $pipIni)) {
    Write-Error "Arquivo pip.ini nao encontrado em: $ProjectRoot"
    exit 1
}
$env:PIP_CONFIG_FILE = $pipIni
$py = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "venv nao encontrado. Crie com: python -m venv venv"
    exit 1
}
& $py -m pip @args
exit $LASTEXITCODE
