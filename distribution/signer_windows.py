# SPDX-License-Identifier: GPL-3.0-or-later
"""Catalogue Windows : conserve l'entrée Android authentifiée déjà publiée."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mises_a_jour import ouvrir_https, valider, version
from version import VERSION
ROOT=Path(__file__).resolve().parents[1]

def preparer(dossier):
    dossier=Path(dossier)
    config=json.loads((ROOT/'configuration_editeur.json').read_text(encoding='utf-8'))
    manifest=json.loads((dossier/'version-verifiee.json').read_text(encoding='utf-8-sig'))
    programme=dossier/f'Patenteasy-Windows-{VERSION}-Installation.exe'
    empreinte=hashlib.sha256(programme.read_bytes()).hexdigest()
    if manifest['version']!=VERSION or manifest['taille']!=programme.stat().st_size or manifest['sha256']!=empreinte:
        raise ValueError('Installateur différent de la construction vérifiée.')
    with ouvrir_https(config['catalogue_mises_a_jour'],timeout=30) as flux:
        contenu=flux.read(1_000_001)
    if len(contenu)>1_000_000:raise ValueError('Catalogue trop volumineux.')
    ancien=json.loads(contenu)
    precedent=valider(ancien,config['cle_publique_mises_a_jour'],'windows')
    valider(ancien,config['cle_publique_mises_a_jour'],'android')
    if version(precedent['version'])>version(VERSION):raise ValueError('Une version Windows plus récente est déjà publiée.')
    if precedent['version']==VERSION and (precedent['sha256']!=empreinte or precedent['taille']!=programme.stat().st_size):
        raise ValueError('Cette version est déjà publiée avec un autre contenu.')
    cle_path=Path(os.environ.get('PATENTEASY_CATALOGUE_KEY_FILE') or str(Path(os.environ['LOCALAPPDATA'])/'ska_987/signature-patenteasy/cle-privee.pem'))
    cle=serialization.load_pem_private_key(cle_path.read_bytes(),password=None)
    if not isinstance(cle,Ed25519PrivateKey):raise ValueError('Clé Ed25519 originale requise.')
    publique=base64.b64encode(cle.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
    if publique!=config['cle_publique_mises_a_jour']:raise ValueError('La clé ne correspond pas aux applications installées.')
    donnees=ancien['versions'].copy()
    donnees['windows']={'version':VERSION,'url':config['catalogue_mises_a_jour'].rsplit('/',1)[0]+'/fichiers/'+programme.name,'format':'exe','taille':programme.stat().st_size,'sha256':empreinte,'notes':'Catalogue ajusté, suivi des avoirs et factures directes sans devis.'}
    canonique=json.dumps(donnees,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    enveloppe={'versions':donnees,'signature':base64.b64encode(cle.sign(canonique)).decode()}
    valider(enveloppe,publique,'windows');valider(enveloppe,publique,'android')
    temporaire=dossier/'catalogue.tmp';temporaire.write_text(json.dumps(enveloppe,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporaire.replace(dossier/'catalogue.json')
    (dossier/'SHA256SUMS.txt').write_text(empreinte+'  '+programme.name+'\n',encoding='ascii')
    print('Catalogue signé : Windows '+VERSION+' ; Android conservé en '+donnees['android']['version']+'.')
    print('Envoyer EXE et sources dans R2, puis catalogue.json EN DERNIER. Aucun envoi effectué par ce script.')
    return enveloppe

if __name__=='__main__':
    try:preparer(Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd())
    except Exception as e:
        print('Signature interrompue :',e);raise SystemExit(1)
