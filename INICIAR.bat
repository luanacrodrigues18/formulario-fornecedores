@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if exist "%~dp0caminhos_rede_alcoa.bat" call "%~dp0caminhos_rede_alcoa.bat"

:menu
cls
echo.
echo  ========================================================
echo   FORMULARIO DE FORNECEDORES — Alcoa
echo   Use este menu. Nao precisa saber programar.
echo  ========================================================
echo.
echo   1 - Abrir FORMULARIO  (fornecedores)
echo   2 - Abrir DASHBOARD   (tela interna)
echo   3 - Preparar PC pela primeira vez (instalar pacotes)
echo   4 - Verificar se o Python esta instalado
echo   5 - Mapear pasta de rede Alcoa (V:)
echo   6 - Copiar projeto da rede para C:\Projetos\...
echo   0 - Sair
echo.
set /p OPCAO=Digite o numero e pressione Enter: 

if "%OPCAO%"=="1" goto form
if "%OPCAO%"=="2" goto dash
if "%OPCAO%"=="3" goto setup
if "%OPCAO%"=="4" goto check
if "%OPCAO%"=="5" goto map
if "%OPCAO%"=="6" goto copy
if "%OPCAO%"=="0" goto fim
echo Opcao invalida.
pause
goto menu

:check
call "%~dp0verificar_python.bat"
goto menu

:setup
call "%~dp0setup_outro_pc.bat"
goto menu

:map
call "%~dp0mapear_rede_alcoa.bat"
goto menu

:copy
call "%~dp0copiar_rede_para_local.bat"
goto menu

:form
if not exist "venv\Scripts\activate.bat" (
  echo.
  echo Ainda nao esta preparado. Escolha a opcao 3 primeiro.
  pause
  goto menu
)
call "venv\Scripts\activate.bat"
echo.
echo Abrindo formulario... aguarde o navegador.
echo Para fechar: feche esta janela preta.
echo.
streamlit run app.py
goto menu

:dash
if not exist "venv\Scripts\activate.bat" (
  echo.
  echo Ainda nao esta preparado. Escolha a opcao 3 primeiro.
  pause
  goto menu
)
call "venv\Scripts\activate.bat"
echo.
echo Abrindo dashboard... aguarde o navegador.
echo Para fechar: feche esta janela preta.
echo.
streamlit run dashboard.py
goto menu

:fim
endlocal
exit /b 0
