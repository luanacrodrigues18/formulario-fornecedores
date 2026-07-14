@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
if exist "%~dp0caminhos_rede_alcoa.bat" call "%~dp0caminhos_rede_alcoa.bat"

echo.
echo === Verificacao do Python ===
echo.

set "EXE=python"
if defined PYTHON_EXE set "EXE=%PYTHON_EXE%"

where %EXE% >nul 2>&1
if errorlevel 1 (
  echo [FALHOU] Python nao encontrado no PATH.
  echo.
  echo Como resolver:
  echo   1. Peça à TI instalar Python 3.11 ou 3.12 ^(Add to PATH^)
  echo   2. Ou use Python portatil e configure PYTHON_EXE
  echo      em caminhos_rede_alcoa.bat / setup_outro_pc.bat
  echo   3. Ou use so a nuvem ^(Streamlit Cloud^) — veja COMO_INSTALAR_PYTHON.txt
  echo.
  echo Guia completo: COMO_INSTALAR_PYTHON.txt
  pause
  exit /b 1
)

echo [OK] Python encontrado:
%EXE% --version
echo.

%EXE% -c "import sys; v=sys.version_info; print('Versao:', v.major, v.minor); raise SystemExit(0 if v.major==3 and v.minor>=11 else 1)"
if errorlevel 1 (
  echo [AVISO] Recomendado Python 3.11+. Versoes antigas podem falhar.
) else (
  echo [OK] Versao adequada ^(3.11+^).
)

echo.
%EXE% -c "import venv" 2>nul
if errorlevel 1 (
  echo [FALHOU] Modulo venv indisponivel. Use instalacao completa ou WinPython.
) else (
  echo [OK] Modulo venv disponivel.
)

echo.
%EXE% -m pip --version 2>nul
if errorlevel 1 (
  echo [AVISO] pip nao encontrado. Tentaremos corrigir no setup_outro_pc.bat
) else (
  echo [OK] pip disponivel.
)

echo.
if exist "venv\Scripts\python.exe" (
  echo [OK] Ambiente venv\ ja existe nesta pasta.
) else (
  echo [INFO] Ainda nao ha venv\. Rode setup_outro_pc.bat
)

echo.
echo === Resumo ===
echo Se todos os [OK] apareceram, rode: setup_outro_pc.bat
echo Se faltou Python, leia: COMO_INSTALAR_PYTHON.txt
echo.
pause
endlocal
