# SPDX-License-Identifier: GPL-3.0-or-later
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import database as db,gestion as g,coffre
from PySide6.QtWidgets import QApplication,QDialog,QMessageBox,QFileDialog
from PySide6.QtCore import QSettings,QTimer,Qt
from PySide6.QtTest import QTest
from PySide6.QtPdf import QPdfDocument
import qt_app as ui
import exports_pdf

@pytest.fixture
def app():return QApplication.instance() or QApplication([])

@pytest.fixture
def facture(tmp_path,monkeypatch):
    coffre.ACTIF=None
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'base.db');monkeypatch.setattr(db,'DATA_DIR',tmp_path)
    g.migrer();db.modifier_entreprise('Entreprise','','','','','','')
    client=db.ajouter_client('Client');jour=g.aujourd_hui().isoformat()
    devis=g.creer_devis(client,jour,'Document test')
    db.ajouter_ligne_devis(devis,'Désignation distincte','unité','2','10.25','0','REF-2026')
    g.emettre_devis(devis);g.decision_devis(devis,'accepte')
    ident=g.creer_facture(devis,jour,jour)
    yield ident,devis
    coffre.ACTIF=None

@pytest.fixture
def export_dir(app,tmp_path,monkeypatch):
    settings=QSettings(str(tmp_path/'exports.ini'),QSettings.IniFormat)
    monkeypatch.setattr(exports_pdf,'preferences',lambda:settings)
    bureau=tmp_path/'Bureau';bureau.mkdir()
    monkeypatch.setattr(exports_pdf.QStandardPaths,'writableLocation',lambda _:str(bureau))
    return settings,bureau


def fail(parent,error):raise error


def test_ouverture_facture_et_encaissement_depuis_interface(app,facture,monkeypatch):
    ident,devis=facture
    monkeypatch.setattr(ui,'show_error',fail)
    journal=[];main=SimpleNamespace(gestion_comptes=SimpleNamespace(tracer=lambda *args:journal.append(args)))
    monkeypatch.setattr(app,'fenetre_principale',main,raising=False)
    class Paiement(ui.PaymentDialog):
        def exec(self):
            self.amount.setText('10.25');self.reference.setText('REGLEMENT-1')
            self.mode.setCurrentIndex(self.mode.findData('carte'))
            return QDialog.Accepted
    monkeypatch.setattr(ui,'PaymentDialog',Paiement)
    dialog=ui.InvoiceDialog(ident);dialog.resize(850,500);dialog.show();app.processEvents()
    assert dialog.lines.horizontalHeaderItem(0).text()=='Référence'
    assert dialog.lines.item(0,0).text()=='REF-2026'
    assert dialog.lines.item(0,1).text()=='Désignation distincte'
    assert dialog.pay_btn.isVisible()
    assert not dialog.scroll.isAncestorOf(dialog.pay_btn)
    dialog.pay_btn.click()
    assert g.document(ident)['paye']==1025 and g.document(ident)['reste']==1025
    assert dialog.payments.rowCount()==1 and journal
    dialog.pay_btn.click()
    assert g.document(ident)['reste']==0 and not dialog.pay_btn.isVisible()
    dialog.close()


def test_ouvrir_depuis_liste_et_tableau_de_bord(app,facture,monkeypatch):
    ident,_=facture;opened=[]
    class Invoice(ui.InvoiceDialog):
        def exec(self):opened.append(self.document_id);return QDialog.Accepted
    monkeypatch.setattr(ui,'InvoiceDialog',Invoice)
    page=ui.InvoicesPage();page.compte_connecte={"role":"admin"};page.refresh();page.show();app.processEvents();page.table.selectRow(0)
    page.open()
    dashboard=ui.DashboardPage();dashboard.refresh();dashboard.unpaid.selectRow(0);dashboard.open_invoice()
    assert opened==[ident,ident]
    page.close();dashboard.close()


def test_apercu_et_export_sur_meme_facture(app,facture,monkeypatch):
    import apercu_pdf
    ident,_=facture;previews=[];exports=[]
    monkeypatch.setattr(ui,'show_error',fail)
    monkeypatch.setattr(apercu_pdf,'ouvrir',lambda parent,data,name:previews.append((data,name)))
    monkeypatch.setattr(ui,'save_pdf',lambda parent,data,name:exports.append((data,name)))
    dialog=ui.InvoiceDialog(ident)
    dialog.pdf_btn.click();dialog.export_btn.click()
    assert previews[0][1]==exports[0][1]==g.document(ident)['numero']+'.pdf'
    assert previews[0][0].startswith(b'%PDF') and exports[0][0].startswith(b'%PDF')
    dialog.close()


