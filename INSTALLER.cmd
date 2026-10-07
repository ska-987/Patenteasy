@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Installation de Patenteasy - ska_987
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
echo Installation interrompue. Verifiez Python 3.10 et votre connexion Internet.
pause
exit /b 1
