# SPDX-License-Identifier: GPL-3.0-or-later
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import base64,json
from datetime import datetime,timezone,timedelta,date
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from licences_pro import verifier,LicencePro,json_unique
from finances_calculs import synthese,lignes_valides,evenements
import database as db,gestion as g,coffre
from finances_pro import FinancesPro

NOW=datetime(2026,10,13,tzinfo=timezone.utc)
@pytest.fixture
def licence():
    key=Ed25519PrivateKey.generate();pub=base64.b64encode(key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode()
    def signe(**changements):
        p={'schema':'ska-license-v1','app_id':'patenteasy','license_id':'L-TEST','customer_id':'C-TEST','customer_name':'Entreprise','features':['finance_tva','administratif'],'limits':{'employees':1,'sites':1},'issued_at':NOW.isoformat(),'not_before':NOW.isoformat(),'expires_at':(NOW+timedelta(days=365)).isoformat()};p.update(changements)
        return {'payload':p,'signature':base64.urlsafe_b64encode(key.sign(json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())).decode().rstrip('=')}
    return pub,signe

def test_signature_et_expiration(licence):
    pub,signe=licence;s=signe()
    assert verifier(s,pub,'Entreprise',maintenant=NOW)['modules']==['finance_tva','administratif']
    assert not verifier(s,pub,'Entreprise',maintenant=NOW+timedelta(days=365))['active']
    assert not verifier(s,pub,'Autre société',maintenant=NOW)['active']
    assert not verifier(signe(app_id='autre'),pub,'Entreprise',maintenant=NOW)['active']
    assert not verifier(s,'','Entreprise',maintenant=NOW)['active']
    s['payload']['features'].append('autre');assert not verifier(s,pub,'Entreprise',maintenant=NOW)['active']

def test_mauvaise_cle_et_dates(licence):
    pub,signe=licence
    other=base64.b64encode(Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode()
    assert not verifier(signe(),other,'Entreprise',maintenant=NOW)['active']
    assert not verifier(signe(not_before=(NOW+timedelta(days=1)).isoformat()),pub,'Entreprise',maintenant=NOW)['active']
    assert not verifier(signe(),pub,'Entreprise',maintenant=NOW,dernier=(NOW+timedelta(hours=1)).isoformat())['active']
    with pytest.raises(ValueError):json_unique('{"payload":{},"payload":{}}')

def document(nature='service',livraison='',paiements=None):
    return {'date':'2026-10-01','ttc':11600,'livraison':livraison,'lignes':[{'ht':10000,'tva':1600,'taux':1600,'nature':nature}], 'paiements':paiements or [{'date':'2026-10-02','montant':5800},{'date':'2026-11-02','montant':5800}]}

def test_encaissements_partiels_et_arrondis():
    d=document();a=synthese('2026-10-01','2026-10-31',[d],[],'reel');b=synthese('2026-11-01','2026-11-30',[d],[],'reel')
    assert a['tva_percue']==a['tva_exigible']==800 and b['tva_exigible']==800
    d['paiements']=[{'date':'2026-10-01','montant':1},{'date':'2026-10-02','montant':2},{'date':'2026-10-03','montant':11597}]
    assert sum(e['tva'] for e in evenements(d['lignes'],11600,d['paiements'],d['date'],''))==1600

def test_livraison_et_debits():
    d=document('bien','2026-10-15');s=synthese('2026-10-01','2026-10-31',[d],[],'reel')
    assert s['tva_exigible']==1600 and s['tva_percue']==800
    d=document('bien','2026-11-15');assert synthese('2026-10-01','2026-10-31',[d],[],'reel')['tva_exigible']==800
    assert synthese('2026-10-01','2026-10-31',[document('debits')],[],'reel')['tva_exigible']==1600

def test_franchise_deduction_et_taux():
    a={'date':'2026-10-01','livraison':'2026-10-01','ttc':16600,'justificatif':True,'paiements':[],'lignes':lignes_valides([{'ht':10000,'taux':1600,'nature':'bien'},{'ht':5000,'taux':0,'nature':'bien'}])}
    s=synthese('2026-10-01','2026-10-31',[document()], [a],'franchise');assert s['tva_deductible']==s['a_reverser']==s['tva_percue']==0
    s=synthese('2026-10-01','2026-10-31',[],[a],'reel');assert s['tva_deductible']==1600 and s['credit']==1600 and len(s['taux'])==2
    a['justificatif']=False;assert synthese('2026-10-01','2026-10-31',[],[a],'reel')['tva_deductible']==0

@pytest.fixture
def service(tmp_path,monkeypatch,licence):
    coffre.ACTIF=None;monkeypatch.setattr(db,'DB_PATH',tmp_path/'base.db');monkeypatch.setattr(db,'DATA_DIR',tmp_path);g.migrer();db.modifier_entreprise('Entreprise','','','','','','')
    pub,signe=licence;clock=[NOW]
    l=LicencePro(db.base,config={'cle_publique_ed25519':pub},horloge=lambda:clock[0],autoriser=lambda:None)
    l.importer(json.dumps(signe()));yield FinancesPro(db.base,l),clock,signe
    coffre.ACTIF=None

def test_reglements_fournisseurs_sans_doublon(service):
    s,clock,_=service
    a={'date':'2026-10-01','livraison':'','fournisseur':'Fournisseur','reference':'ACH-1','justificatif':True,'lignes':[{'ht':10000,'taux':1600,'nature':'service'}]}
    ident=s.ajouter_achat(a,5800,'2026-10-02');s.payer_achat(ident,'2026-10-03',5800)
    assert s.achats()[0]['reste']==0
    with db.base.session() as c:
        assert c.execute('SELECT COUNT(*) FROM operations').fetchone()[0]==2
        operation=c.execute('SELECT id FROM operations LIMIT 1').fetchone()[0]
    with pytest.raises(ValueError):s.payer_achat(ident,'2026-10-03',1)
    with pytest.raises(ValueError):db.supprimer_operation(operation)
    assert s.calculer('2026-10-01','2026-10-31','reel')['tva_deductible']==1600

def test_expiration_bloque_sans_effacer(service):
    s,clock,_=service;clock[0]=NOW+timedelta(days=365)
    with pytest.raises(PermissionError):s.achats()
    with pytest.raises(PermissionError):s.calculer('2026-10-01','2026-10-31','reel')
    assert db.obtenir_entreprise()['nom']=='Entreprise'

def test_horloge_monotone_et_reimport(service):
    s,clock,signe=service;clock[0]=NOW+timedelta(hours=1);assert s.licence.etat()['active']
    clock[0]-=timedelta(minutes=4);assert s.licence.etat()['active']
    clock[0]-=timedelta(minutes=4);assert not s.licence.etat()['active']
    with pytest.raises(ValueError):s.licence.importer(json.dumps(signe()))

def test_ecrans_et_verrouillage(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication
    import finances_ui
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'base.db');monkeypatch.setattr(db,'DATA_DIR',tmp_path);coffre.ACTIF=None;g.migrer()
    for cls in [finances_ui.LicencePage,finances_ui.FinancesPage,finances_ui.AdministratifPage]:
        page=cls();page.refresh()
        if hasattr(page,'actions_pro'):assert all(not a.isEnabled() for a in page.actions_pro)
        page.close()

def test_facture_auto_recettes_et_pdf(service,tmp_path):
    s,_,_=service
    g.regler_region('PF','XPF',0,'dd/MM/yy','fr','TVA','','N° TAHITI')
    client=db.ajouter_client('Client');j=date.today().isoformat();devis=g.creer_devis(client,j,'Test licence')
    db.ajouter_ligne_devis(devis,'Service','heure','1','10000','16');g.confirmer_fiscalite(int(j[:4]),'reel',ca='12000000');g.emettre_devis(devis);g.decision_devis(devis,'accepte');facture=g.creer_facture(devis,j,j)
    s.qualifier(facture,['service'])
    g.payer(facture,j,'5800','virement','TEST')
    result=s.calculer(j,j,'reel');assert result['tva_percue']==result['tva_exigible']==800
    with db.base.session() as c:assert c.execute("SELECT COUNT(*) FROM operations WHERE type_operation='recette'").fetchone()[0]==1
    s.enregistrer_profil({'fiscal':'it','dn_cps':'TEST'})
    ident,dossier=s.preparer('tva1010',j,j,j,'https://www.service-public.pf/dicp/','reel')
    from finances_pdf import exporter_preparation
    fichier=tmp_path/'preparation.pdf';exporter_preparation(s,ident,fichier);assert fichier.read_bytes().startswith(b'%PDF')
    assert dossier['recettes_ttc']==5800

def test_rapprochement_et_part_deductible(service):
    s,_,_=service
    with db.base.session() as c:op=c.execute("INSERT INTO operations(date_operation,libelle,type_operation,montant_centiemes) VALUES('2026-10-02','Ancien règlement','depense',5800)").lastrowid
    achat={'date':'2026-10-01','livraison':'','fournisseur':'F','reference':'OLD','justificatif':True,'lignes':[{'ht':10000,'taux':1600,'nature':'service','deduction':5000}]}
    s.ajouter_achat(achat,operation_existante=op)
    assert s.calculer('2026-10-01','2026-10-31','reel')['tva_deductible']==400
    with db.base.session() as c:assert c.execute('SELECT COUNT(*) FROM operations').fetchone()[0]==1
    with pytest.raises(ValueError):s.ajouter_achat(achat,operation_existante=op)
