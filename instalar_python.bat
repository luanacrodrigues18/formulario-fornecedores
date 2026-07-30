@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo ========================================================
echo  INSTALAR PYTHON 3.12 (usuario, sem admin)
echo ========================================================
echo.
echo  Isso instala o Python no SEU usuario do Windows,
echo  nao dentro da pasta do projeto.
echo  Depois use: setup_outro_pc.bat  ou  INICIAR.bat opcao 3
echo.
echo  Precisa de internet. Em PC da Alcoa pode ser bloqueado pela TI.
echo.
pause

set "INSTALLER=%TEMP%\python-3.12.7-amd64.exe"
set "URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"

where python >nul 2>&1
if not errorlevel 1 (
  echo.
  echo Python ja encontrado:
  python --version
  echo.
  echo Se quiser reinstalar mesmo assim, continue.
  pause
)

echo.
echo Baixando instalador...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if (-not (Test-Path '%INSTALLER%')) { Invoke-WebRequest -Uri '%URL%' -OutFile '%INSTALLER%' -UseBasicParsing }; Write-Host 'Download OK'"

if not exist "%INSTALLER%" (
  echo [ERRO] Nao foi possivel baixar o instalador.
  echo Peça o Python 3.12 à TI ou use o app pela nuvem.
  pause
  exit /b 1
)

echo.
echo Instalando Python 3.12 (aguarde)...
start /wait "" "%INSTALLER%" /passive InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1

echo.
echo ========================================
echo  Instalacao enviada.
echo  FECHE e ABRA de novo o Prompt / Explorer
echo  Depois rode: verificar_python.bat
echo  Depois: setup_outro_pc.bat  ou  INICIAR.bat opcao 3
echo ========================================
echo.
pause
endlocal
