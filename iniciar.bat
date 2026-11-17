@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "VENV_DIR=%~dp0.venv"
set "APP_PYTHON=%VENV_DIR%\Scripts\python.exe"

py -3.13 --version >nul 2>nul
if errorlevel 1 (
    echo Python 3.13 nao foi encontrado pelo launcher py.
    echo Instale Python 3.13 e confirme que o comando py funciona.
    pause
    exit /b 1
)

if not exist "%APP_PYTHON%" (
    echo Criando o ambiente virtual .venv com Python 3.13...
    py -3.13 -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Nao foi possivel criar .venv. Verifique a instalacao do Python 3.13.
        pause
        exit /b 1
    )
)

"%APP_PYTHON%" -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 13))" >nul 2>nul
if errorlevel 1 (
    echo O ambiente .venv existente nao usa Python 3.13.
    echo Renomeie .venv para preservar o ambiente antigo e execute este arquivo novamente.
    pause
    exit /b 1
)

"%APP_PYTHON%" -c "import flask, requests, docx, pptx, pypdf, argostranslate, reportlab, pymupdf, pytesseract, PIL" >nul 2>nul
if errorlevel 1 (
    echo Algumas dependencias Python do projeto ainda nao estao instaladas.
    choice /C SN /N /M "Deseja instalar requirements.txt no ambiente .venv agora? [S/N] "
    if errorlevel 2 (
        echo Instalacao cancelada. Para instalar manualmente, execute:
        echo py -3.13 -m pip --python ".venv\Scripts\python.exe" install -r requirements.txt
        pause
        exit /b 1
    )

    py -3.13 -m pip --python "%APP_PYTHON%" install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo A instalacao das dependencias falhou. Verifique a conexao e as mensagens acima.
        pause
        exit /b 1
    )

    "%APP_PYTHON%" -c "import flask, requests, docx, pptx, pypdf, argostranslate, reportlab, pymupdf, pytesseract, PIL" >nul 2>nul
    if errorlevel 1 (
        echo Ainda faltam dependencias apos a instalacao. Verifique requirements.txt e tente novamente.
        pause
        exit /b 1
    )
)

set "LIBRETRANSLATE_EXE=%~dp0.venv-lt\Scripts\libretranslate.exe"
if not exist "%LIBRETRANSLATE_EXE%" (
    where libretranslate >nul 2>nul
    if not errorlevel 1 set "LIBRETRANSLATE_EXE=libretranslate"
)

if defined LIBRETRANSLATE_EXE (
    powershell -NoProfile -Command "try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/languages' -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>nul
    if errorlevel 1 (
        echo Iniciando LibreTranslate como primeira opcao. A traducao local Argos continua disponivel como alternativa.
        start "LibreTranslate" "%LIBRETRANSLATE_EXE%" --host 127.0.0.1 --port 5000 --load-only pt,en,es
    )
) else (
    echo LibreTranslate nao foi encontrado. O aplicativo tentara usar os modelos Argos locais.
)

powershell -NoProfile -Command "try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/api/health' -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 (
    echo Iniciando o aplicativo web...
    start "Tradutor de Aulas" "%APP_PYTHON%" "%~dp0app.py"
    powershell -NoProfile -Command "$deadline = (Get-Date).AddSeconds(30); do { try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/api/health' -TimeoutSec 2; exit 0 } catch { Start-Sleep -Seconds 1 } } while ((Get-Date) -lt $deadline); exit 1"
    if errorlevel 1 (
        echo O aplicativo web nao iniciou. Verifique as dependencias e a janela do Tradutor de Aulas.
        pause
        exit /b 1
    )
)

start "" http://127.0.0.1:5001
