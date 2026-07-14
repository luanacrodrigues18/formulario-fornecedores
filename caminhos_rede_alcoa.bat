@echo off
REM ======================================================================
REM  Caminhos de rede Alcoa — Formulario de Fornecedores (Alumar / Vitoria)
REM  Usado por: mapear_rede_alcoa.bat e pelos scripts de instalacao
REM ======================================================================

REM Unidade mapeada
set "ALCOA_DRIVE=V:"

REM Pasta UNC (InfoShare Alumar - operacao Vitoria)
set "ALCOA_UNC=\\noa.alcoa.com\dfs\PGH\InfoShare1\GSS_PMO\AA_Static\116_PSC_PO_Followup\Alumar-operação\Vitoria"

REM Subpasta do projeto na unidade mapeada (ajuste se a pasta tiver outro nome)
set "ALCOA_PROJETO=%ALCOA_DRIVE%\FormularioFornecedores"

REM Pasta local recomendada para rodar Python/Streamlit
set "ALCOA_LOCAL=C:\Projetos\FormularioFornecedores"

REM Python (descomente se nao estiver no PATH — ex.: portatil / WinPython)
REM set "PYTHON_EXE=C:\PythonPortable\python.exe"
REM set "PYTHON_EXE=C:\Python312\python.exe"
if not defined PYTHON_EXE set "PYTHON_EXE=python"
