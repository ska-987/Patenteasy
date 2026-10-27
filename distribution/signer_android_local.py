# SPDX-License-Identifier: GPL-3.0-or-later
"""Signature locale de l'APK contrôlée ; aucune publication réseau."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

CERTIFICAT = 'cfc8d95ee97be9a7a80eca28de72178d7e9cd01236dc8187c69ba1c60ff7c119'


def signer(dossier):
    dossier = Path(dossier).resolve()
    m = json.loads((dossier/'android-verifie.json').read_text(encoding='utf-8'))
    if (m['version'], m['versionCode'], m['package']) != ('0.4.6', 14, 'pf.ska987.patenteasy.local'):
        raise ValueError('Construction Android incorrecte.')
    candidat = dossier/'Patenteasy-Android-0.4.6-A-SIGNER.apk'
    jar = dossier/'apksigner.jar'
    if candidat.stat().st_size != m['taille'] or hashlib.sha256(candidat.read_bytes()).hexdigest() != m['sha256']:
        raise ValueError('APK incomplète ou modifiée.')
    if hashlib.sha256(jar.read_bytes()).hexdigest() != m['apksigner_sha256']:
        raise ValueError('Outil de signature modifié.')
    with zipfile.ZipFile(candidat) as z:
        if json.loads(z.read('assets/licence_editeur.json'))['cle_publique_ed25519'] != 'JYN0UatgXCsf8FNSBSTxqzS0E2R/VzD3F3gXTtSFGtU=':
            raise ValueError('Clé publique de licence incorrecte.')
    cle = Path(os.environ['PATENTEASY_KEYSTORE'])
    if not cle.is_file() or not os.environ.get('PATENTEASY_KEY_PASSWORD'):
        raise ValueError('Clé Android originale et mot de passe requis.')
    java = os.environ.get('PATENTEASY_JAVA', 'java')
    # Le JKS reste chiffré. Un chemin court évite les caractères invisibles
    # et les problèmes d'encodage rencontrés avec certains chemins Windows.
    with tempfile.TemporaryDirectory(prefix='patenteasy-signature-') as temporaire:
        temp = Path(temporaire)
        copie = temp/'original.jks'
        shutil.copyfile(cle, copie)
        signe = temp/'signe.apk'
        subprocess.run([java, '-jar', str(jar), 'sign', '--ks', str(copie),
                        '--ks-key-alias', os.environ.get('PATENTEASY_KEY_ALIAS', 'ska987'),
                        '--ks-pass', 'env:PATENTEASY_KEY_PASSWORD',
                        '--key-pass', 'env:PATENTEASY_KEY_PASSWORD',
                        '--out', str(signe), str(candidat)], check=True)
        rapport = subprocess.check_output([java, '-jar', str(jar), 'verify', '--verbose', '--print-certs', str(signe)], text=True)
        certificats = [l.split(':', 1)[1].strip().lower() for l in rapport.splitlines()
                       if 'certificate SHA-256 digest:' in l]
        if certificats != [CERTIFICAT]:
            raise ValueError('Cette clé ne correspond pas à la signature Android originale.')
        with zipfile.ZipFile(candidat) as original, zipfile.ZipFile(signe) as final:
            for nom in original.namelist():
                if not nom.startswith('META-INF/') and original.read(nom) != final.read(nom):
                    raise ValueError('Le contenu de l’APK a changé pendant la signature.')
        sortie = dossier/'Patenteasy-Android-0.4.6.apk'
        shutil.copyfile(signe, sortie.with_suffix('.tmp'))
        sortie.with_suffix('.tmp').replace(sortie)
    print('APK signée et vérifiée :', sortie)
    return sortie


if __name__ == '__main__':
    try:
        signer(sys.argv[1])
    except Exception as erreur:
        print('Signature interrompue :', erreur, file=sys.stderr)
        raise SystemExit(1)
