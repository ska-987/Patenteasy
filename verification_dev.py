# SPDX-License-Identifier: GPL-3.0-or-later
"""Contrôle de l'édition compilée sur une production fictive chiffrée."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import traceback


def verifier(rapport):
    resultat={'ok':False}
    try:
        import edition
        assert edition.DEVELOPPEMENT, 'Marqueur de test absent du programme compilé'
        with tempfile.TemporaryDirectory(prefix='patenteasy-isolation-',ignore_cleanup_errors=True) as tmp:
            os.environ['LOCALAPPDATA']=tmp
            test=edition.repertoire();prod=Path(tmp)/'PatenteasyLocal'
            assert test!=prod and test.name=='PatenteasyLocal-DEV'
            os.environ['PATENTEASY_DATA_DIR']=str(test)
            from coffre import Coffre
            from comptes import GestionComptes
            from database import BaseDonnees
            from gestion import GestionDocuments
            from donnees_test import copier
            data=prod/'data';data.mkdir(parents=True)
            original=Coffre(data/'patenteeasy.db');original.creer('test','MotDePasse-Test-DEV!')
            b=BaseDonnees(original.chemin);GestionDocuments(b).migrer()
            b.modifier_entreprise('Production fictive','','','','','','')
            original.verrouiller()
            avant={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data.iterdir()}
            copier(data,test/'data')
            manager=GestionComptes(BaseDonnees(test/'data'/'patenteeasy.db'))
            assert manager.authentifier('test','MotDePasse-Test-DEV!')
            manager.base.modifier_entreprise('Copie modifiée pour le test','','','','','','')
            assert manager.base.obtenir_entreprise()['nom']=='Copie modifiée pour le test'
            manager.coffre.verrouiller()
            assert avant=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data.iterdir()}
            assert Path(json.loads((test/'data'/'acces.json').read_text())['sauvegardes']['dossier']).resolve()==(test/'sauvegardes').resolve()
            try:copier(data,test/'data')
            except ValueError:pass
            else:raise AssertionError('La copie de test existante a été remplacée')
            resultat={'ok':True,'edition_test':True,'copie_chiffree':True,'identifiants_conserves':True,
                      'modification_copie_seulement':True,'production_inchangee':True,
                      'sauvegardes_separees':True,'copie_existante_preservee':True}
    except Exception:
        resultat['erreur']=traceback.format_exc()
    Path(rapport).write_text(json.dumps(resultat,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if resultat['ok'] else 1
