@echo off
chcp 65001 >nul
setlocal

REM ======================================================================
REM  Instalação do ambiente no PC (primeira vez)
REM  Preferência: rode no disco LOCAL (C:\Projetos\FormularioFornecedores)
REM  Caminhos Alcoa: caminhos_rede_alcoa.bat / mapear_rede_alcoa.bat
REM ======================================================================

REM Se o Python não estiver no PATH, configure em caminhos_rede_alcoa.bat:
REM   set "PYTHON_EXE=C:\PythonPortable\python.exe"
if not defined PYTHON_EXE set PYTHON_EXE=python

cd /d "%~dp0"
if exist "%~dp0caminhos_rede_alcoa.bat" call "%~dp0caminhos_rede_alcoa.bat"
if defined PYTHON_EXE set "PYTHON_EXE=%PYTHON_EXE%"

echo.
echo === Pasta do projeto ===
echo %CD%
echo.

echo %CD% | findstr /B "\\" >nul
if %ERRORLEVEL%==0 (
  echo [AVISO] Voce parece estar em caminho de REDE UNC \\...
  echo         O ideal e copiar o projeto para C:\Projetos\ e rodar de la.
  echo.
)

where %PYTHON_EXE% >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python nao encontrado: "%PYTHON_EXE%"
  echo.
  echo Instale Python 3.11+ ^(marque Add to PATH^) ou edite PYTHON_EXE neste .bat
  echo Veja COMO_RODAR_OUTRO_PC.txt
  pause
  exit /b 1
)

echo Python encontrado:
%PYTHON_EXE% --version
echo.

if not exist "requirements.txt" (
  echo [ERRO] requirements.txt nao encontrado nesta pasta.
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo Criando ambiente virtual venv\ ...
  %PYTHON_EXE% -m venv venv
  if errorlevel 1 (
    echo [ERRO] Falha ao criar venv. Peça à TI para instalar Python completo.
    pause
    exit /b 1
  )
) else (
  echo Ambiente venv\ ja existe.
)

echo.
echo Instalando dependencias...
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo [ERRO] Falha no pip install.
  pause
  exit /b 1
)

if not exist ".env" (
  if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo.
    echo [ATENCAO] Criei .env a partir de .env.example — preencha SUPABASE_URL e SUPABASE_KEY.
  )
)

echo.
echo === Pronto ===
echo Proximo passo:
echo   1. Edite o arquivo .env
echo   2. Coloque relatorio_fup.xlsm e fornecedores_codigos.json nesta pasta
echo   3. Duplo clique em rodar_formulario.bat
echo.
pause
endlocal
