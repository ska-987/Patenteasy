# SPDX-License-Identifier: GPL-3.0-or-later
"""Authentification locale et droits explicites."""
import hashlib
import hmac
import secrets
import sqlite3
from contextlib import closing
import time
from database import BaseDonnees
from coffre import Coffre, envelopper, desenvelopper, ecrire_json

class GestionComptes:
    def __init__(self, base=None):
        self.base = base or BaseDonnees()
        self.coffre = Coffre(self.base.chemin)
        self.session = None

    def initialiser(self):
        from sauvegarde_portable import reprendre
        reprendre(self.coffre)

    def restaurer_nouveau_pc(self, preparation, nouveau_mot_de_passe=None, code=None):
        if self.coffre.metadata.exists() or self.base.chemin.exists():
            raise ValueError('La récupération sur un nouveau PC nécessite un espace sans données existantes.')
        from sauvegarde_portable import verifier, installer
        if nouveau_mot_de_passe is not None:
            self.valider_mot_de_passe(nouveau_mot_de_passe)
            try:
                cle = desenvelopper(preparation['metadata']['recuperation'], code, 'recuperation')
                if not hmac.compare_digest(cle, preparation['cle']): raise ValueError()
            except Exception:
                raise ValueError('Code de récupération incorrect.') from None
        verifier(preparation, self.base.chemin.parent)
        installer(preparation, self.coffre)
        self.session = preparation['compte']
        self.coffre.activer(preparation['cle'], self.session)
        if nouveau_mot_de_passe is not None:
            self.recuperer(code, nouveau_mot_de_passe)
        self.tracer('Récupération sur nouveau PC')
        return self.session

    def premier_compte_requis(self):
        if self.coffre.metadata.exists(): return False
        return not self._anciens()

    def _anciens(self):
        if not self.base.chemin.exists(): return []
        try:
            with closing(sqlite3.connect(self.base.chemin.resolve().as_uri()+'?mode=ro', uri=True)) as c:
                c.row_factory=sqlite3.Row
                return [dict(x) for x in c.execute('SELECT * FROM comptes')]
        except sqlite3.DatabaseError: return []

    @staticmethod
    def valider_identifiant(identifiant):
        identifiant=identifiant.strip()
        if not 3<=len(identifiant)<=40 or not all(x.isascii() and (x.isalnum() or x in '._-') for x in identifiant):
            raise ValueError('Identifiant : 3 à 40 lettres, chiffres, points ou tirets.')
        return identifiant

    @staticmethod
    def valider_mot_de_passe(secret):
        if not 12<=len(secret)<=256: raise ValueError('Mot de passe : au moins 12 caractères, maximum 256.')

    def creer_premier_admin(self, identifiant, mot_de_passe):
        if not self.premier_compte_requis(): raise ValueError('Connectez-vous au compte existant.')
        identifiant=self.valider_identifiant(identifiant); self.valider_mot_de_passe(mot_de_passe)
        self.session=self.coffre.creer(identifiant,mot_de_passe)
        return self.session

    def authentifier(self, identifiant, mot_de_passe):
        identifiant=identifiant.strip()
        if not self.coffre.metadata.exists():
            for a in self._anciens():
                if a['identifiant'].casefold()!=identifiant.casefold() or a['role']!='admin' or not a['actif']:continue
                empreinte=hashlib.pbkdf2_hmac('sha256',mot_de_passe.encode(),a['sel'],a['iterations'])
                if hmac.compare_digest(empreinte,a['empreinte']):
                    self.session=self.coffre.creer(a['identifiant'],mot_de_passe)
                    return self.session
            return None
        m=self.coffre.lire()
        compte=next((c for c in m['comptes'] if c['identifiant'].casefold()==identifiant.casefold()),None)
        if compte is None:
            hashlib.scrypt(mot_de_passe.encode(),salt=bytes(16),n=32768,r=8,p=1,maxmem=64*1024*1024)
            return None
        if not compte['actif'] or compte.get('bloque_jusqua',0)>time.time():return None
        try:cle=desenvelopper(compte['enveloppe'],mot_de_passe,compte['identifiant'].casefold()+':'+compte['role'])
        except Exception:
            compte['echecs']=compte.get('echecs',0)+1
            if compte['echecs']>=5:compte['echecs']=0;compte['bloque_jusqua']=time.time()+60
            ecrire_json(self.coffre.metadata,m);return None
        compte['echecs']=0;compte['bloque_jusqua']=0;ecrire_json(self.coffre.metadata,m)
        self.session={k:compte[k] for k in ('id','identifiant','role')}
        self.coffre.cle=cle; self.coffre.reprendre_migration()
        self.coffre.activer(cle,self.session)
        return self.session

    def exiger_admin(self):
        if not self.session or self.session['role']!='admin':raise PermissionError('Action réservée à l’administrateur.')

    def lister(self):
        self.exiger_admin()
        return [{k:c[k] for k in ('id','identifiant','role','actif')} for c in self.coffre.lire()['comptes']]

    def creer_utilisateur(self, identifiant, secret):
        self.exiger_admin(); identifiant=self.valider_identifiant(identifiant);self.valider_mot_de_passe(secret)
        m=self.coffre.lire()
        if any(c['identifiant'].casefold()==identifiant.casefold() for c in m['comptes']):raise ValueError('Identifiant déjà utilisé.')
        m['comptes'].append({'id':secrets.token_hex(12),'identifiant':identifiant,'role':'utilisateur','actif':True,
            'enveloppe':envelopper(self.coffre.cle,secret,identifiant.casefold()+':utilisateur'),'preferences':{},'echecs':0,'bloque_jusqua':0})
        ecrire_json(self.coffre.metadata,m);self.tracer('Création utilisateur',identifiant)

    def basculer_actif(self, ident):
        self.exiger_admin();m=self.coffre.lire()
        c=next(x for x in m['comptes'] if x['id']==ident)
        if c['role']=='admin':raise ValueError('Le compte administrateur ne peut pas être désactivé.')
        c['actif']=not c['actif'];ecrire_json(self.coffre.metadata,m);self.tracer('État utilisateur',c['identifiant'])

    def changer_mot_de_passe(self, ancien, nouveau):
        self.valider_mot_de_passe(nouveau);m=self.coffre.lire()
        c=next(c for c in m['comptes'] if c['id']==self.session['id'])
        try:cle=desenvelopper(c['enveloppe'],ancien,c['identifiant'].casefold()+':'+c['role'])
        except Exception:raise ValueError('Mot de passe actuel incorrect.') from None
        c['enveloppe']=envelopper(cle,nouveau,c['identifiant'].casefold()+':'+c['role']);ecrire_json(self.coffre.metadata,m)
        self.tracer('Changement mot de passe')

    def recuperer(self, code, nouveau):
        self.valider_mot_de_passe(nouveau);m=self.coffre.lire()
        try:cle=desenvelopper(m['recuperation'],code.strip(),'recuperation')
        except Exception:raise ValueError('Code de récupération incorrect.') from None
        admin=next(c for c in m['comptes'] if c['role']=='admin')
        admin['enveloppe']=envelopper(cle,nouveau,admin['identifiant'].casefold()+':admin');admin['echecs']=0;admin['bloque_jusqua']=0
        nouveau_code=secrets.token_hex(24);m['recuperation']=envelopper(cle,nouveau_code,'recuperation')
        ecrire_json(self.coffre.metadata,m);self.coffre.code_recuperation=nouveau_code
        return admin['identifiant']

    def preferences(self):
        return next(c for c in self.coffre.lire()['comptes'] if c['id']==self.session['id']).get('preferences',{})

    def enregistrer_preferences(self,p):
        m=self.coffre.lire();c=next(c for c in m['comptes'] if c['id']==self.session['id']);c['preferences']=p;ecrire_json(self.coffre.metadata,m)

    def tracer(self,action,detail=''):
        if self.coffre.cle is None:return
        c=self.coffre.ouvrir()
        try:
            c.execute('CREATE TABLE IF NOT EXISTS audit_local (date REAL, utilisateur TEXT, action TEXT, detail TEXT)')
            c.execute('INSERT INTO audit_local VALUES (?,?,?,?)',(time.time(),self.session['identifiant'],action,detail));c.commit()
        finally:c.close()
