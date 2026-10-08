# SPDX-License-Identifier: GPL-3.0-or-later
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import io,json,zipfile
import pytest
import database as db
import gestion as g
import coffre
import regional
from comptes import GestionComptes
from sauvegardes import GestionSauvegardes, MAGIC as V1
import sauvegarde_portable as portable
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
import qt_app as ui

@pytest.fixture
def base(tmp_path,monkeypatch):
    coffre.ACTIF=None
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'base.db')
    monkeypatch.setattr(db,'DATA_DIR',tmp_path)
    g.migrer()
    yield tmp_path
    if coffre.ACTIF:coffre.ACTIF.verrouiller()
    coffre.ACTIF=None

@pytest.fixture
def app():return QApplication.instance() or QApplication([])

def devis():
    db.modifier_entreprise('Business','','','','','','')
    c=db.ajouter_client('Customer')
    return g.creer_devis(c,'2026-10-08','Subject')

@pytest.mark.parametrize('devise,precision,prix,total',[('JPY',0,'1000',1000),('KWD',3,'1.234',1234),('CLF',4,'1.2345',12345)])
def test_precision_et_document_fige(base,devise,precision,prix,total):
    g.regler_region('US',devise,precision,'MM/dd/yy','en','Sales tax','','Business ID')
    d=devis();db.ajouter_ligne_devis(d,'Item','unit','1',prix,'10')
    g.confirmer_fiscalite(2026,'reel',ca='12000000')
    assert g.calculer(d)['ht']==total
    assert not g.rappel_seuil_ca(2026)
    with pytest.raises(ValueError,match='déjà utilisée'):g.regler_region('US','EUR',2,'MM/dd/yy','en','Tax','','ID')
    g.emettre_devis(d);snap=g.calculer(d)
    assert snap['entreprise']['devise']==devise
    g.regler_region('JP',devise,precision,'dd/MM/yy','fr','Autre taxe','','ID')
    assert g.calculer(d)==snap
    from pdf_documents import generer
    assert generer(snap).startswith(b'%PDF')


def test_general_sans_identifiant_ni_choix_fiscal(base):
    assert regional.configuration()['pays']==''
    d=devis();db.ajouter_ligne_devis(d,'Service','unit','1','10','16')
    g.emettre_devis(d)
    assert g.calculer(d)['tva']==0
    g.decision_devis(d,'accepte')
    f=g.creer_facture(d,'2026-10-08','2026-10-15')
    assert f


def test_migration_ancien_profil_preserve_montants(base):
    # The legacy schema has XPF, but no generic regional columns.
    with g.connexion() as c:
        for champ in regional.DEFAULTS:c.execute(f'ALTER TABLE entreprise DROP COLUMN {champ}')
    g.migrer()
    e=db.obtenir_entreprise()
    assert (e['pays'],e['devise'],e['decimales'],e['libelle_identifiant'])==('PF','XPF',2,'N° TAHITI')
    assert db.convertir_montant('1000')==100000


@pytest.mark.parametrize('fmt,chiffres,iso',[('MM/dd/yy','100826','2026-10-08'),('yyyy-MM-dd','20261008','2026-10-08')])
def test_separateurs_formats(base,app,fmt,chiffres,iso):
    g.regler_region('US','USD',2,fmt,'en','Tax','','ID')
    date=ui.make_date('2026-01-01');date.entry.selectAll();QTest.keyClicks(date.entry,chiffres)
    assert ui.iso_date(date)==iso


def test_brouillon_survit_aux_lignes_et_fermeture(base,app):
    d=devis();window=ui.QuoteEditorDialog(d)
    window.objet.setText('Unsaved customer subject')
    window.vente.setPlainText('Custom notes')
    window.date.entry.selectAll();QTest.keyClicks(window.date.entry,'0810')
    assert window.save_header(quiet=True,refresh=False)
    db.ajouter_ligne_devis(d,'Item','unit','1','10','0');window.refresh(keep_header=True)
    assert window.objet.text()=='Unsaved customer subject'
    window.close();again=ui.QuoteEditorDialog(d)
    assert again.objet.text()=='Unsaved customer subject' and again.vente.toPlainText()=='Custom notes'
    assert g.lire_brouillon_ui(d)
    again.date.entry.selectAll();QTest.keyClicks(again.date.entry,'081026')
    assert again.save_header(refresh=False)
    assert db.obtenir_devis(d)['objet']=='Unsaved customer subject'
    assert g.lire_brouillon_ui(d) is None
    again.close()


def backup(tmp_path):
    owner=GestionComptes(db.BaseDonnees(tmp_path/'old'/'base.db'))
    owner.creer_premier_admin('owner','administrator password')
    c=owner.coffre.ouvrir();c.execute('CREATE TABLE secret (value TEXT)');c.execute("INSERT INTO secret VALUES ('business secret')");c.commit();c.close()
    owner.creer_utilisateur('employee','employee password')
    s=GestionSauvegardes(owner);s.configurer(tmp_path/'backups');p=s.creer()
    return owner,p

@pytest.mark.parametrize('mode',['mot_de_passe','code'])
def test_sauvegarde_autonome_sur_nouveau_pc(tmp_path,mode):
    owner,p=backup(tmp_path);code=owner.coffre.code_recuperation
    assert p.read_bytes().startswith(portable.MAGIC)
    assert b'business secret' not in p.read_bytes()
    with pytest.raises(ValueError):portable.preparer(p,'employee password')
    owner.coffre.verrouiller();coffre.ACTIF=None
    preparation=portable.preparer(p,code if mode=='code' else 'administrator password',mode)
    recovered=GestionComptes(db.BaseDonnees(tmp_path/'new'/'base.db'))
    recovered.restaurer_nouveau_pc(preparation,'new administrator password' if mode=='code' else None,code)
    c=recovered.coffre.ouvrir();assert c.execute('SELECT value FROM secret').fetchone()[0]=='business secret';c.close()
    assert recovered.coffre.lire()['sauvegardes']['dossier']==''
    assert recovered.authentifier('owner','new administrator password' if mode=='code' else 'administrator password')
    recovered.coffre.verrouiller();coffre.ACTIF=None


def test_ancienne_sauvegarde_et_corruption(tmp_path):
    owner,p=backup(tmp_path)
    data=p.read_bytes();bad=tmp_path/'bad.pebackup';bad.write_bytes(data[:-1]+bytes([data[-1]^1]))
    with pytest.raises(ValueError):portable.preparer(bad,'administrator password')
    prep=portable.preparer(p,'administrator password')
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr('base.db',prep['base']);z.writestr('acces.json',json.dumps(prep['metadata']))
    nonce=os.urandom(12);old=tmp_path/'old.pebackup';old.write_bytes(V1+nonce+AESGCM(prep['cle']).encrypt(nonce,stream.getvalue(),V1))
    with pytest.raises(ValueError,match='acces.json'):portable.preparer(old,'administrator password')
    assert portable.preparer(old,'administrator password',ancien_acces=owner.coffre.metadata)['base']==prep['base']
    new=GestionComptes(db.BaseDonnees(tmp_path/'new'/'base.db'))
    with pytest.raises(ValueError):new.restaurer_nouveau_pc(prep,'new administrator password','wrong-code')
    assert not new.base.chemin.exists() and not new.coffre.metadata.exists()
    owner.coffre.verrouiller();coffre.ACTIF=None
