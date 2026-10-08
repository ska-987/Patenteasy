# SPDX-License-Identifier: GPL-3.0-or-later
"""Conditions facultatives : réglages actuels et pied de page des documents."""
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtWidgets import QApplication, QTextEdit, QStackedWidget, QWidget
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtPdf import QPdfDocument
import database as db
import gestion as g
import coffre
import qt_app as ui
from pdf_documents import generer


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def documents(tmp_path, monkeypatch):
    coffre.ACTIF = None
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'base.db')
    monkeypatch.setattr(db, 'DATA_DIR', tmp_path)
    g.migrer()
    db.modifier_entreprise('Entreprise', '', '', '', '', '', '')
    client = db.ajouter_client('Client')
    devis = g.creer_devis(client, '2026-10-08', 'Prestation')
    db.ajouter_ligne_devis(devis, 'Service', 'unité', '1', '100', '0')
    g.emettre_devis(devis)
    g.decision_devis(devis, 'accepte')
    facture = g.creer_facture(devis, '2026-10-08', '2026-10-15')
    yield devis, facture
    coffre.ACTIF = None


def textes_pdf(data, path):
    path.write_bytes(data)
    lecture = QPdfDocument()
    assert lecture.load(str(path)) == QPdfDocument.Error.None_
    textes = [lecture.getAllText(page).text() for page in range(lecture.pageCount())]
    return lecture, textes


def regler(vente='', reglement='', mention=''):
    g.regler_entreprise(30, vente, reglement, mention, '', '0', '')


def test_conditions_ajoutees_modifiees_effacees_sur_documents_anciens(app, documents, tmp_path):
    devis, facture = documents
    g.payer(facture, '2026-10-08', '25', 'carte', '')
    avant = g.document(facture)
    devis_avant = g.calculer(devis)
    for vente, paiement, note in [('Vente mondiale', 'Paiement convenu', 'Note libre'),
                                 ('Nouvelles conditions', '', 'Nouvelle note'), ('', '', '')]:
        regler(vente, paiement, note)
        for contenu in [g.calculer(devis), g.document(facture)['contenu']]:
            lecture, textes = textes_pdf(generer(contenu), tmp_path / 'document.pdf')
            texte = '\n'.join(textes)
            assert bool(vente) == ('Conditions de vente' in texte)
            assert bool(paiement) == ('Conditions de règlement' in texte)
            assert bool(note) == ('Mentions complémentaires' in texte)
            for valeur in (vente, paiement, note):
                if valeur: assert valeur in texte
            assert 'Vente mondiale' not in texte or vente == 'Vente mondiale'
            lecture.close()
        assert g.calculer(devis) == devis_avant
        assert g.document(facture) == avant  # Montants, instantanés et paiements conservés.


def test_conditions_en_bas_de_derniere_page_sans_chevauchement(app, documents, tmp_path):
    devis, _ = documents
    regler('Texte de vente', 'Texte de paiement', 'Dernière mention')
    contenu = g.calculer(devis)
    for n in (1, 70):
        contenu['lignes'] = contenu['lignes'][:1] * n
        lecture, textes = textes_pdf(generer(contenu), tmp_path / 'position.pdf')
        dernier = lecture.pageCount() - 1
        assert ('Conditions de vente' in textes[-1]) and all('Conditions de vente' not in t for t in textes[:-1])
        assert 'Total à payer' in textes[-1]  # Pas de page contenant uniquement un court pied de page.
        index = textes[-1].index('Conditions de vente')
        haut = lecture.getSelectionAtIndex(dernier, index, len('Conditions de vente')).boundingRectangle().top()
        assert haut > 650  # Dans le bas de la page A4 (842 points).
        index_fin = textes[-1].index('Dernière mention')
        bas = lecture.getSelectionAtIndex(dernier, index_fin, len('Dernière mention')).boundingRectangle().bottom()
        assert haut < bas < 790  # Le pied de page et la numérotation restent séparés.
        texte_complet = '\n'.join(textes)
        assert texte_complet.index('Acceptation') < texte_complet.index('Conditions de vente')
        lecture.close()


