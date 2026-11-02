@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "APP_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%APP_PYTHON%" (
    "%APP_PYTHON%" -c "import flask, requests, docx, pptx, pypdf" >nul 2>nul
    if errorlevel 1 set "APP_PYTHON="
) else (
    set "APP_PYTHON="
)

if not defined APP_PYTHON (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined APP_PYTHON (
            "%%P" -c "import flask, requests, docx, pptx, pypdf" >nul 2>nul
            if not errorlevel 1 set "APP_PYTHON=%%P"
        )
    )
)

if not defined APP_PYTHON (
    echo Dependencias do aplicativo ausentes. Execute: python -m pip install -r requirements.txt
    pause
    exit /b 1
)

set "LIBRETRANSLATE_EXE=%~dp0.venv-lt\Scripts\libretranslate.exe"
if not exist "%LIBRETRANSLATE_EXE%" (
    where libretranslate >nul 2>nul
    if errorlevel 1 (
        echo LibreTranslate nao encontrado. Instale o LibreTranslate para iniciar a traducao.
        pause
        exit /b 1
    )
    set "LIBRETRANSLATE_EXE=libretranslate"
)

powershell -NoProfile -Command "try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/languages' -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 (
    echo Iniciando o servico de traducao. Na primeira vez, os modelos de idiomas serao baixados.
    start "LibreTranslate" "%LIBRETRANSLATE_EXE%" --host 127.0.0.1 --port 5000 --load-only pt,en,es
)

echo Aguardando o servico e os modelos de traducao...
powershell -NoProfile -Command "$deadline = (Get-Date).AddMinutes(20); do { try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/languages' -TimeoutSec 2; exit 0 } catch { Start-Sleep -Seconds 2 } } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
    echo O servico de traducao nao ficou pronto. Verifique a janela do LibreTranslate e sua conexao com a internet.
    pause
    exit /b 1
)

powershell -NoProfile -Command "try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/api/health' -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 (
    echo Iniciando o aplicativo web...
    start "Tradutor de Aulas" "%APP_PYTHON%" "%~dp0app.py"
    powershell -NoProfile -Command "$deadline = (Get-Date).AddSeconds(30); do { try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/api/health' -TimeoutSec 2; exit 0 } catch { Start-Sleep -Seconds 1 } } while ((Get-Date) -lt $deadline); exit 1"
    if errorlevel 1 (
        echo O aplicativo web nao iniciou. Verifique a janela do Tradutor de Aulas.
        pause
        exit /b 1
    )
)

start "" http://127.0.0.1:5001
