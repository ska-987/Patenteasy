@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Installation de Patenteasy - ska_987

py -3.10 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10,1) else 1)" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Python 3.10.0 n'est pas compatible avec la compilation de Patenteasy.
    echo Installez Python 3.10.11 64 bits puis relancez INSTALLER.cmd.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3.10 -m venv .venv
    if errorlevel 1 goto erreur
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto erreur
echo.
echo Installation terminee. Lancez LANCER.cmd.
pause
exit /b 0
:erreur
echo Installation interrompue. Verifiez Python 3.10.11 et votre connexion Internet.
pause
exit /b 1
