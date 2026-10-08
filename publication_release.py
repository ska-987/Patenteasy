# SPDX-License-Identifier: GPL-3.0-or-later
"""Préparation locale du catalogue officiel, sans exporter la clé privée."""
import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mises_a_jour import valider
from version import VERSION, VERSION_ANDROID
ROOT = Path(__file__).resolve().parent
CERTIFICAT_ANDROID = 'cfc8d95ee97be9a7a80eca28de72178d7e9cd01236dc8187c69ba1c60ff7c119'


def verifier_apk(dossier, manifeste_windows):
    dossier = Path(dossier)
    manifeste = json.loads((dossier / 'android-verifie.json').read_text(encoding='utf-8'))
    if (manifeste['version'] != VERSION_ANDROID or manifeste['versionCode'] != 10
            or manifeste['package'] != 'pf.ska987.patenteasy.local'
            or not manifeste.get('source') or manifeste['source'] != manifeste_windows.get('source')):
        raise ValueError('Les deux applications doivent provenir du même commit vérifié.')
    programme = dossier / f'Patenteasy-Android-{VERSION_ANDROID}.apk'
    jar = dossier / 'apksigner.jar'
    if hashlib.sha256(jar.read_bytes()).hexdigest() != manifeste['apksigner_sha256']:
        raise ValueError('L’outil de signature a été modifié.')
    resultat = subprocess.check_output([os.environ.get('PATENTEASY_JAVA', 'java'), '-jar', str(jar),
                                      'verify', '--verbose', '--print-certs', str(programme)], text=True)
    certificats = [ligne.split(':', 1)[1].strip().lower() for ligne in resultat.splitlines()
                  if 'certificate SHA-256 digest:' in ligne]
    if certificats != [CERTIFICAT_ANDROID]:
        raise ValueError('La signature Android ne correspond pas à vos applications installées.')
    taille = programme.stat().st_size
    empreinte = hashlib.sha256(programme.read_bytes()).hexdigest()
    return programme, taille, empreinte


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
    apk, taille_apk, empreinte_apk = verifier_apk(dossier, manifeste)
    chemin = (Path(os.environ['PATENTEASY_CATALOGUE_KEY_FILE']) if os.environ.get('PATENTEASY_CATALOGUE_KEY_FILE')
              else Path(os.environ['LOCALAPPDATA']) / 'ska_987' / 'signature-patenteasy' / 'cle-privee.pem')
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
                    'notes': 'Bêta 0.4.1 : accès factures et PDF, conditions facultatives rétroactives, nouveau client depuis le devis et profil général.'},
        'android': {'version': VERSION_ANDROID, 'url': serveur + '/fichiers/' + apk.name,
                    'sha256': empreinte_apk, 'taille': taille_apk, 'format': 'apk',
                    'notes': 'Bêta 0.4.1 : conditions enregistrées dans Réglages, nouveau client depuis le devis, profil général et dossier PDF mémorisé.'}
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
            f'Catalogue signé et vérifié :\n{catalogue}\n\nLes deux versions sont prêtes. Lancez Publier-0.4.1.cmd pour envoyer les applications et vérifier les téléchargements avant de publier le catalogue.\n\nLa clé privée reste sur votre ordinateur.')
        return 0
    except Exception as erreur:
        QMessageBox.critical(None, 'Patenteasy — Publication', str(erreur))
        return 1
