# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
"""Versions proposées par un catalogue HTTPS signé par l'éditeur."""
import base64
import hashlib
import json
import re
from pathlib import Path
import ssl
import certifi
from urllib.request import Request, urlopen, build_opener, HTTPSHandler, HTTPRedirectHandler
from urllib.parse import urlsplit
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from version import VERSION
ROOT=Path(__file__).resolve().parent
DERNIERE_VERIFICATION = {}

class RedirectionsHTTPS(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        destination=urlsplit(newurl)
        if destination.scheme != 'https' or destination.username or destination.password:
            raise ValueError('Redirection de mise à jour non sécurisée.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def ouvrir_https(url, timeout):
    destination=urlsplit(url)
    if destination.scheme!='https' or not destination.hostname or destination.username or destination.password:
        raise ValueError('Lien HTTPS requis.')
    contexte = ssl.create_default_context(cafile=certifi.where())
    requete = Request(url, headers={"User-Agent": "Patenteasy/" + VERSION, "Accept": "*/*"})
    ouvreur=build_opener(HTTPSHandler(context=contexte),RedirectionsHTTPS())
    return ouvreur.open(requete,timeout=timeout)

def version(v):
    if not isinstance(v,str) or not re.fullmatch(r'\d+\.\d+\.\d+',v): raise ValueError('Version invalide.')
    return tuple(map(int,v.split('.')))


def valider(enveloppe,cle,plateforme):
    if not isinstance(enveloppe,dict): raise ValueError('Catalogue invalide.')
    donnees=enveloppe['versions']
    contenu=json.dumps(donnees,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    Ed25519PublicKey.from_public_bytes(base64.b64decode(cle,validate=True)).verify(base64.b64decode(enveloppe['signature'],validate=True),contenu)
    r=donnees[plateforme]
    url=urlsplit(r['url'])
    if url.scheme!='https' or not url.hostname or url.username or url.password or not re.fullmatch('[a-fA-F0-9]{64}',r['sha256']): raise ValueError('Lien ou empreinte invalide.')
    if not isinstance(r.get('taille'),int) or not 0<r['taille']<=500_000_000:raise ValueError('Taille invalide.')
    format=r.get('format','apk' if plateforme=='android' else 'exe')
    if format not in (('apk',) if plateforme=='android' else ('exe','zip')):raise ValueError('Format de mise à jour invalide.')
    return {**r,'format':format,'plateforme':plateforme,'nouvelle':version(r['version'])>version(VERSION)}


def verifier(plateforme='windows'):
    config=json.loads((ROOT/'configuration_editeur.json').read_text(encoding='utf-8'))
    url=config.get('catalogue_mises_a_jour','');cle=config.get('cle_publique_mises_a_jour','')
    if not url or not cle:return {'configure':False,'version':VERSION}
    if urlsplit(url).scheme!='https':raise ValueError('Le catalogue exige HTTPS.')
    with ouvrir_https(url, timeout=10) as reponse:
        contenu=reponse.read(1_000_001)
        if len(contenu)>1_000_000:raise ValueError('Catalogue trop volumineux.')
    return {'configure':True,**valider(json.loads(contenu),cle,plateforme)}


def telecharger(r,dossier):
    dossier=Path(dossier);dossier.mkdir(parents=True,exist_ok=True)
    fichier=dossier/('Patenteasy-'+r['version']+('-android.apk' if r.get('plateforme')=='android' else '-installation.'+r.get('format','exe')))
    temporaire=fichier.with_suffix('.part');h=hashlib.sha256();taille=0
    try:
        with ouvrir_https(r['url'], timeout=30) as source, temporaire.open('wb') as cible:
            while True:
                morceau=source.read(65536)
                if not morceau:break
                taille+=len(morceau)
                if taille>r['taille']:raise ValueError('Taille de mise à jour incorrecte.')
                h.update(morceau);cible.write(morceau)
        if taille!=r['taille'] or h.hexdigest().lower()!=r['sha256'].lower():raise ValueError('Intégrité de la mise à jour incorrecte.')
        temporaire.replace(fichier);return fichier
    finally:temporaire.unlink(missing_ok=True)


def installer(app,templates):
    from fastapi import Form
    from threading import Thread
    def verification_discrete():
        global DERNIERE_VERIFICATION
        try:DERNIERE_VERIFICATION=verifier()
        except Exception:DERNIERE_VERIFICATION={}
    @app.on_event('startup')
    def verifier_au_demarrage():
        Thread(target=verification_discrete,daemon=True).start()
    templates.env.globals['mise_a_jour_proposee']=lambda:DERNIERE_VERIFICATION.get('nouvelle',False)
    from fastapi import Request
    from fastapi.responses import FileResponse
    @app.get('/mises-a-jour')
    def page(request:Request):
        from editeur import editeur
        configuration = editeur.lire()
        try:etat=verifier();erreur=''
        except Exception:etat={'configure':True};erreur='Impossible de vérifier une version authentique. Aucun programme téléchargé.'
        return templates.TemplateResponse(request=request,name='mises_a_jour.html',context={'etat':etat,'erreur':erreur,'version':VERSION,'publication':configuration})
    @app.post('/mises-a-jour/liens')
    def liens(drive: str = Form(''), paypal: str = Form('')):
        from editeur import editeur
        from fastapi.responses import RedirectResponse
        configuration = editeur.enregistrer(drive, paypal)
        templates.env.globals['paypal_url'] = configuration['paypal_url']
        return RedirectResponse('/mises-a-jour', 303)
    @app.post('/mises-a-jour/telecharger')
    def recuperer():
        import database as db
        import sqlite3
        from datetime import datetime
        r=verifier()
        if not r.get('nouvelle'):raise ValueError('Aucune nouvelle version vérifiée disponible.')
        # Sauvegarde préalable ; l'installateur n'est jamais exécuté par le serveur web.
        dossier=db.BASE_DIR/'sauvegardes';dossier.mkdir(exist_ok=True)
        with sqlite3.connect(db.DB_PATH) as source,sqlite3.connect(dossier/('avant-mise-a-jour-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.db')) as cible:source.backup(cible)
        p=telecharger(r,db.DATA_DIR/'mises-a-jour')
        return FileResponse(p,filename=p.name,media_type='application/octet-stream')
