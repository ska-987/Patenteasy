# SPDX-License-Identifier: GPL-3.0-or-later
"""Copie initiale seulement, sans ouvrir ni modifier la base de production."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile


def copier(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source==destination or source in destination.parents or destination in source.parents:
        raise ValueError('Les dossiers de production et de test doivent être distincts.')
    if destination.exists():
        raise ValueError('La copie de test existe déjà : elle ne sera pas remplacée.')
    if not (source/'patenteeasy.db').is_file():
        raise ValueError('Base habituelle introuvable.')
    for nom in ('patenteeasy.db-wal','patenteeasy.db-journal','restauration-acces.json','restauration.db','patenteeasy.db.chiffrement'):
        if (source/nom).exists() and (source/nom).stat().st_size:
            raise ValueError('Terminez la restauration ou ouvrez puis fermez Patenteasy habituel avant la copie.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='copie-',dir=destination.parent) as tmp:
        staging=Path(tmp)/'data';staging.mkdir()
        for nom in ('patenteeasy.db','acces.json'):
            fichier=source/nom
            if not fichier.exists():continue
            if fichier.is_symlink(): raise ValueError('Les liens de fichiers ne sont pas acceptés pour la copie.')
            avant=hashlib.sha256(fichier.read_bytes()).digest()
            shutil.copyfile(fichier,staging/nom)
            if avant!=hashlib.sha256((staging/nom).read_bytes()).digest() or avant!=hashlib.sha256(fichier.read_bytes()).digest():
                raise ValueError('La base a changé pendant la copie. Fermez Patenteasy habituel et recommencez.')
        metadata=staging/'acces.json'
        if metadata.exists():
            m=json.loads(metadata.read_text(encoding='utf-8'))
            m.setdefault('sauvegardes',{})['dossier']=str(destination.parent/'sauvegardes')
            metadata.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
        os.rename(staging,destination)


def premier_lancement(destination, mutex):
    from PySide6.QtWidgets import QApplication,QMessageBox
    import edition
    destination=Path(destination)/'data'
    if destination.exists(): return True
    source=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'PatenteasyLocal'/'data'
    app=QApplication.instance() or QApplication([])
    if not (source/'patenteeasy.db').exists(): return True
    choix=QMessageBox()
    choix.setWindowTitle('Patenteasy TEST · Première utilisation')
    choix.setText('Créer une copie de votre base habituelle pour les tests ?')
    choix.setInformativeText('Fermez Patenteasy habituel avant de copier. Vous garderez les mêmes identifiants et mots de passe. La base habituelle reste inchangée. Cette copie ne sera faite qu’une fois.')
    oui=choix.addButton('Copier ma base pour les tests',QMessageBox.ButtonRole.AcceptRole)
    vide=choix.addButton('Démarrer un test vide',QMessageBox.ButtonRole.ActionRole)
    choix.addButton(QMessageBox.StandardButton.Cancel)
    choix.exec()
    if choix.clickedButton()==vide:return True
    if choix.clickedButton()!=oui:return False
    verrou=mutex(source.parent)
    try:
        if verrou.deja_ouverte:raise ValueError('Fermez Patenteasy habituel puis relancez Patenteasy TEST pour copier sa base.')
        copier(source,destination)
    except Exception as erreur:
        QMessageBox.warning(None,'Copie de test interrompue',str(erreur));return False
    finally:verrou.fermer()
    return True
