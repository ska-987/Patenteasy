# SPDX-License-Identifier: GPL-3.0-or-later
"""Sauvegardes chiffrées, rétention et restauration administrateur."""
import io
import json
import os
from pathlib import Path
import secrets
import tempfile
import zipfile
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from coffre import ecrire_json

MAGIC=b'PATENTEASY-BACKUP-1\n'

class GestionSauvegardes:
    def __init__(self, comptes):self.comptes=comptes;self.coffre=comptes.coffre

    def configuration(self):return self.coffre.lire()['sauvegardes']

    def configurer(self,dossier,jours=7,semaines=4):
        self.comptes.exiger_admin()
        if not 1<=jours<=90 or not 0<=semaines<=52:raise ValueError('Rétention invalide.')
        p=Path(dossier);p.mkdir(parents=True,exist_ok=True)
        if p.resolve()==self.coffre.chemin.parent.resolve():raise ValueError('Choisissez un dossier de sauvegardes distinct.')
        m=self.coffre.lire();m['sauvegardes'].update(dossier=str(p),jours=jours,semaines=semaines);ecrire_json(self.coffre.metadata,m)

    def creer(self,raison='manuelle'):
        try:return self._creer(raison)
        except Exception:
            m=self.coffre.lire();m['sauvegardes']['erreur']='Sauvegarde impossible. Vérifiez le dossier choisi.';ecrire_json(self.coffre.metadata,m)
            raise

    def _creer(self,raison):
        configuration=self.configuration()
        if not configuration['dossier']:raise ValueError('L’administrateur doit choisir le dossier de sauvegardes.')
        dossier=Path(configuration['dossier'])
        if not dossier.is_dir():raise ValueError('Le dossier de sauvegardes est inaccessible.')
        nom='Patenteasy-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-'+raison+'.pebackup'
        destination=dossier/nom
        fd,tmp=tempfile.mkstemp(suffix='.db',dir=self.coffre.chemin.parent);os.close(fd);Path(tmp).unlink()
        source=self.coffre.ouvrir()
        try:
            source.execute('ATTACH DATABASE ? AS sauvegarde KEY "x\''+self.coffre.cle.hex()+'\'"',(tmp,))
            source.execute("SELECT sqlcipher_export('sauvegarde')")
            source.execute('DETACH DATABASE sauvegarde')
            c=self.coffre.ouvrir(tmp)
            try:
                if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA cipher_integrity_check').fetchall():raise ValueError('Sauvegarde invalide.')
            finally:c.close()
            flux=io.BytesIO()
            with zipfile.ZipFile(flux,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr('base.db',Path(tmp).read_bytes())
                z.writestr('acces.json',self.coffre.metadata.read_bytes())
            from sauvegarde_portable import emballer
            contenu=emballer(flux.getvalue(),self.coffre.cle,self.coffre.lire())
            temporaire=destination.with_suffix('.part')
            with temporaire.open('wb') as f:f.write(contenu);f.flush();os.fsync(f.fileno())
            os.replace(temporaire,destination)
            m=self.coffre.lire();m['sauvegardes'].update(derniere=datetime.now().isoformat(),dernier_jour=datetime.now().date().isoformat(),erreur='',format=2);ecrire_json(self.coffre.metadata,m)
            self.comptes.tracer('Sauvegarde',raison)
            self._retenir(configuration)
            return destination
        finally:
            source.close();Path(tmp).unlink(missing_ok=True)

    def _retenir(self,configuration):
        # Seules les sauvegardes automatiques générées ici sont purgées.
        fichiers=sorted(Path(configuration['dossier']).glob('Patenteasy-*-auto.pebackup'),reverse=True)
        jours=set();semaines=set();conserver=set()
        for p in fichiers:
            try:date=datetime.strptime(p.name.split('-')[1],'%Y%m%d')
            except ValueError:continue
            jour=date.date();semaine=date.isocalendar()[:2]
            if jour not in jours and len(jours)<configuration['jours']:jours.add(jour);conserver.add(p)
            if semaine not in semaines and len(semaines)<configuration['semaines']:semaines.add(semaine);conserver.add(p)
        for p in fichiers:
            if p not in conserver:p.unlink()

    def automatique(self):
        c=self.configuration()
        if not c['dossier']:return None
        if c.get('dernier_jour')==datetime.now().date().isoformat() and c.get('format')==2:return None
        return self.creer('auto')

    def restaurer(self,fichier):
        self.comptes.exiger_admin()
        from sauvegarde_portable import preparer, verifier, installer
        preparation = preparer(fichier, '', cle_existante=self.coffre.cle)
        verifier(preparation, self.coffre.chemin.parent)
        self.creer('avant-restauration')
        installer(preparation, self.coffre, self.configuration())