def test_reference_vide_conserve_selection_et_edition(app,facture):
    _,old=facture;devis=g.dupliquer_devis(old)
    with g.connexion() as c:c.execute("UPDATE devis_lignes SET reference='' WHERE devis_id=?",(devis,))
    dialog=ui.QuoteEditorDialog(devis)
    dialog.lines.selectRow(0)
    assert ui.selected_id(dialog.lines) is not None
    assert dialog.lines.item(0,0).text()=='' and dialog.lines.item(0,1).text()=='Désignation distincte'
    dialog.close()


def test_premier_export_cree_dossier_et_memorise(app,export_dir,monkeypatch):
    settings,bureau=export_dir;asked=[];defaults=[]
    def proposer(self):asked.append(1);return QMessageBox.Yes
    monkeypatch.setattr(QMessageBox,'exec',proposer)
    def enregistrer(self):defaults.append(self.selectedFiles()[0]);return QDialog.Accepted
    monkeypatch.setattr(QFileDialog,'exec',enregistrer)
    p=exports_pdf.enregistrer(None,b'%PDF-test','fact-00001.pdf')
    q=exports_pdf.enregistrer(None,b'%PDF-test-2','dev-00001.pdf')
    assert p==bureau/'Patenteasy'/'fact-00001.pdf' and p.read_bytes()==b'%PDF-test'
    assert q.parent==p.parent and q.read_bytes()==b'%PDF-test-2'
    assert asked==[1] and Path(settings.value('exports_pdf/dossier'))==p.parent
    assert [Path(x) for x in defaults]==[p,q]


def test_export_choix_autre_dossier_et_annulation(app,export_dir,tmp_path,monkeypatch):
    settings,bureau=export_dir;autre=tmp_path/'Mes documents';autre.mkdir()
    monkeypatch.setattr(QMessageBox,'exec',lambda _:QMessageBox.Cancel)
    assert exports_pdf.enregistrer(None,b'%PDF','fact.pdf') is None
    assert not (bureau/'Patenteasy').exists() and not settings.value('exports_pdf/dossier')
    monkeypatch.setattr(QMessageBox,'exec',lambda _:QMessageBox.No)
    monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *args:str(autre))
    monkeypatch.setattr(QFileDialog,'exec',lambda _:QDialog.Accepted)
    p=exports_pdf.enregistrer(None,b'%PDF','fact.pdf')
    assert p.parent==autre and not (bureau/'Patenteasy').exists()


def test_annuler_export_ne_remplace_aucun_pdf(app,export_dir,monkeypatch):
    settings,bureau=export_dir;settings.setValue('exports_pdf/dossier',str(bureau))
    existant=bureau/'fact.pdf';existant.write_bytes(b'%PDF-original')
    monkeypatch.setattr(QFileDialog,'exec',lambda _:QDialog.Rejected)
    assert exports_pdf.enregistrer(None,b'%PDF-nouveau','fact.pdf') is None
    assert existant.read_bytes()==b'%PDF-original'


def test_export_depuis_apercu_utilise_dossier_memorise(app,facture,export_dir,monkeypatch):
    import apercu_pdf
    from PySide6.QtWidgets import QPushButton
    ident,_=facture;settings,bureau=export_dir;settings.setValue('exports_pdf/dossier',str(bureau))
    monkeypatch.setattr(QFileDialog,'exec',lambda _:QDialog.Accepted)
    monkeypatch.setattr(ui,'show_info',lambda *args:None);monkeypatch.setattr(ui,'show_error',fail)
    def click():
        dialog=app.activeModalWidget()
        if dialog:
            next(b for b in dialog.findChildren(QPushButton) if b.text()=='Enregistrer le PDF').click()
            dialog.accept()
    for _ in range(3):
        QTimer.singleShot(0,click)
        apercu_pdf.ouvrir(None,ui.generer(g.document(ident)['contenu']),'facture-apercu.pdf')
    assert (bureau/'facture-apercu.pdf').read_bytes().startswith(b'%PDF')


def test_reference_et_designation_dans_pdf(app,facture,tmp_path):
    ident,_=facture
    pdf=tmp_path/'fact.pdf';pdf.write_bytes(ui.generer(g.document(ident)['contenu']))
    lecture=QPdfDocument();assert lecture.load(str(pdf))==QPdfDocument.Error.None_
    texte=lecture.getAllText(0).text()
    assert 'Référence' in texte and 'Désignation' in texte
    assert 'REF-2026' in texte and 'Désignation distincte' in texte
    assert 'REF-2026 — Désignation' not in texte
    lecture.close()


def test_especes_profil_general_sans_regle_locale(app,facture):
    ident,_=facture
    g.payer(ident,g.aujourd_hui().isoformat(),'10.25','especes','')
    assert g.document(ident)['paye']==1025