def test_conditions_longues_reparties_sans_perte(app, documents, tmp_path):
    devis, _ = documents
    regler('\n'.join(f'Clause {i:03d} : condition libre et lisible.' for i in range(200)), 'Fin des conditions de paiement')
    lecture, textes = textes_pdf(generer(g.calculer(devis)), tmp_path / 'long.pdf')
    assert lecture.pageCount() >= 4
    texte = '\n'.join(textes)
    for i in range(200): assert texte.count(f'Clause {i:03d}') == 1
    assert 'Fin des conditions de paiement' in textes[-1]
    for page in range(lecture.pageCount()): assert f'Page {page + 1}' in textes[page]
    lecture.close()


def test_anciens_textes_figes_ne_reapparaissent_pas(app, documents, tmp_path):
    devis, facture = documents
    with g.connexion() as c:
        for table, ident in [('devis', devis), ('documents', facture)]:
            contenu = json.loads(c.execute(f'SELECT instantane FROM {table} WHERE id=?', (ident,)).fetchone()[0])
            contenu['conditions_vente'] = 'Ancienne condition figée'
            c.execute(f'UPDATE {table} SET instantane=? WHERE id=?', (json.dumps(contenu), ident))
    regler()
    for contenu in [g.calculer(devis), g.document(facture)['contenu']]:
        lecture, textes = textes_pdf(generer(contenu), tmp_path / 'ancien.pdf')
        assert 'Ancienne condition figée' not in '\n'.join(textes)
        lecture.close()


def test_conditions_editables_uniquement_dans_reglages_et_ancien_brouillon_preserve(app, documents, monkeypatch, tmp_path):
    devis, _ = documents
    copie = g.dupliquer_devis(devis)
    g.enregistrer_brouillon_ui(copie, {'client_id': db.obtenir_devis(copie)['client_id'], 'date': '08/10/26',
        'objet': 'Objet à conserver', 'validite': 30, 'vente': 'Ancienne saisie', 'reglement': '', 'mention': ''})
    monkeypatch.setattr(ui, 'show_info', lambda *args: None)
    settings = ui.SettingsPage();settings.refresh()
    settings.terms.setPlainText('Texte réglages');settings.save()
    assert g.conditions_documents()['conditions_vente'] == 'Texte réglages'
    editeur = ui.QuoteEditorDialog(copie)
    assert not editeur.findChildren(QTextEdit)
    assert editeur.objet.text() == 'Objet à conserver'
    assert editeur.save_header(refresh=False)
    d = db.obtenir_devis(copie)
    g.modifier_devis(copie, d['client_id'], d['date_devis'], d['objet'], 30, 'Tentative locale', '', '')
    assert g.conditions_documents()['conditions_vente'] == 'Texte réglages'
    assert db.obtenir_devis(copie)['conditions_vente'] == ''
    lecture, textes = textes_pdf(generer(g.calculer(copie), True), tmp_path / 'brouillon.pdf')
    assert 'Texte réglages' in textes[-1] and 'Ancienne saisie' not in '\n'.join(textes)
    lecture.close();editeur.close();settings.close()


def test_conditions_libres_et_titres_traduits(app, documents, tmp_path):
    _, facture = documents
    contenu = g.document(facture)['contenu']
    contenu['entreprise']['langue'] = 'en'
    regler('Métier libre < texte & données >', 'Paiement libre')
    lecture, textes = textes_pdf(generer(contenu), tmp_path / 'english.pdf')
    texte = '\n'.join(textes)
    assert 'Sales terms' in texte and 'Payment terms' in texte
    assert 'Métier libre < texte & données >' in texte
    assert 'Additional notes' not in texte
    lecture.close()


