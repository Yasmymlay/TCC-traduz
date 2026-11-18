# Gera a versão instalável do Tradutor de Aulas.
#   1. copia os modelos Argos e o Tesseract instalados nesta máquina
#   2. empacota com PyInstaller   -> dist\TradutorDeAulas\
#   3. gera o instalador com Inno Setup -> dist\TradutorDeAulas-Setup-<versao>.exe
# Uso (na raiz do projeto):  powershell -ExecutionPolicy Bypass -File packaging\build.ps1
param(
    [string]$Version = "1.0.0",
    [string]$ArgosPackages = "$env:USERPROFILE\.local\share\argos-translate\packages",
    [string]$Tesseract = "C:\Program Files\Tesseract-OCR",
    [string]$Iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root ".venv\Scripts\python.exe"
$res = Join-Path $root "build\resources"

foreach ($path in @($python, $ArgosPackages, "$Tesseract\tesseract.exe", $Iscc)) {
    if (-not (Test-Path $path)) { throw "Não encontrado: $path" }
}

Write-Host "Copiando modelos e Tesseract..."
if (Test-Path $res) { Remove-Item $res -Recurse -Force }
New-Item -ItemType Directory -Force "$res\argos-packages", "$res\tesseract\tessdata" | Out-Null
Copy-Item "$ArgosPackages\*" "$res\argos-packages" -Recurse
# Do Tesseract só vão o executável, as DLLs e os idiomas usados.
Copy-Item "$Tesseract\*.exe", "$Tesseract\*.dll" "$res\tesseract"
Remove-Item "$res\tesseract\unins*.exe" -ErrorAction SilentlyContinue
foreach ($lang in "por", "eng", "spa", "osd") {
    Copy-Item "$Tesseract\tessdata\$lang.traineddata" "$res\tesseract\tessdata"
}

Write-Host "Empacotando com PyInstaller..."
$env:TRADUTOR_RESOURCES = $res
& $python -m PyInstaller --noconfirm --clean --distpath "$root\dist" --workpath "$root\build\pyinstaller" "$PSScriptRoot\TradutorDeAulas.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou." }

Write-Host "Gerando o instalador..."
& $Iscc "/DAppVersion=$Version" "/DSourceDir=$root\dist\TradutorDeAulas" "/O$root\dist" "$PSScriptRoot\installer.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falhou." }
Get-Item "$root\dist\TradutorDeAulas-Setup-$Version.exe" | Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,1)}}
