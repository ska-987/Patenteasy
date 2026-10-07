# SPDX-License-Identifier: GPL-3.0-or-later
"""Contrôle d’intégrité d’un installateur NSIS non signé, avant publication."""
from pathlib import Path
import struct
import zlib
import sys

def verifier(chemin):
    b = Path(chemin).read_bytes()
    signature = b"\xef\xbe\xad\xdeNullsoftInst"
    offset = b.find(signature) - 4
    if offset < 0 or offset + 28 > len(b):
        raise ValueError("En-tête NSIS introuvable.")
    longueur = struct.unpack_from("<I", b, offset + 24)[0]
    if offset + longueur != len(b):
        raise ValueError("Longueur NSIS incorrecte : fichier incomplet ou données supplémentaires.")
    attendu = struct.unpack_from("<I", b, len(b) - 4)[0]
    obtenu = zlib.crc32(b[512:-4]) & 0xffffffff
    if obtenu != attendu:
        raise ValueError("CRC NSIS incorrect : fichier endommagé.")
    return len(b), attendu

if __name__ == "__main__":
    taille, crc = verifier(sys.argv[1])
    print(f"Intégrité NSIS validée : {taille} octets, CRC {crc:08x}.")
