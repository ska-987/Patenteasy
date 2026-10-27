import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
from pathlib import Path
import pytest
import database as db, gestion as g, coffre
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt
from PySide6.QtPdf import QPdfDocument
import qt_app as ui

@pytest.fixture
def base(tmp_path,monkeypatch):
    coffre.ACTIF=None
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'base.db');monkeypatch.setattr(db,'DATA_DIR',tmp_path)
    g.migrer();db.modifier_entreprise('Atelier test','','','','','','')
    return db.ajouter_client('Client test'),g.aujourd_hui().isoformat()

def facture(base,prix='100',client=None):
    cid,j=base;b=g.creer_brouillon_facture(client or cid,j,'Vente comptoir')
    db.ajouter_ligne_devis(b,'Pièce test','unité','1',prix,'0','PIECE')
    return g.emettre_facture_directe(b,j,j),b

@pytest.fixture
def app():return QApplication.instance() or QApplication([])

def test_facture_directe_sans_devis_numero_et_immutabilite(base,tmp_path):
    f,b=facture(base)
    d=g.document(f)
    assert d['devis_id'] is None and d['brouillon_id']==b
    assert d['numero'].startswith('fact-') and 'numero_devis' not in d['contenu']
    assert not db.lister_devis() and not g.brouillons_factures()
    assert not g.liste("SELECT * FROM sequences WHERE type='devis'")
    with pytest.raises(ValueError):g.emettre_facture_directe(b,base[1],base[1])
    with pytest.raises(ValueError):g.creer_facture(b,base[1],base[1])
    with pytest.raises(ValueError):db.modifier_ligne_devis(b,db.lister_lignes_devis(b)[0]['id'],'Autre','u','1','1','0')
    original=d['instantane'];g.payer(f,base[1],'100','carte','COMPTOIR')
    assert g.document(f)['instantane']==original and g.document(f)['reste']==0
    p=tmp_path/'direct.pdf';p.write_bytes(ui.generer(g.document(f)['contenu']))
    lecture=QPdfDocument();lecture.load(str(p));texte=lecture.getAllText(0).text();lecture.close()
    assert 'FACTURE' in texte and 'Devis de référence' not in texte

def test_brouillon_incomplet_repris_et_migration_idempotente(base):
    b=g.creer_brouillon_facture(base[0],base[1],'Urgence')
    assert [x['id'] for x in g.brouillons_factures()]==[b]
    with pytest.raises(ValueError):g.emettre_facture_directe(b,base[1],base[1])
    g.migrer();g.migrer();assert g.brouillons_factures()[0]['id']==b
    assert not g.liste("SELECT * FROM sequences WHERE type='facture'")

def test_avoir_partiellement_utilise_et_rembourse_sans_faux_encaissement(base):
    f,_=facture(base);g.payer(f,base[1],'100','carte','')
    a=g.creer_avoir(f,'Retour pièce');cible,_=facture(base,'80')
    assert g.etat_avoir(a)['disponible']==10000
    original=g.document(cible)['instantane']
    g.utiliser_avoir(a,cible,base[1],'60')
    assert g.document(cible)['reste']==2000 and g.document(cible)['encaisse']==0
    assert g.document(cible)['paiements'][0]['reference']==g.document(a)['numero']
    assert g.document(cible)['instantane']==original
    assert len(db.lister_operations(g.aujourd_hui().year))==1
    g.rembourser_avoir(a,base[1],'40','carte')
    etat=g.etat_avoir(a);assert etat['disponible']==0 and etat['utilise']==6000 and etat['rembourse']==4000
    assert g.document(f)['a_rembourser']==0
    with pytest.raises(ValueError):g.utiliser_avoir(a,cible,base[1],'1')
    with pytest.raises(ValueError):g.rembourser(f,base[1],'1','carte')
    assert len(db.lister_operations(g.aujourd_hui().year))==2

def test_avoir_impaye_deja_deduit_ne_peut_pas_etre_reutilise(base):
    f,_=facture(base);a=g.creer_avoir(f,'Annulation')
    assert g.etat_avoir(a)['compense']==10000 and g.etat_avoir(a)['disponible']==0
    cible,_=facture(base)
    with pytest.raises(ValueError):g.utiliser_avoir(a,cible,base[1],'100')
    with pytest.raises(ValueError):g.rembourser_avoir(a,base[1],'100','carte')

