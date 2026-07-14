@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
call "%~dp0caminhos_rede_alcoa.bat"

echo.
echo === Copiar projeto da rede para o disco local ===
echo Origem:  %ALCOA_PROJETO%
echo Destino: %ALCOA_LOCAL%
echo.

if not exist "%ALCOA_DRIVE%\" (
  echo Unidade %ALCOA_DRIVE% nao mapeada. Rodando mapear_rede_alcoa.bat ...
  call "%~dp0mapear_rede_alcoa.bat"
)

if not exist "%ALCOA_PROJETO%\" (
  echo [AVISO] Pasta do projeto na rede nao encontrada:
  echo   %ALCOA_PROJETO%
  echo.
  echo Crie a pasta FormularioFornecedores na rede ou ajuste
  echo ALCOA_PROJETO em caminhos_rede_alcoa.bat
  echo.
  echo Se o projeto ja esta em outro subcaminho de %ALCOA_DRIVE%,
  echo edite caminhos_rede_alcoa.bat e rode este script de novo.
  pause
  exit /b 1
)

if not exist "C:\Projetos" mkdir "C:\Projetos"

echo Copiando arquivos ^(exceto venv^)...
robocopy "%ALCOA_PROJETO%" "%ALCOA_LOCAL%" /E /XD venv __pycache__ .git /NFL /NDL /NJH /NJS
echo.

echo Pronto. Abrindo pasta local...
explorer "%ALCOA_LOCAL%"
echo.
echo Agora, na pasta %ALCOA_LOCAL%:
echo   1. Duplo clique em setup_outro_pc.bat
echo   2. Depois rodar_formulario.bat
echo.
pause
endlocal
