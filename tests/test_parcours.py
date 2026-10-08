# SPDX-License-Identifier: GPL-3.0-or-later
import json
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import database as db
import gestion as g
import main
import web_final
from fastapi.testclient import TestClient

@pytest.fixture
def application(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DATA_DIR',tmp_path)
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'test.db')
    with TestClient(main.app) as client:
        yield client


def post(c,url,**data):
    return c.post(url,data={'csrf_token':web_final.CSRF,**data})


def preparer(c,regime='franchise'):
    jour=g.aujourd_hui().isoformat()
    r=post(c,'/entreprise',nom='Atelier TEST',responsable='Mika',telephone='123',email='test@example.org',adresse='Moorea',numero_tahiti='TEST',numero_rcs='TEST')
    assert r.status_code==200
    assert post(c,'/entreprise/debut-activite',date_debut_activite='2020-01-01').status_code==200
    assert post(c,'/reglages',validite='15',reglement='Virement à réception',vente='Garantie selon dispositions applicables',solde='1000',date_solde=jour).status_code==200
    assert post(c,'/fiscalite',annee=g.aujourd_hui().year,regime=regime,date_confirmation=f'{g.aujourd_hui().year}-01-01',ca='0',date_ca=jour).status_code==200
    cid=db.ajouter_client('Client TEST',adresse='Tahiti')
    return cid,jour


def devis_test(c,regime='franchise'):
    cid,jour=preparer(c,regime)
    r=post(c,'/devis',client_id=cid,date_devis=jour,objet='Réparation')
    assert r.status_code==200
    did=db.lister_devis()[0]['id']
    assert db.obtenir_devis(did)['validite_jours']==15
    r=post(c,f'/devis/{did}/ligne-libre',designation='Main d’œuvre',unite='heure',quantite='1,5',prix_unitaire='3500',taxe='13',reference='MO',type_article='service',enregistrer_catalogue='true')
    assert r.status_code==200
    return did,jour


def test_pages_et_csrf(application):
    for url in ['/','/clients','/articles','/entreprise','/reprise','/journal','/devis','/factures','/reglages','/fiscalite','/echeances','/stock','/aide']:
        r=application.get(url)
        assert r.status_code==200,url
        assert 'Patenteasy' in r.text
    assert application.post('/clients',data={'nom':'Interdit'}).status_code==403
    assert db.lister_clients()==[]


def test_document_paiement_immutabilite(application):
    did,jour=devis_test(application)
    assert g.calculer(did)['ttc']==525000
    # doublon catalogue : pas de ligne supplémentaire
    r=post(application,f'/devis/{did}/ligne-libre',designation='Autre',unite='heure',quantite='1',prix_unitaire='1',taxe='13',reference='MO',enregistrer_catalogue='true')
    assert r.status_code==400
    assert len(db.lister_lignes_devis(did))==1
    assert post(application,f'/devis/{did}/emettre').status_code==200
    avant=g.calculer(did)
    db.modifier_client(avant['client']['id'],'Nouveau nom')
    assert g.calculer(did)['client']['nom']=='Client TEST'
    assert post(application,f'/devis/{did}/decision',statut='accepte').status_code==200
    assert post(application,f'/devis/{did}/facturer',date_facture=jour,echeance=jour).status_code==200
    fid=g.documents()[0]['id']
    assert post(application,f'/factures/{fid}/paiement',date_paiement=jour,montant='2000',mode='virement').status_code==200
    assert g.document(fid)['reste']==325000
    assert post(application,f'/factures/{fid}/paiement',date_paiement=jour,montant='4000',mode='virement').status_code==400
    assert len(db.lister_operations(g.aujourd_hui().year))==1
    op=g.document(fid)['paiements'][0]['operation_id']
    assert post(application,f'/journal/{op}/supprimer').status_code==400
    assert application.get(f'/factures/{fid}/pdf').content.startswith(b'%PDF')
    assert application.get(f'/devis/{did}/pdf').content.startswith(b'%PDF')
    assert post(application,f'/devis/{did}/facturer',date_facture=jour,echeance=jour).status_code==400
    assert post(application,f'/devis/{did}/dupliquer').status_code==200
    assert len(db.lister_devis())==2


