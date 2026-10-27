import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from datetime import date
from copy import deepcopy
import json
import pytest
from statuts_documents import statut_devis,statut_facture
from PySide6.QtWidgets import QApplication,QTableWidget,QWidget,QVBoxLayout,QLabel
from PySide6.QtCore import Qt
import qt_app as ui

JOUR=date(2026,10,27)

def devis(statut='envoye',expiration='2026-10-27'):
    return dict(statut=statut,date_devis='2026-10-01',validite_jours=90,instantane=json.dumps({'validite':expiration}))

def facture(**kw):
    return dict(type='facture',total_centiemes=1000,paye=0,credite=0,impute=0,echeance='2026-10-27',**kw)

@pytest.mark.parametrize('statut,expire,libelle,code',[
 ('brouillon','2026-10-01','Brouillon','neutre'),('envoye','2026-10-27','En cours','bleu'),
 ('envoye','2026-10-26','Hors délai','rouge'),('accepte','2026-10-01','Accepté','vert'),
 ('refuse','2026-10-01','Refusé','neutre'),('facture','2026-10-01','Facturé','violet')])
def test_statuts_devis_borne_et_decisions(statut,expire,libelle,code):
    d=devis(statut,expire);avant=deepcopy(d);r=statut_devis(d,JOUR)
    assert (r['libelle'],r['code'])==(libelle,code)
    assert d==avant


def test_validite_figee_et_date_manquante():
    d=devis();d['validite_jours']=1
    assert statut_devis(d,JOUR)['libelle']=='En cours'
    assert statut_devis(d,date(2026,10,28))['libelle']=='Hors délai'
    d.pop('instantane');assert statut_devis(d,JOUR)['libelle']=='Hors délai'
    d['date_devis']='invalide';assert statut_devis(d,JOUR)['libelle']=='À vérifier'

@pytest.mark.parametrize('paye,credite,impute,echeance,libelle,code',[
 (0,0,0,'2026-10-27','À régler','orange'),(300,0,0,'2026-10-27','Règlement partiel','orange'),
 (0,0,0,'2026-10-26','En retard','rouge'),(300,0,0,'2026-10-26','En retard','rouge'),
 (1000,0,0,'2026-10-01','Réglée','vert'),(0,1000,0,'2026-10-01','Soldée avec avoir','vert'),
 (1000,0,500,'2026-10-01','Soldée avec avoir','vert')])
def test_statuts_factures_reste_et_dates(paye,credite,impute,echeance,libelle,code):
    d=facture();d.update(paye=paye,credite=credite,impute=impute,echeance=echeance);avant=deepcopy(d)
    r=statut_facture(d,JOUR);assert (r['libelle'],r['code'])==(libelle,code);assert d==avant


def test_avoir_et_echeance_invalide():
    d=facture();d['type']='avoir';assert statut_facture(d,JOUR,{'statut':'Disponible'})['libelle']=='Disponible'
    d['type']='facture';d['echeance']='';assert statut_facture(d,JOUR)['libelle']=='À vérifier'

@pytest.fixture
def app():return QApplication.instance() or QApplication([])


def test_couleurs_suivent_id_apres_tri_et_themes(app):
    t=QTableWidget();ui.configure_table(t,['Document','État'])
    ui.fill_table(t,[['B','En retard'],['A','Réglée']],[1,2])
    etats={1:statut_facture({**facture(),'echeance':'2026-10-01'},JOUR),2:statut_facture({**facture(),'paye':1000},JOUR)}
    t.sortItems(0,Qt.SortOrder.AscendingOrder)
    for sombre in (False,True):
        ui.colorer_statuts(t,1,etats,sombre)
        for r in range(2):
            ident=t.item(r,0).data(Qt.UserRole);item=t.item(r,1)
            assert item.data(Qt.UserRole+20)==etats[ident]['code']
            assert item.font().bold() and item.data(Qt.AccessibleTextRole)
            assert item.background().color()!=item.foreground().color()
            assert t.item(r,0).background().color()==item.background().color()
        t.sortItems(0,Qt.SortOrder.DescendingOrder)
    t.close();t.deleteLater()


def test_listes_dates_et_statuts_sur_donnees_sans_modification(app,monkeypatch):
    qs=[dict(devis(statut,expiration),id=i,numero=f'DEV-{i}',nom_client=f'Client {i}',objet='Prestation') for i,(statut,expiration) in enumerate([('envoye','2026-10-27'),('envoye','2026-10-01'),('accepte','2026-10-01'),('brouillon','2026-10-01')],1)]
    fs=[dict(facture(),id=1,numero='FACT-1',date_document='2026-10-01',instantane=json.dumps({'client':{'nom':'Client'}})),dict(facture(),id=2,numero='FACT-2',date_document='2026-10-01',instantane=json.dumps({'client':{'nom':'Client'}}))]
    fs[0]['echeance']='2026-10-01';fs[1]['paye']=1000
    avant=deepcopy((qs,fs))
    monkeypatch.setattr(ui.g,'aujourd_hui',lambda:JOUR);monkeypatch.setattr(ui.db,'lister_devis',lambda:qs)
    monkeypatch.setattr(ui.db,'obtenir_devis',lambda ident:next(q for q in qs if q['id']==ident))
    monkeypatch.setattr(ui.g,'documents',lambda:fs);monkeypatch.setattr(ui,'est_admin',lambda _:True)
    q=ui.QuotesPage();q.refresh();f=ui.InvoicesPage();f.refresh()
    assert q.table.columnCount()==6 and f.table.columnCount()==8
    assert {q.table.item(r,5).text() for r in range(4)}=={'En cours','Hors délai','Accepté','Brouillon'}
    assert {f.table.item(r,7).text() for r in range(2)}=={'En retard','Réglée'}
    q.recherche.setText('Client 3');assert q.table.rowCount()==1 and q.table.item(0,5).text()=='Accepté'
    f.recherche.setText('FACT-2');assert f.table.rowCount()==1 and f.table.item(0,7).text()=='Réglée'
    assert (qs,fs)==avant
    q.close();f.close();q.deleteLater();f.deleteLater()
