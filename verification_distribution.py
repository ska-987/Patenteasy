# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
"""Vérifie le programme distribué dans un dossier de données isolé."""
import json
import os
from pathlib import Path
import tempfile
import traceback


def verifier(rapport):
    resultat = {'ok': False}
    try:
        with tempfile.TemporaryDirectory(prefix='patenteasy-verification-') as dossier:
            os.environ['PATENTEASY_DATA_DIR'] = dossier
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QCoreApplication, QEvent
            from coffre import Coffre
            import coffre
            import database as db
            import gestion as g
            from pdf_documents import generer
            from qt_app import FiscalPage, SettingsPage, QuoteEditorDialog
            from version import VERSION
            app = QApplication.instance() or QApplication([])
            protection = Coffre(db.DB_PATH)
            protection.creer('verification', 'VerificationLocale-039!')
            g.migrer()
            db.modifier_entreprise('Atelier test', '', '', '', 'Moorea', 'TEST', '')
            client = db.ajouter_client('Client test')
            jour = g.aujourd_hui().isoformat()
            devis = g.creer_devis(client, jour, 'Vérification')
            db.ajouter_ligne_devis(devis, 'Prestation', 'heure', '1', '1000', '16')
            g.confirmer_fiscalite(int(jour[:4]), 'reel', ca='12000000')
            contenu = g.calculer(devis)
            assert contenu['tva'] == 16000
            assert generer(contenu).startswith(b'%PDF')
            g.emettre_devis(devis)
            assert db.obtenir_devis(devis)['statut'] == 'envoye'
            autre = g.dupliquer_devis(devis)
            ecrans = [FiscalPage(), SettingsPage(), QuoteEditorDialog(autre)]
            for ecran in ecrans:
                ecran.resize(900, 500); ecran.show(); app.processEvents(); ecran.close(); ecran.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            ecrans.clear()
            app.processEvents()
            assert not db.DB_PATH.read_bytes().startswith(b'SQLite format 3')
            protection.verrouiller()
            coffre.ACTIF = None
            resultat = {'ok': True, 'version': VERSION, 'qt': True, 'chiffrement': True,
                        'pdf': True, 'tva': True, 'documents': True}
    except Exception:
        resultat['erreur'] = traceback.format_exc()
    Path(rapport).write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if resultat['ok'] else 1