def test_avoir_meme_client_pas_depassement_et_ancien_remboursement(base):
    f,_=facture(base);g.payer(f,base[1],'100','carte','');a=g.creer_avoir(f,'Retour')
    g.rembourser(f,base[1],'30','carte')
    assert g.etat_avoir(a)['rembourse']==3000 and g.etat_avoir(a)['disponible']==7000
    autre,_=facture(base,'100',db.ajouter_client('Autre client'))
    with pytest.raises(ValueError):g.utiliser_avoir(a,autre,base[1],'10')
    cible,_=facture(base,'50')
    with pytest.raises(ValueError):g.utiliser_avoir(a,cible,base[1],'51')
    g.utiliser_avoir(a,cible,base[1],'50');assert g.etat_avoir(a)['disponible']==2000
    with pytest.raises(ValueError):g.rembourser(f,base[1],'21','carte')
    assert len(g.liste('SELECT * FROM utilisations_avoirs'))==1

def test_plusieurs_avoirs_paiement_partiel_et_remboursements(base):
    f,b=facture(base);g.payer(f,base[1],'50','carte','');line=db.lister_lignes_devis(b)[0]['id']
    a=g.creer_avoir(f,'Première partie',{str(line):'0.3'})
    autre=g.creer_avoir(f,'Reste',{str(line):'0.7'})
    assert g.etat_avoir(a)['compense']==3000 and g.etat_avoir(a)['disponible']==0
    assert g.etat_avoir(autre)['compense']==2000 and g.etat_avoir(autre)['disponible']==5000
    g.rembourser_avoir(autre,base[1],'50','carte');assert g.etat_avoir(autre)['disponible']==0

def test_ecrans_catalogue_long_facture_et_avoir(base,app,monkeypatch,tmp_path):
    db.ajouter_article('REF-'+'LONGUE'*50,'Pompe de remplacement '+'désignation '*60,prix_vente='50',taxe='0')
    dialog=ui.CatalogLineDialog();dialog.resize(560,480);dialog.show();app.processEvents()
    assert dialog.article.width()<=dialog.width() and dialog.width()<800
    dialog.article.showPopup();app.processEvents()
    assert dialog.article.view().window().width()<=dialog.article.width()
    assert 'Pompe de remplacement' in dialog.detail_article.text()
    dialog.article.hidePopup();dialog.close()
    f,b=facture(base);draft=g.creer_brouillon_facture(base[0],base[1])
    editeur=ui.QuoteEditorDialog(draft);editeur.show();app.processEvents()
    assert editeur.direct and editeur.emit_btn.text()=='Émettre la facture'
    assert not editeur.accept_btn.isVisible() and not editeur.invoice_btn.isVisible()
    editeur.close()
    g.payer(f,base[1],'100','carte','');a=g.creer_avoir(f,'Retour')
    avoir=ui.InvoiceDialog(a);avoir.compte_connecte={'role':'admin'};avoir.refresh();avoir.show();app.processEvents()
    assert avoir.use_credit_btn.isVisible() and avoir.refund_btn.isVisible()
    assert 'Disponible' in avoir.metrics.text()
    avoir.close()

def test_remboursement_origine_apres_utilisation_premier_avoir(base):
    f,b=facture(base);g.payer(f,base[1],'100','carte','');line=db.lister_lignes_devis(b)[0]['id']
    a=g.creer_avoir(f,'Premier',{str(line):'0.5'});b=g.creer_avoir(f,'Second',{str(line):'0.5'})
    cible,_=facture(base,'50');g.utiliser_avoir(a,cible,base[1],'50')
    g.rembourser(f,base[1],'50','carte')
    for ident in (a,b):
        e=g.etat_avoir(ident)
        assert e['disponible']==0
        assert e['compense']+e['utilise']+e['rembourse']==5000
    assert g.document(f)['a_rembourser']==0
    with pytest.raises(ValueError):g.rembourser_avoir(b,base[1],'1','carte')
