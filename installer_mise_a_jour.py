# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
"""Attend la fermeture de Patenteasy avant installation."""

import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import sys


def installer(
    pid: int,
    fichier: str | Path,
    empreinte_attendue: str,
    taille_attendue: int,
):
    fichier = Path(fichier)
    pid = int(pid)
    taille_attendue = int(taille_attendue)

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)

    kernel.OpenProcess.argtypes = [
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
    ]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [
        wintypes.HANDLE, wintypes.DWORD
    ]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL

    # Attend au maximum deux minutes la fin du processus.
    handle = kernel.OpenProcess(0x00100000, False, pid)

    if handle:
        try:
            resultat = kernel.WaitForSingleObject(handle, 120_000)
            if resultat != 0:
                raise RuntimeError(
                    "Patenteasy ne s'est pas ferme. "
                    "Installation annulee."
                )
        finally:
            kernel.CloseHandle(handle)
    elif ctypes.get_last_error() != 87:
        raise ctypes.WinError(ctypes.get_last_error())

    if fichier.suffix.lower() != ".exe":
        raise RuntimeError("Format d'installation incorrect.")

    empreinte = hashlib.sha256()
    taille = 0

    with fichier.open("rb") as source:
        while True:
            bloc = source.read(65536)
            if not bloc:
                break
            taille += len(bloc)
            if taille > taille_attendue:
                raise RuntimeError("Taille du fichier incorrecte.")
            empreinte.update(bloc)

    if (
        taille != taille_attendue
        or empreinte.hexdigest().lower()
        != empreinte_attendue.lower()
    ):
        raise RuntimeError(
            "Le fichier a change. Installation annulee."
        )

    os.startfile(str(fichier.resolve()))


if __name__ == "__main__":
    try:
        if len(sys.argv) != 5:
            raise RuntimeError("Arguments de mise à jour incomplets.")
        installer(
            int(sys.argv[1]),
            sys.argv[2],
            sys.argv[3],
            int(sys.argv[4]),
        )
    except Exception as erreur:
        ctypes.windll.user32.MessageBoxW(
            None, str(erreur), "Patenteasy — Mise à jour", 0x10
        )
        raise SystemExit(1)