def test_tva_avoir_stock(application):
    did,jour=devis_test(application,'reel')
    assert g.calculer(did)['tva']==68250
    assert post(application,f'/devis/{did}/emettre').status_code==200
    assert post(application,f'/devis/{did}/decision',statut='accepte').status_code==200
    assert post(application,f'/devis/{did}/facturer',date_facture=jour,echeance=jour).status_code==200
    fid=g.documents()[0]['id']
    assert post(application,f'/factures/{fid}/avoir',motif='Annulation').status_code==200
    assert g.document(fid)['reste']==0
    assert post(application,f'/factures/{fid}/avoir',motif='Encore').status_code==400
    aid=db.ajouter_article('P1','Pompe',prix_vente='5000',taxe='16')
    assert post(application,'/stock',article_id=aid,jour=jour,quantite='3',sens='entree',motif='Achat').status_code==200
    assert post(application,'/stock',article_id=aid,jour=jour,quantite='4',sens='sortie',motif='Vente').status_code==400
    assert g.stock()[0]['stock']==300


def test_sauvegarde_et_reprise(application,tmp_path):
    cid,jour=preparer(application)
    annee=g.aujourd_hui().year
    db.enregistrer_ca_n1(annee,'0')
    assert 'value="0"' in application.get('/reprise').text
    db.enregistrer_fin_reprise(annee,jour)
    assert post(application,'/journal',annee=annee,date_operation=jour,libelle='Double',type_operation='recette',montant='1').status_code==400
    r=application.get('/sauvegarde')
    fichier=tmp_path/'backup.db'; fichier.write_bytes(r.content)
    with sqlite3.connect(fichier) as c:
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert c.execute('SELECT nom FROM clients').fetchone()[0]=='Client TEST'
    assert application.get('/export/journal').status_code==200


def test_avoir_partiel_et_remboursement(application):
    did,jour=devis_test(application)
    post(application,f'/devis/{did}/emettre')
    post(application,f'/devis/{did}/decision',statut='accepte')
    post(application,f'/devis/{did}/facturer',date_facture=jour,echeance=jour)
    fid=g.documents()[0]['id']; ligne=g.document(fid)['contenu']['lignes'][0]
    assert post(application,f'/factures/{fid}/paiement',date_paiement=jour,montant='5250',mode='virement').status_code==200
    assert post(application,f'/factures/{fid}/avoir',motif='Réduction de prestation',**{f'q_{ligne["id"]}':'0,5'}).status_code==200
    assert g.document(fid)['a_rembourser']==175000
    assert post(application,f'/factures/{fid}/rembourser',jour=jour,montant='1750',mode='virement').status_code==200
    assert g.document(fid)['a_rembourser']==0
    assert post(application,f'/factures/{fid}/rembourser',jour=jour,montant='1',mode='virement').status_code==400
    assert len(db.lister_operations(g.aujourd_hui().year))==2


def test_lignes_modification_et_regime_inconnu(application):
    did,jour=devis_test(application)
    ligne=db.lister_lignes_devis(did)[0]['id']
    assert application.get(f'/devis/{did}/lignes/{ligne}/modifier').status_code==200
    assert post(application,f'/devis/{did}/lignes/{ligne}/modifier',reference='MO',designation='Main d’œuvre',unite='heure',quantite='2',prix_unitaire='3500',taxe='13').status_code==200
    assert g.calculer(did)['ht']==700000
    g.confirmer_fiscalite(g.aujourd_hui().year,'','','','')
    assert post(application,f'/devis/{did}/emettre').status_code==200
    assert db.obtenir_devis(did)['statut']=='envoye'
    did=g.dupliquer_devis(did)
    ligne=db.lister_lignes_devis(did)[0]['id']
    assert post(application,f'/devis/{did}/lignes/{ligne}/supprimer').status_code==200
    assert db.lister_lignes_devis(did)==[]
