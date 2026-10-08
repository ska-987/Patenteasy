# SPDX-License-Identifier: GPL-3.0-or-later
"""Préparation locale du catalogue officiel, sans exporter la clé privée."""
import base64
import hashlib
import json
import os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mises_a_jour import valider
from version import VERSION
ROOT = Path(__file__).resolve().parent


def preparer(dossier):
    dossier = Path(dossier)
    configuration = json.loads((ROOT / 'configuration_editeur.json').read_text(encoding='utf-8'))
    manifeste = json.loads((dossier / 'version-verifiee.json').read_text(encoding='utf-8-sig'))
    if manifeste['version'] != VERSION:
        raise ValueError('Installez la version correspondant au dossier de publication.')
    programme = dossier / f'Patenteasy-Windows-{VERSION}-Installation.exe'
    taille = programme.stat().st_size
    h = hashlib.sha256()
    with programme.open('rb') as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b''):
            h.update(bloc)
    if taille != manifeste['taille'] or h.hexdigest() != manifeste['sha256']:
        raise ValueError('L’installeur est incomplet ou a été modifié.')
    chemin = Path(os.environ['LOCALAPPDATA']) / 'ska_987' / 'signature-patenteasy' / 'cle-privee.pem'
    if not chemin.is_file():
        raise ValueError('La clé officielle est absente de cet ordinateur. Préparez la publication sur votre PC éditeur.')
    cle = serialization.load_pem_private_key(chemin.read_bytes(), password=None)
    if not isinstance(cle, Ed25519PrivateKey):
        raise ValueError('Clé Ed25519 officielle requise.')
    publique = base64.b64encode(cle.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode('ascii')
    if publique != configuration['cle_publique_mises_a_jour']:
        raise ValueError('Cette clé ne correspond pas aux applications officielles.')
    serveur = configuration['catalogue_mises_a_jour'].rsplit('/', 1)[0]
    versions = {
        'windows': {'version': VERSION, 'url': serveur + '/fichiers/' + programme.name,
                    'sha256': h.hexdigest(), 'taille': taille, 'format': 'exe',
                    'notes': 'Sélection lisible, défilement, conditions allégées, fiscalité sans blocage et dates JJ/MM/AA.'},
        'android': {'version': '0.3.7', 'url': serveur + '/fichiers/Patenteasy-Android-0.3.7.apk',
                    'sha256': '7d6899b90c63ed6eb83f95a20adb8a714b23f4a9be1b061d1bfebca52e9271ff',
                    'taille': 427542, 'format': 'apk', 'notes': 'Beta Android 0.3.7.'}
    }
    canonique = json.dumps(versions, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    catalogue = {'versions': versions, 'signature': base64.b64encode(cle.sign(canonique)).decode('ascii')}
    valider(catalogue, publique, 'windows')
    valider(catalogue, publique, 'android')
    cible = dossier / 'catalogue.json'
    temporaire = dossier / 'catalogue.tmp'
    temporaire.write_text(json.dumps(catalogue, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporaire.replace(cible)
    return cible


def lancer(dossier):
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication([])
    try:
        catalogue = preparer(dossier)
        QMessageBox.information(None, 'Patenteasy — Publication',
            f'Catalogue signé et vérifié :\n{catalogue}\n\nDans le bucket R2 patenteasy-releases :\n1. Envoyez l’installeur EXE.\n2. Envoyez catalogue.json en dernier.\n\nLa clé privée reste sur votre ordinateur.')
        return 0
    except Exception as erreur:
        QMessageBox.critical(None, 'Patenteasy — Publication', str(erreur))
        return 1
