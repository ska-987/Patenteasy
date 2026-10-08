# SPDX-License-Identifier: GPL-3.0-or-later
"""Signature originale, puis publication R2 : fichiers vérifiés avant catalogue."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import publication_release as publication
from version import VERSION, VERSION_ANDROID


def signer_android(dossier):
    dossier=Path(dossier)
    m=json.loads((dossier/'android-verifie.json').read_text())
    candidat=dossier/f'Patenteasy-Android-{VERSION_ANDROID}-A-SIGNER.apk'
    jar=dossier/'apksigner.jar'
    if (m['version']!=VERSION_ANDROID or m['taille']!=candidat.stat().st_size
            or m['sha256']!=hashlib.sha256(candidat.read_bytes()).hexdigest()
            or m['apksigner_sha256']!=hashlib.sha256(jar.read_bytes()).hexdigest()):
        raise ValueError('APK préparée ou outil de signature modifié.')
    exe=json.loads((dossier/'version-verifiee.json').read_text(encoding='utf-8-sig'))
    if not m.get('source') or exe.get('source')!=m['source']:
        raise ValueError('Les deux constructions doivent correspondre au même commit.')
    sortie=dossier/f'Patenteasy-Android-{VERSION_ANDROID}.apk'
    try:
        subprocess.run([os.environ.get('PATENTEASY_JAVA','java'),'-jar',str(jar),'sign',
                        '--ks',os.environ['PATENTEASY_KEYSTORE'],
                        '--ks-key-alias',os.environ['PATENTEASY_KEY_ALIAS'],
                        '--ks-pass','env:PATENTEASY_KEY_PASSWORD',
                        '--key-pass','env:PATENTEASY_KEY_PASSWORD',
                        '--out',str(sortie),str(candidat)],check=True)
        publication.verifier_apk(dossier,exe)
    except Exception:
        sortie.unlink(missing_ok=True)
        raise
    return sortie


def lire_public(url,attendu):
    requete=urllib.request.Request(url,headers={'User-Agent':f'Patenteasy-Publication/{VERSION}',
                                              'Cache-Control':'no-cache'})
    h=hashlib.sha256();taille=0
    with urllib.request.urlopen(requete,timeout=60) as flux:
        if flux.geturl().split('/',3)[:3]!=url.split('/',3)[:3]:
            raise ValueError('Le téléchargement sort du serveur officiel.')
        while bloc:=flux.read(1024*1024):
            taille+=len(bloc)
            if taille>attendu['taille']:raise ValueError('Taille du téléchargement incorrecte.')
            h.update(bloc)
    if taille!=attendu['taille'] or h.hexdigest()!=attendu['sha256']:
        raise ValueError('Téléchargement public incorrect. Le catalogue ne sera pas publié.')


def empreinte_objet(objet):
    try:
        h=hashlib.sha256();taille=0
        while bloc:=objet['Body'].read(1024*1024):h.update(bloc);taille+=len(bloc)
        return taille,h.hexdigest()
    finally:objet['Body'].close()


def publier(dossier,client=None,lecteur=lire_public):
    dossier=Path(dossier)
    catalogue=publication.preparer(dossier)
    donnees=json.loads(catalogue.read_text())
    if client is None:
        import boto3
        compte=os.environ['CLOUDFLARE_ACCOUNT_ID']
        if not re.fullmatch('[0-9a-f]{32}',compte):raise ValueError('Identifiant Cloudflare incorrect.')
        client=boto3.client('s3',endpoint_url=f'https://{compte}.r2.cloudflarestorage.com',
                            aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
                            aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],region_name='auto')
    existants=set()
    for version in donnees['versions'].values():
        nom=version['url'].rsplit('/',1)[1]
        try:
            objet=client.get_object(Bucket='patenteasy-releases',Key=nom)
        except Exception as e:
            code=getattr(e,'response',{}).get('Error',{}).get('Code')
            if code not in ('NoSuchKey','404','NotFound'):raise
        else:
            if empreinte_objet(objet)!=(version['taille'],version['sha256']):
                raise ValueError('Cette version existe déjà avec un autre contenu. Incrémentez la version avant de publier.')
            existants.add(nom)
    for plateforme,version in donnees['versions'].items():
        nom=version['url'].rsplit('/',1)[1]
        fichier=dossier/nom
        if nom not in existants:
            with fichier.open('rb') as flux:
                client.put_object(Bucket='patenteasy-releases',Key=nom,Body=flux,
                                  ContentType='application/vnd.android.package-archive' if plateforme=='android' else 'application/octet-stream',
                                  CacheControl='public, max-age=31536000, immutable')
        objet=client.get_object(Bucket='patenteasy-releases',Key=nom)
        if empreinte_objet(objet)!=(version['taille'],version['sha256']):
            raise ValueError('Objet R2 incomplet. Ancien catalogue conservé.')
        lecteur(version['url'],version)
    # Dernière écriture seulement après vérification des DEUX fichiers distribués.
    client.put_object(Bucket='patenteasy-releases',Key='catalogue.json',Body=catalogue.read_bytes(),
                      ContentType='application/json; charset=utf-8',CacheControl='no-store')
    distant=client.get_object(Bucket='patenteasy-releases',Key='catalogue.json')
    try:raw=distant['Body'].read(1000000)
    finally:distant['Body'].close()
    if json.loads(raw)!=donnees:raise ValueError('Catalogue envoyé non vérifié.')
    configuration=json.loads((publication.ROOT/'configuration_editeur.json').read_text())
    with urllib.request.urlopen(urllib.request.Request(configuration['catalogue_mises_a_jour'],headers={'Cache-Control':'no-cache'}),timeout=60) as flux:
        public=json.loads(flux.read(1000000))
    if public!=donnees:raise ValueError('Catalogue R2 envoyé, mais réponse publique différente. Vérifiez le cache Cloudflare avant d’annoncer la publication.')
    print(f'Windows et Android {VERSION} publiés et vérifiés sur Cloudflare.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('dossier',type=Path)
    parser.add_argument('--signer-android',action='store_true');parser.add_argument('--preparer-seulement',action='store_true')
    options=parser.parse_args()
    if options.signer_android:signer_android(options.dossier)
    if options.preparer_seulement:print(publication.preparer(options.dossier))
    else:publier(options.dossier)
