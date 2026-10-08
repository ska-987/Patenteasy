@echo off
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
    echo Executez INSTALLER.cmd auparavant.
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install pyinstaller==6.16.0 -r requirements.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name Patenteasy --icon static\patenteasy.ico --hidden-import qt_app --hidden-import database --hidden-import gestion --hidden-import editeur --hidden-import mises_a_jour --hidden-import installer_mise_a_jour --hidden-import verification_distribution --hidden-import pdf_documents --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui --hidden-import PySide6.QtWidgets --add-data "static;static" --add-data "configuration_editeur.json;." --add-data "LICENSE;." application_windows.py
if errorlevel 1 exit /b 1
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" distribution\Patenteasy.iss
) else if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" distribution\Patenteasy.iss
) else (
    echo Executable portable cree dans dist\Patenteasy. Installez Inno Setup 6 pour produire l'installateur.
)
pause
