# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
"""Lanceur Windows natif de Patenteasy.

La version bureau utilise PySide6/Qt directement. Aucun serveur local, navigateur
embarqué, Edge/WebView2 ou terminal n'est nécessaire.
"""
from __future__ import annotations

import ctypes
import hashlib
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys


class InstanceWindows:
    """Une seule application Patenteasy par compte Windows."""
    def __init__(self, repertoire: Path):
        self.handle = None
        self.kernel = None
        self.deja_ouverte = False
        if os.name != "nt":
            return
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        self.kernel.CreateMutexW.restype = ctypes.c_void_p
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        nom = "Local\\Patenteasy-" + hashlib.sha256(str(repertoire).encode()).hexdigest()[:24]
        ctypes.set_last_error(0)
        self.handle = self.kernel.CreateMutexW(None, False, nom)
        if not self.handle:
            raise OSError("Impossible de réserver une instance Windows.")
        self.deja_ouverte = ctypes.get_last_error() == 183

    def fermer(self):
        if self.handle and self.kernel:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def dialogue(message: str):
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, message, "Patenteasy", 0x40)
    else:
        print(message, file=sys.stderr)


def lancer_assistant_mise_a_jour() -> int:
    """Exécute le mode d'assistance embarqué dans Patenteasy.exe."""
    try:
        if len(sys.argv) != 6:
            raise RuntimeError("Arguments de mise à jour incomplets.")
        from installer_mise_a_jour import installer
        installer(
            int(sys.argv[2]),
            sys.argv[3],
            sys.argv[4],
            int(sys.argv[5]),
        )
        return 0
    except Exception as erreur:
        if os.name == "nt":
            ctypes.windll.user32.MessageBoxW(
                None,
                str(erreur),
                "Patenteasy — Mise à jour",
                0x10,
            )
        else:
            print(erreur, file=sys.stderr)
        return 1


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        from verification_distribution import verifier
        return verifier(sys.argv[2])

    if len(sys.argv) > 1 and sys.argv[1] == "--install-update":
        return lancer_assistant_mise_a_jour()

    os.environ["PATENTEASY_INSTALLE"] = "1"
    repertoire = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PatenteasyLocal"
    repertoire.mkdir(parents=True, exist_ok=True)
    journaux = repertoire / "journaux"
    journaux.mkdir(exist_ok=True)
    journal = journaux / "application.log"
    logging.basicConfig(
        level=logging.INFO,
        handlers=[RotatingFileHandler(journal, maxBytes=1_000_000, backupCount=2, encoding="utf-8")],
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )
    # pythonw / PyInstaller --windowed ne crée aucune console.
    instance = None
    try:
        instance = InstanceWindows(repertoire)
        if instance.deja_ouverte:
            dialogue("Patenteasy est déjà ouvert. Retrouvez sa fenêtre dans la barre des tâches.")
            return 0
        from qt_app import run
        return run()
    except Exception:
        logging.exception("Démarrage ou exécution interrompus.")
        dialogue(
            "Patenteasy n’a pas pu ouvrir sa fenêtre Qt.\n\n"
            "Vos données sont conservées. Relancez l’installateur puis réessayez.\n\n"
            "Support : sav.centreprotech@proton.me\n"
            "Journal : " + str(journal)
        )
        return 1
    finally:
        if instance is not None:
            instance.fermer()
        logging.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