def test_saisie_navigation_ancienne_facture_et_nouvel_export(app, documents, tmp_path, monkeypatch):
    devis, facture = documents
    avant = g.document(facture)
    stack = QStackedWidget()
    settings = ui.SettingsPage();settings.refresh()
    autre = QWidget();stack.addWidget(settings);stack.addWidget(autre)
    stack.resize(900, 500);stack.show();app.processEvents()
    QTest.keyClicks(settings.payment, 'Paiement a reception par virement')
    # Départ immédiat, sans attendre le délai et sans cliquer sur Enregistrer.
    stack.setCurrentWidget(autre);app.processEvents()
    assert not settings.conditions_timer.isActive()
    assert g.conditions_documents()['conditions_reglement'] == 'Paiement a reception par virement'
    reopened = ui.SettingsPage();reopened.refresh()
    assert reopened.payment.toPlainText() == 'Paiement a reception par virement'
    invoice = ui.InvoiceDialog(facture);invoice.show();app.processEvents()
    assert invoice.conditions.isVisible()
    heading, texte = invoice.conditions.fields['conditions_reglement']
    assert heading.isVisible() and texte.text() == reopened.payment.toPlainText()
    assert texte.textFormat() == Qt.TextFormat.PlainText
    assert not invoice.findChildren(QTextEdit)
    quote = ui.QuoteEditorDialog(devis);quote.show();app.processEvents()
    assert quote.conditions.fields['conditions_reglement'][1].text() == texte.text()
    pdfs = []
    monkeypatch.setattr(ui, 'save_pdf', lambda parent, data, name: pdfs.append(data))
    monkeypatch.setattr(ui, 'show_error', lambda parent, exc: pytest.fail(str(exc)))
    invoice.export_btn.click()
    lecture, textes = textes_pdf(pdfs[0], tmp_path / 'nouvel-export.pdf')
    assert reopened.payment.toPlainText() in textes[-1]
    assert 'Conditions de règlement' in textes[-1]
    assert g.document(facture) == avant
    lecture.close();invoice.close();quote.close();reopened.close();stack.close()


def test_conditions_auto_enregistrees_meme_autres_reglages_incomplets(app, documents):
    avant = db.obtenir_entreprise()
    settings = ui.SettingsPage();settings.refresh()
    settings.balance.setText('montant incomplet')
    settings.balance_date.entry.setText('08/10/')
    settings.payment.setPlainText('Règlement indépendant du solde')
    QTest.qWait(settings.conditions_timer.interval() + 100)
    assert not settings._conditions_dirty
    assert g.conditions_documents()['conditions_reglement'] == 'Règlement indépendant du solde'
    maintenant = db.obtenir_entreprise()
    for champ in ('solde_depart_centiemes', 'date_solde_depart', 'validite_devis_jours', 'periodicite_tva'):
        assert maintenant[champ] == avant[champ]
    settings.close()


def test_modification_et_effacement_actualisent_document_deja_ouvert(app, documents):
    devis, facture = documents
    invoice = ui.InvoiceDialog(facture);invoice.show()
    quote = ui.QuoteEditorDialog(devis);quote.show()
    settings = ui.SettingsPage();settings.refresh()
    assert not invoice.conditions.isVisible() and not quote.conditions.isVisible()
    for contenu in ('Texte initial <libre>', 'Texte modifié'):
        settings.payment.setPlainText(contenu)
        assert settings.save_conditions()
        for doc in (invoice, quote):
            assert doc.conditions.isVisible()
            assert doc.conditions.fields['conditions_reglement'][1].text() == contenu
    settings.payment.clear();assert settings.save_conditions()
    assert not invoice.conditions.isVisible() and not quote.conditions.isVisible()
    assert g.conditions_documents()['conditions_reglement'] == ''
    invoice.close();quote.close();settings.close()


def test_erreur_enregistrement_affichee_sans_perdre_saisie(app, documents, monkeypatch):
    settings = ui.SettingsPage();settings.refresh()
    def echec(*args): raise OSError('Disque indisponible')
    originale = g.regler_conditions_documents
    monkeypatch.setattr(g, 'regler_conditions_documents', echec)
    settings.payment.setPlainText('Texte à conserver')
    assert not settings.save_conditions()
    assert settings._conditions_dirty
    assert 'Conditions non enregistrées' in settings.conditions_status.text()
    settings.refresh()
    assert settings.payment.toPlainText() == 'Texte à conserver'
    monkeypatch.setattr(g, 'regler_conditions_documents', originale)
    assert settings.save_conditions()
    assert g.conditions_documents()['conditions_reglement'] == 'Texte à conserver'
    settings.close()
