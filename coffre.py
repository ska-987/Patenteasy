# SPDX-License-Identifier: GPL-3.0-or-later
"""SQLCipher et enveloppes de clés : aucun secret développeur."""
import base64
import json
import os
from pathlib import Path
import secrets
import sqlite3 as sqlite_clair
import hashlib
from sqlcipher3 import dbapi2 as sqlcipher
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ACTIF = None

def b64(b): return base64.b64encode(b).decode('ascii')
def deb64(s): return base64.b64decode(s, validate=True)

def ecrire_json(path, valeur):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(valeur, f, ensure_ascii=False, indent=2)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def envelopper(cle, secret, contexte):
    sel, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    derivee = hashlib.scrypt(secret.encode('utf-8'), salt=sel, n=32768, r=8, p=1, maxmem=64*1024*1024, dklen=32)
    return {'sel':b64(sel),'nonce':b64(nonce),'contenu':b64(AESGCM(derivee).encrypt(nonce, cle, contexte.encode()))}

def desenvelopper(enveloppe, secret, contexte):
    derivee = hashlib.scrypt(secret.encode('utf-8'), salt=deb64(enveloppe['sel']), n=32768, r=8, p=1, maxmem=64*1024*1024, dklen=32)
    return AESGCM(derivee).decrypt(deb64(enveloppe['nonce']), deb64(enveloppe['contenu']), contexte.encode())

class Coffre:
    def __init__(self, chemin):
        self.chemin = Path(chemin)
        self.metadata = self.chemin.parent / 'acces.json'
        self.cle = None
        self.compte = None
        self.code_recuperation = None

    def lire(self):
        reprise=self.chemin.parent/'restauration-acces.json'
        if reprise.exists() and not (self.chemin.parent/'restauration.db').exists():
            os.replace(reprise,self.metadata)
        return json.loads(self.metadata.read_text(encoding='utf-8'))

    def ouvrir(self, chemin=None):
        if self.cle is None: raise PermissionError('Connectez-vous pour ouvrir les données.')
        c = sqlcipher.connect(str(chemin or self.chemin), timeout=15)
        try:
            c.execute('PRAGMA key = "x\'' + self.cle.hex() + '\'"')
            if not c.execute('PRAGMA cipher_version').fetchone():
                raise RuntimeError('SQLCipher est indisponible.')
            c.execute('PRAGMA foreign_keys = ON')
            c.execute('PRAGMA temp_store = MEMORY')
            c.execute('PRAGMA secure_delete = ON')
            c.execute('SELECT count(*) FROM sqlite_master').fetchone()
            c.row_factory = sqlcipher.Row
            return c
        except Exception:
            c.close(); raise

    def activer(self, cle, compte):
        global ACTIF
        self.cle, self.compte = cle, compte
        ACTIF = self
        c = self.ouvrir(); c.close()

    def creer(self, identifiant, mot_de_passe):
        if self.metadata.exists(): raise ValueError('Le coffre existe déjà.')
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        cle = secrets.token_bytes(32)
        self.cle = cle
        recovery = secrets.token_hex(24)
        compte = {'id':secrets.token_hex(12), 'identifiant':identifiant, 'role':'admin', 'actif':True,
                  'enveloppe':envelopper(cle, mot_de_passe, identifiant.casefold()+':admin'), 'echecs':0,'bloque_jusqua':0,'preferences':{}}
        metadata = {'format':1, 'comptes':[compte], 'recuperation':envelopper(cle, recovery, 'recuperation'),
                    'sauvegardes':{'dossier':'','jours':7,'semaines':4}, 'journal':[]}
        # Une migration travaille vers un nouveau fichier chiffré.
        temp = self.chemin.with_name(self.chemin.name + '.chiffrement')
        try:
            if self.chemin.exists():
                source = sqlcipher.connect(str(self.chemin))
                try:
                    source.execute('ATTACH DATABASE ? AS protege KEY "x\'' + cle.hex() + '\'"', (str(temp),))
                    source.execute("SELECT sqlcipher_export('protege')")
                    source.execute('DETACH DATABASE protege')
                finally: source.close()
            else:
                c = self.ouvrir(temp)
                c.execute('CREATE TABLE coffre_version (version INTEGER)'); c.execute('INSERT INTO coffre_version VALUES (1)'); c.commit(); c.close()
            c = self.ouvrir(temp)
            try:
                if c.execute('PRAGMA integrity_check').fetchall()[0][0] != 'ok': raise RuntimeError('Migration invalide.')
                if c.execute('PRAGMA cipher_integrity_check').fetchall(): raise RuntimeError('Chiffrement invalide.')
            finally: c.close()
            # Métadonnées d'abord : reprise possible si le remplacement échoue.
            ecrire_json(self.metadata, metadata)
            os.replace(temp, self.chemin)
            self.code_recuperation = recovery
            self.activer(cle, {k:compte[k] for k in ('id','identifiant','role')})
            return self.compte
        except Exception:
            self.cle = None
            raise

    def reprendre_migration(self):
        temp = self.chemin.with_name(self.chemin.name + '.chiffrement')
        if temp.exists():
            c=self.ouvrir(temp)
            try:
                if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Migration incomplète.')
            finally:c.close()
            os.replace(temp,self.chemin)

    def verrouiller(self):
        global ACTIF
        self.cle = None; self.compte = None
        if ACTIF is self: ACTIF = None

# Interface DB-API centralisée pour le code métier existant.
class AccesSQLite:
    Row = sqlcipher.Row
    def __getattr__(self, nom): return getattr(sqlcipher, nom)
    def connect(self, chemin, *args, **kwargs):
        if ACTIF is not None and Path(chemin).resolve() == ACTIF.chemin.resolve():
            return ACTIF.ouvrir()
        # Base indépendante : tests/ancienne migration uniquement.
        return sqlcipher.connect(str(chemin), *args, **kwargs)

sqlite3 = AccesSQLite()
