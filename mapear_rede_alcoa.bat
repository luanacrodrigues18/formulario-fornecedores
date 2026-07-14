@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
call "%~dp0caminhos_rede_alcoa.bat"

echo.
echo === Mapear pasta de rede Alcoa ===
echo UNC:  %ALCOA_UNC%
echo Drive: %ALCOA_DRIVE%
echo.

net use %ALCOA_DRIVE% /delete /y >nul 2>&1
net use %ALCOA_DRIVE% "%ALCOA_UNC%" /persistent:yes
if errorlevel 1 (
  echo [ERRO] Nao foi possivel mapear %ALCOA_DRIVE%
  echo Confira VPN/rede Alcoa e se voce tem permissao na pasta.
  pause
  exit /b 1
)

echo Mapeado com sucesso:
echo   %ALCOA_DRIVE%  -^>  %ALCOA_UNC%
echo.
echo Proximo passo recomendado:
echo   1. Copie o projeto para %ALCOA_LOCAL%  ^(melhor para rodar Python^)
echo   2. Ou use a pasta na rede: %ALCOA_PROJETO%
echo   3. Rode setup_outro_pc.bat na pasta LOCAL
echo.
explorer "%ALCOA_DRIVE%\"
pause
endlocal
