# SPDX-License-Identifier: GPL-3.0-or-later
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
import database as db
import gestion as g
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QTableWidget, QLabel
from PySide6.QtTest import QTest
import qt_app as ui

@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path/'test.db')
    monkeypatch.setattr(db, 'DATA_DIR', tmp_path)
    g.migrer()
    db.modifier_entreprise('Atelier', '', '', '', 'Moorea', '123', '')
    cid = db.ajouter_client('Client')
    did = g.creer_devis(cid, g.aujourd_hui().isoformat(), 'Réparation')
    db.ajouter_ligne_devis(did, 'Pièce', 'pièce', '1', '1000', '16')
    return did

@pytest.fixture
def app():
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(ui.APP_QSS)
    return app

@pytest.mark.parametrize('regime,tva', [('', 0), ('franchise', 0), ('reel', 16000)])
def test_ca_sans_date_ne_bloque_pas_et_ne_change_pas_la_tva(base, regime, tva):
    year=g.aujourd_hui().year
    g.confirmer_fiscalite(year, regime, ca='12000000')
    # D'anciennes options et dates ne doivent plus imposer le réel.
    db.enregistrer_option_reel(year, f'{year}-01-01')
    assert g.calculer(base)['tva'] == tva
    assert g.rappel_seuil_ca(year)
    g.emettre_devis(base)  # Ni conditions, ni attestation, ni dates fiscales.
    assert db.obtenir_devis(base)['statut'] == 'envoye'
    before = g.calculer(base)
    g.confirmer_fiscalite(year, 'reel' if regime != 'reel' else '')
    assert g.calculer(base) == before  # Les documents émis restent figés.


def test_seuil_et_effacement(base):
    year=g.aujourd_hui().year
    g.confirmer_fiscalite(year, 'reel', ca='10000000')
    assert not g.rappel_seuil_ca(year)
    g.confirmer_fiscalite(year, '', ca='')
    f=db.obtenir_fiscalite_annuelle(year)
    assert f['regime_confirme'] == '' and f['ca_annee_centiemes'] is None
    assert f['date_confirmation'] == '' and f['date_ca'] == ''


def test_selection_esc_et_clic_vide_ne_suppriment_rien(app):
    table=QTableWidget()
    ui.configure_table(table, ['Désignation', 'Montant'])
    ui.fill_table(table, [['Pompe', '1000'], ['Moteur', '2000']], [11, 22])
    table.resize(500,300);table.show();app.processEvents()
    table.selectRow(0)
    assert ui.selected_id(table) is not None
    QTest.keyClick(table, Qt.Key_Escape)
    assert ui.selected_id(table) is None
    table.selectRow(0)
    QTest.mouseClick(table.viewport(), Qt.LeftButton, pos=QPoint(15, 200))
    assert ui.selected_id(table) is None
    assert table.rowCount() == 2
    assert {table.item(i,0).text() for i in range(2)} == {'Pompe','Moteur'}


def test_pages_et_formulaires_defilent(app, base):
    settings=ui.SettingsPage();settings.resize(900,400);settings.show();app.processEvents()
    assert settings.scroll.verticalScrollBar().maximum() > 0
    settings.scroll.verticalScrollBar().setValue(settings.scroll.verticalScrollBar().maximum())
    assert settings.scroll.verticalScrollBar().value() > 0
    form=ui.FormDialog('Long formulaire')
    for i in range(25):form.form.addRow(str(i),QLabel('Champ'))
    form.resize(560,300);form.show();app.processEvents()
    assert form.scroll.verticalScrollBar().maximum() > 0
    quote=ui.QuoteEditorDialog(base);quote.resize(900,500);quote.show();app.processEvents()
    assert not quote.terms_panel.isVisible()
    quote.terms_toggle.click();app.processEvents()
    assert quote.terms_panel.isVisible()
    assert quote.scroll.verticalScrollBar().maximum() > 0
    for widget in (settings,form,quote):widget.close()


@pytest.mark.parametrize('typed,display,iso', [
    ('081026', '08/10/26', '2026-10-08'),
    ('311226', '31/12/26', '2026-12-31'),
    ('290228', '29/02/28', '2028-02-29'),
])
def test_dates_six_chiffres(app, typed, display, iso):
    date=ui.make_date('2026-01-01')
    date.entry.selectAll()
    QTest.keyClicks(date.entry, typed)
    assert date.entry.text() == display
    assert ui.iso_date(date) == iso


def test_date_invalide_vide_et_ancien_siecle(app):
    date=ui.make_date('1999-12-31')
    assert ui.iso_date(date) == '1999-12-31'
    date.entry.selectAll(); QTest.keyClicks(date.entry, '290227')
    with pytest.raises(ValueError, match='n’existe pas'): ui.iso_date(date)
    date.entry.selectAll(); QTest.keyClicks(date.entry, '0801')
    with pytest.raises(ValueError, match='Complétez'): ui.iso_date(date)
    optional=ui.DateInput(optional=True)
    assert ui.iso_date(optional) == ''
    optional.setDate(ui.qdate_from_iso('2026-10-08'))
    assert optional.entry.text() == '08/10/26'
    optional.clear(); assert ui.iso_date(optional) == ''
