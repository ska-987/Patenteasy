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
            protection.creer('verification', 'VerificationLocale-040!')
            g.migrer()
            g.regler_region('US', 'USD', 2, 'MM/dd/yy', 'en', 'Sales tax', '', 'Business ID')
            db.modifier_entreprise('Atelier test', '', '', '', 'Moorea', 'TEST', '')
            client = db.ajouter_client('Client test')
            jour = g.aujourd_hui().isoformat()
            devis = g.creer_devis(client, jour, 'Vérification')
            db.ajouter_ligne_devis(devis, 'Prestation', 'heure', '1', '1000', '16')
            g.confirmer_fiscalite(int(jour[:4]), 'reel', ca='12000000')
            contenu = g.calculer(devis)
            assert contenu['tva'] == 16000
            pdf = generer(contenu)
            assert pdf.startswith(b'%PDF')
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView
            from PySide6.QtCore import QSize
            fichier = Path(dossier)/'verification.pdf'; fichier.write_bytes(pdf)
            lecture = QPdfDocument()
            assert lecture.load(str(fichier)) == QPdfDocument.Error.None_
            assert lecture.pageCount() > 0
            assert not lecture.render(0, QSize(300,400)).isNull()
            view = QPdfView(); view.setDocument(lecture); view.show(); app.processEvents()
            view.setDocument(None); view.close(); view.deleteLater(); lecture.close(); lecture.deleteLater()
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
            from comptes import GestionComptes
            from sauvegardes import GestionSauvegardes
            from sauvegarde_portable import preparer, verifier
            comptes = GestionComptes(db.BaseDonnees(db.DB_PATH))
            comptes.coffre = protection; comptes.session = protection.compte
            copies = GestionSauvegardes(comptes); copies.configurer(Path(dossier)/'copies')
            sauvegarde = copies.creer()
            preparation = preparer(sauvegarde, 'VerificationLocale-040!')
            assert verifier(preparation, Path(dossier)/'verification')['devis'] == 2
            protection.verrouiller()
            coffre.ACTIF = None
            nouveau = GestionComptes(db.BaseDonnees(Path(dossier)/'nouveau-pc'/'base.db'))
            nouveau.restaurer_nouveau_pc(preparation)
            c = nouveau.coffre.ouvrir()
            assert c.execute('SELECT count(*) FROM devis').fetchone()[0] == 2
            c.close(); nouveau.coffre.verrouiller()
            coffre.ACTIF = None
            resultat = {'ok': True, 'version': VERSION, 'qt': True, 'chiffrement': True,
                        'pdf': True, 'apercu_pdf': True, 'taxe': True, 'documents': True,
                        'profil_general': True, 'sauvegarde_nouveau_pc': True}
    except Exception:
        resultat['erreur'] = traceback.format_exc()
    Path(rapport).write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if resultat['ok'] else 1
