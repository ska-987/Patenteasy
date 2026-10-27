import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import hashlib
from pathlib import Path
import pytest
import coffre
import database as db
import gestion as g
from finances_pro import FinancesPro
from donnees_test import copier
from PySide6.QtWidgets import QApplication

class Droits:
    def exiger(self,module):return {'active':True}

@pytest.fixture
def base(tmp_path,monkeypatch):
    coffre.ACTIF=None
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'patenteeasy.db');monkeypatch.setattr(db,'DATA_DIR',tmp_path)
    g.migrer();g.regler_region('PF','XPF',0,'dd/MM/yy','fr','TVA','','N° Tahiti')
    db.modifier_entreprise('Atelier test','','','','','','');g.confirmer_fiscalite(g.aujourd_hui().year,'franchise')
    client=db.ajouter_client('Client');j=g.aujourd_hui().isoformat()
    b=g.creer_brouillon_facture(client,j,'Vente');db.ajouter_ligne_devis(b,'Prestation','unité','1','1000','0')
    f=g.emettre_facture_directe(b,j,j)
    return f,j,FinancesPro(db.base,Droits())

@pytest.fixture
def app():return QApplication.instance() or QApplication([])

def test_banques_reglement_historique_et_journal(base):
    f,j,s=base;instantane=g.document(f)['instantane']
    g.enregistrer_banques([' Socredo ','socredo','Banque de Tahiti'])
    assert g.banques()==['Socredo','Banque de Tahiti']
    g.payer(f,j,'300','virement','VIR-123','Socredo')
    p=g.document(f)['paiements'][0]
    assert p['banque']=='Socredo' and p['reference']=='VIR-123'
    operation=db.obtenir_operation(p['operation_id'])
    assert operation['banque']=='Socredo' and 'VIR-123' in operation['libelle'] and g.document(f)['numero'] in operation['libelle']
    g.enregistrer_banques(['Banque de Tahiti'])
    assert g.document(f)['paiements'][0]['banque']=='Socredo'
    assert g.document(f)['instantane']==instantane
    assert g.document(f)['reste']==700

@pytest.mark.parametrize('mode,banque',[('virement','Inconnue'),('especes','Socredo')])
def test_banque_invalide_pas_de_paiement(base,mode,banque):
    f,j,s=base;g.enregistrer_banques(['Socredo'])
    with pytest.raises(ValueError):g.payer(f,j,'100',mode,'',banque)
    assert g.document(f)['reste']==1000 and not g.document(f)['paiements']

def test_franchise_ttc_pas_tva_et_pas_faux_double_compte(base):
    f,j,s=base;g.payer(f,j,'500','virement','')
    a=s.ajouter_achat({'date':j,'livraison':'','fournisseur':'Fournisseur','reference':'ACH1','justificatif':True,'lignes':[{'ht':100,'tva':16,'ttc':116,'taux':1600,'nature':'service'}]})
    g.enregistrer_banques(['Socredo']);s.payer_achat(a,j,116,'cheque','Socredo','CHQ88')
    r=s.calculer(j,j,'franchise',999)
    assert (r['recettes_ttc'],r['depenses_ttc'],r['solde_periode'])==(500,116,384)
    assert all(r[k]==0 for k in ('tva_percue','tva_exigible','tva_deductible','a_reverser','credit','credit_precedent'))
    assert r['taux']==[] and r['alertes']==[]
    assert db.lister_operations(g.aujourd_hui().year)[0]['banque']=='Socredo'
    assert s.calculer(j,j,'reel')['tva_deductible']==16


def test_franchise_interface_ttc_et_recherche_banque(base,app,monkeypatch):
    from finances_ui import FinancesPage,AchatDialog
    from licences_pro import LicencePro
    import qt_app as ui
    monkeypatch.setattr(LicencePro,'etat',lambda _:dict(active=True,modules=['finance_tva'],message='Test'))
    monkeypatch.setattr(LicencePro,'exiger',lambda *a:dict(active=True))
    f,j,s=base;g.enregistrer_banques(['Socredo']);g.payer(f,j,'100','cheque','CHQ99','Socredo')
    p=FinancesPage();p.calculer()
    assert p.regime.currentData()=='franchise' and p.taux.isHidden() and p.credit.isHidden()
    assert 'Montants TTC' in p.resume.text() and 'À reverser' not in p.resume.text()
    d=AchatDialog(franchise=True);d.fournisseur.setText('Fournisseur');d.reference.setText('F1');d.table.item(0,4).setText('116')
    achat,_,_=d.donnees();assert achat['lignes'][0]['ttc']==116 and achat['lignes'][0]['tva']==0 and achat['lignes'][0]['deduction']==0
    capture=os.environ.get('PATENTEASY_DEV_SCREENSHOT')
    if capture:
        p.resize(1100,700);p.show();app.processEvents();p.grab().save(capture)
    journal=ui.JournalPage();journal.refresh();journal.banque_filtre.setCurrentIndex(journal.banque_filtre.findData('Socredo'));journal.recherche.setText('CHQ99')
    assert journal.table.rowCount()==1 and journal.table.item(0,4).text()=='Socredo'
    journal.recherche.setText('INCONNU');assert journal.table.rowCount()==0
    for w in (p,d,journal):w.close();w.deleteLater()


