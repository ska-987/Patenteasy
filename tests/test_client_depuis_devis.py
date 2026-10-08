# SPDX-License-Identifier: GPL-3.0-or-later
"""Créer et sélectionner un client en poursuivant la saisie d'un devis."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox
from PySide6.QtCore import QTimer
import database as db
import gestion as g
import coffre
import qt_app as ui


@pytest.fixture
def app(): return QApplication.instance() or QApplication([])


@pytest.fixture
def base(tmp_path, monkeypatch):
    coffre.ACTIF = None
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'base.db')
    monkeypatch.setattr(db, 'DATA_DIR', tmp_path)
    g.migrer();db.modifier_entreprise('Entreprise', '', '', '', '', '', '')
    yield
    coffre.ACTIF = None


def remplir_client(app, nom='Nouveau client', annuler=False):
    def remplir():
        dialogue = app.activeModalWidget()
        assert isinstance(dialogue, ui.ClientDialog)
        dialogue.nom.setText(nom);dialogue.tel.setText('+123 456 789')
        dialogue.email.setText('client@example.com');dialogue.adresse.setPlainText('Adresse libre\nPays libre')
        dialogue.buttons.button(QDialogButtonBox.StandardButton.Cancel if annuler else QDialogButtonBox.StandardButton.Save).click()
    QTimer.singleShot(0, remplir)


def test_premier_client_cree_dans_formulaire_nouveau_devis(app, base):
    dialogue = ui.QuoteCreateDialog();dialogue.show();app.processEvents()
    dialogue.objet.setText('Objet déjà saisi');dialogue.date.setDate(ui.qdate_from_iso('2026-10-08'))
    assert not dialogue.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()
    remplir_client(app)
    dialogue.new_client_btn.click()
    clients = db.lister_clients()
    assert len(clients) == 1
    assert dialogue.client.currentData() == clients[0]['id']
    assert clients[0]['telephone'] == '+123 456 789' and clients[0]['adresse'] == 'Adresse libre\nPays libre'
    assert dialogue.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()
    assert dialogue.objet.text() == 'Objet déjà saisi'
    devis = g.creer_devis(*dialogue.values())
    assert db.obtenir_devis(devis)['client_id'] == clients[0]['id']
    assert db.obtenir_devis(devis)['objet'] == 'Objet déjà saisi'
    dialogue.close()


def test_creer_devis_depuis_liste_vide(app, base, monkeypatch):
    ouvert = []
    class Creation(ui.QuoteCreateDialog):
        def exec(self): ouvert.append(self.client.count());return QDialog.DialogCode.Rejected
    monkeypatch.setattr(ui, 'QuoteCreateDialog', Creation)
    monkeypatch.setattr(ui, 'show_info', lambda *args: pytest.fail('La création ne doit pas être bloquée sans clients.'))
    page = ui.QuotesPage();page.add()
    assert ouvert == [0] and db.lister_devis() == []
    page.close()


def test_nouveau_client_selectionne_sans_perdre_brouillon_incomplet(app, base):
    ancien = db.ajouter_client('Client précédent')
    devis = g.creer_devis(ancien, '2026-10-08', 'Objet initial')
    db.ajouter_ligne_devis(devis, 'Service conservé', 'unité', '1', '100', '0')
    dialogue = ui.QuoteEditorDialog(devis);dialogue.show();app.processEvents()
    dialogue.objet.setText('Objet modifié à conserver')
    dialogue.date.entry.setText('08/10/')
    remplir_client(app, 'Autre client')
    dialogue.new_client_btn.click()
    nouveau = dialogue.client.currentData()
    assert nouveau != ancien and db.obtenir_client(nouveau)['nom'] == 'Autre client'
    assert dialogue.objet.text() == 'Objet modifié à conserver'
    assert dialogue.date.entry.text() != '08/10/26'
    assert dialogue.lines.item(0, 1).text() == 'Service conservé'
    assert dialogue.save_header(quiet=True, refresh=False)
    pending = g.lire_brouillon_ui(devis)
    assert pending['client_id'] == nouveau and pending['objet'] == 'Objet modifié à conserver'
    dialogue.date.setDate(ui.qdate_from_iso('2026-10-08'))
    assert dialogue.save_header(refresh=False)
    assert db.obtenir_devis(devis)['client_id'] == nouveau
    dialogue.close()


def test_annuler_nouveau_client_conserve_selection_et_saisie(app, base):
    ancien = db.ajouter_client('Client précédent')
    dialogue = ui.QuoteCreateDialog();dialogue.objet.setText('À conserver')
    dialogue.client.setCurrentIndex(dialogue.client.findData(ancien))
    remplir_client(app, annuler=True)
    dialogue.new_client_btn.click()
    assert len(db.lister_clients()) == 1 and dialogue.client.currentData() == ancien
    assert dialogue.objet.text() == 'À conserver'
    dialogue.close()


def test_erreur_client_conserve_formulaire_puis_permet_reessayer(app, base, monkeypatch):
    appels = []
    def erreur(parent, exc):
        appels.append(str(exc))
        def corriger():
            dialogue = app.activeModalWidget()
            assert isinstance(dialogue, ui.ClientDialog)
            assert dialogue.tel.text() == '+123 456 789'
            dialogue.nom.setText('Client corrigé')
            dialogue.buttons.button(QDialogButtonBox.StandardButton.Save).click()
        QTimer.singleShot(0, corriger)
    monkeypatch.setattr(ui, 'show_error', erreur)
    dialogue = ui.QuoteCreateDialog()
    remplir_client(app, nom='   ')
    dialogue.new_client_btn.click()
    assert len(appels) == 1 and len(db.lister_clients()) == 1
    assert db.obtenir_client(dialogue.client.currentData())['nom'] == 'Client corrigé'
    dialogue.close()


def test_devis_finalise_ne_propose_pas_changement_client(app, base):
    client = db.ajouter_client('Client')
    devis = g.creer_devis(client, '2026-10-08')
    db.ajouter_ligne_devis(devis, 'Service', 'unité', '1', '10', '0');g.emettre_devis(devis)
    dialogue = ui.QuoteEditorDialog(devis);dialogue.show();app.processEvents()
    assert not dialogue.client.isEnabled() and not dialogue.new_client_btn.isVisible()
    dialogue.close()
