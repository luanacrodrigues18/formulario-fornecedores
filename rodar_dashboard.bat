@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
  echo Ambiente venv\ nao encontrado. Rode primeiro: setup_outro_pc.bat
  pause
  exit /b 1
)

call "venv\Scripts\activate.bat"
echo Abrindo dashboard ^(pede login da equipe^).
echo Feche esta janela para encerrar o servidor.
echo.
streamlit run dashboard.py
pause