def test_copie_chiffree_identifiants_et_source_inchangee(tmp_path):
    from comptes import GestionComptes
    source=tmp_path/'production'/'data';source.mkdir(parents=True)
    origine=coffre.Coffre(source/'patenteeasy.db');origine.creer('mika','MotDePasse-De-Test!')
    b=db.BaseDonnees(origine.chemin);g.GestionDocuments(b).migrer();b.modifier_entreprise('Entreprise réelle','','','','','','')
    metadata=json.loads(origine.metadata.read_text());metadata['sauvegardes']['dossier']=str(tmp_path/'vraies-sauvegardes');origine.metadata.write_text(json.dumps(metadata))
    origine.verrouiller()
    avant={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in source.iterdir()}
    dest=tmp_path/'dev'/'data';copier(source,dest)
    assert {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in source.iterdir()}==avant
    assert (dest/'patenteeasy.db').read_bytes()==(source/'patenteeasy.db').read_bytes()
    assert json.loads((dest/'acces.json').read_text())['sauvegardes']['dossier']==str(dest.parent/'sauvegardes')
    manager=GestionComptes(db.BaseDonnees(dest/'patenteeasy.db'));assert manager.authentifier('mika','MotDePasse-De-Test!')
    manager.base.modifier_entreprise('Entreprise TEST','','','','','','');manager.coffre.verrouiller()
    assert {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in source.iterdir()}==avant
    with pytest.raises(ValueError):copier(source,dest)


def test_copie_refuse_source_active_et_destination_production(tmp_path):
    s=tmp_path/'source';s.mkdir();(s/'patenteeasy.db').write_bytes(b'test')
    with pytest.raises(ValueError):copier(s,s)
    (s/'patenteeasy.db-wal').write_bytes(b'journal actif')
    with pytest.raises(ValueError):copier(s,tmp_path/'dev')
    assert not (tmp_path/'dev').exists() and (s/'patenteeasy.db').read_bytes()==b'test'


def test_ttc_reprise_mensuelle_sans_double_compte_ni_prorata_invente(base):
    f,j,s=base;annee=int(j[:4]);premier=f'{annee}-01-01';dernier=f'{annee}-01-31'
    with db.base.session() as c:
        c.execute('UPDATE entreprise SET date_debut_activite=? WHERE id=1',(premier,))
        c.execute('UPDATE fiscalite_annuelle SET date_fin_reprise=? WHERE annee=?',(dernier,annee))
        c.execute("INSERT INTO operations(date_operation,libelle,type_operation,montant_centiemes) VALUES(?,'Ancienne recette doublonnée','recette',900)",(premier,))
    db.enregistrer_reprise_mensuelle(annee,1,'400','100',True)
    r=s.calculer(premier,dernier,'franchise')
    assert (r['recettes_ttc'],r['depenses_ttc'])==(400,100)
    assert any('double compte' in a for a in r['alertes'])
    partiel=s.calculer(f'{annee}-01-15',f'{annee}-01-20','franchise')
    assert partiel['recettes_ttc']==partiel['depenses_ttc']==0
    assert any('partiellement' in a for a in partiel['alertes'])


def test_operation_manuelle_compte_et_colonnes(base,app):
    import qt_app as ui
    f,j,_=base
    db.enregistrer_debut_activite(j)
    g.enregistrer_banques(['Socredo'])
    d=ui.OperationDialog()
    assert d.banque.findData('Socredo')>=0
    d.date.setDate(ui.qdate_from_iso(j));d.libelle.setText('Achat test');d.montant.setText('100')
    d.type.setCurrentIndex(d.type.findData('depense'));d.banque.setCurrentIndex(d.banque.findData('Espèces / caisse'))
    ident=db.ajouter_operation(*d.values())
    assert db.obtenir_operation(ident)['banque']=='Espèces / caisse'
    modification=ui.OperationDialog(db.obtenir_operation(ident))
    assert modification.banque.currentData()=='Espèces / caisse'
    modification.banque.setCurrentIndex(modification.banque.findData('Socredo'))
    db.modifier_operation(ident,*modification.values())
    assert db.obtenir_operation(ident)['banque']=='Socredo'
    page=ui.JournalPage();page.refresh()
    ligne=next(r for r in range(page.table.rowCount()) if page.table.item(r,0).data(ui.Qt.UserRole)==ident)
    assert page.table.item(ligne,2).text()=='' and page.table.item(ligne,3).text()
    assert page.table.item(ligne,4).text()=='Socredo'
    for w in (d,modification,page):w.close();w.deleteLater()
