@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Installation de Patenteasy - ska_987

set "PYTHON="

for %%V in (3.14 3.13 3.12 3.11 3.10) do (
    if not defined PYTHON (
        py -%%V -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10,1) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON=py -%%V"
    )
)

if not defined PYTHON (
    echo.
    echo Aucun Python compatible trouve.
    echo Installez Python 3.10.1 ou plus recent, jusqu'a Python 3.14.
    echo Python 3.10.0 est explicitement refuse car incompatible avec PyInstaller.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10,1) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo Ancien environnement virtuel incompatible : suppression.
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    %PYTHON% -m venv .venv
    if errorlevel 1 goto erreur
)

echo Python utilise :
".venv\Scripts\python.exe" --version

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto erreur

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto erreur

echo.
echo Installation terminee. Lancez LANCER.cmd.
pause
exit /b 0

:erreur
echo Installation interrompue. Verifiez Python et votre connexion Internet.
pause
exit /b 1
