# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path


def root():
    return Path(__file__).resolve().parents[1]


def test_lanceur_windows_qt_sans_serveur_ni_webview():
    source=(root()/'application_windows.py').read_text(encoding='utf-8')
    assert 'from qt_app import run' in source
    assert 'ServeurLocal' not in source
    assert 'import webview' not in source.lower()
    assert 'import uvicorn' not in source.lower()


def test_interface_qt_native_presente():
    source=(root()/'qt_app.py').read_text(encoding='utf-8')
    assert 'from PySide6.QtWidgets import' in source
    assert 'class MainWindow(QMainWindow)' in source
    assert 'QStackedWidget' in source
    assert 'import webview' not in source.lower()


def test_raccourcis_sans_cmd_et_sans_python_console():
    nsis=(root()/'distribution/installer_windows.nsi').read_text(encoding='utf-8')
    lignes=[l for l in nsis.splitlines() if 'CreateShortcut' in l]
    assert len(lignes)==2
    assert 'Delete "$DESKTOP\\Patenteasy.lnk"' in nsis
    assert all('patenteasy.ico' in l for l in lignes)
    assert all('runtime\\pythonw.exe' in l and 'application_windows.py' in l for l in lignes)


def test_installateurs_ne_demandent_plus_webview2():
    nsis=(root()/'distribution/installer_windows.nsi').read_text(encoding='utf-8').lower()
    ps=(root()/'distribution/windows/installer.ps1').read_text(encoding='utf-8').lower()
    assert 'microsoftedgewebview2setup.exe' not in nsis
    assert 'microsoftedgewebview2setup.exe' not in ps
    assert 'test-webview2' not in ps


def test_compilation_pyinstaller_qt_et_windowed():
    script=(root()/'distribution/COMPILER_WINDOWS.cmd').read_text(encoding='utf-8')
    assert '--windowed' in script
    assert 'qt_app' in script
    assert 'PySide6.QtWidgets' in script
    assert '--collect-all webview' not in script
    assert 'pythonnet' not in script
