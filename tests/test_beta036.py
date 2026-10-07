# SPDX-License-Identifier: GPL-3.0-or-later
import json
import sqlite3
import hashlib
from pathlib import Path
import pytest
import coffre
from database import BaseDonnees
from comptes import GestionComptes
from sauvegardes import GestionSauvegardes

@pytest.fixture
def comptes(tmp_path):
    coffre.ACTIF=None
    c=GestionComptes(BaseDonnees(tmp_path/'data'/'base.db'))
    c.creer_premier_admin('proprietaire','une phrase administrateur')
    connexion=c.coffre.ouvrir()
    connexion.execute('CREATE TABLE secret (contenu TEXT)');connexion.execute('INSERT INTO secret VALUES (?)',('client confidentiel et chiffre annuel',));connexion.commit();connexion.close()
    yield c
    c.coffre.verrouiller()

def test_base_chiffree_et_verrouillage(comptes):
    assert b'client confidentiel' not in comptes.base.chemin.read_bytes()
    with pytest.raises(sqlite3.DatabaseError):sqlite3.connect(comptes.base.chemin).execute('SELECT * FROM secret').fetchall()
    comptes.coffre.verrouiller()
    with pytest.raises(PermissionError):comptes.coffre.ouvrir()
    assert comptes.authentifier('proprietaire','incorrect') is None
    assert comptes.authentifier('PROPRIETAIRE','une phrase administrateur')['role']=='admin'

def test_admin_seul_cree_et_desactive(comptes):
    comptes.creer_utilisateur('employe','une phrase utilisateur')
    ident=comptes.lister()[1]['id'];comptes.basculer_actif(ident)
    assert comptes.authentifier('employe','une phrase utilisateur') is None
    comptes.basculer_actif(ident);assert comptes.authentifier('employe','une phrase utilisateur')
    with pytest.raises(PermissionError):comptes.creer_utilisateur('autre','une phrase utilisateur')
    with pytest.raises(PermissionError):comptes.lister()

def test_mot_de_passe_change_sans_rechiffrer(comptes):
    original=comptes.base.chemin.read_bytes()
    with pytest.raises(ValueError):comptes.changer_mot_de_passe('incorrect','une phrase nouvelle')
    comptes.changer_mot_de_passe('une phrase administrateur','une phrase nouvelle')
    assert comptes.authentifier('proprietaire','une phrase administrateur') is None
    assert comptes.authentifier('proprietaire','une phrase nouvelle')
    assert comptes.coffre.ouvrir().execute('SELECT contenu FROM secret').fetchone()[0].startswith('client')

def test_recuperation_et_rotation(comptes):
    code=comptes.coffre.code_recuperation
    with pytest.raises(ValueError):comptes.recuperer('incorrect','une phrase nouvelle')
    comptes.recuperer(code,'une phrase nouvelle')
    with pytest.raises(ValueError):comptes.recuperer(code,'encore une phrase nouvelle')
    assert comptes.authentifier('proprietaire','une phrase nouvelle')

def test_blocage_apres_cinq_erreurs(comptes):
    for _ in range(5):assert comptes.authentifier('proprietaire','incorrect') is None
    assert comptes.authentifier('proprietaire','une phrase administrateur') is None

def test_sauvegarde_chiffree_et_restauration(comptes,tmp_path):
    s=GestionSauvegardes(comptes);s.configurer(tmp_path/'copies');p=s.creer()
    assert b'client confidentiel' not in p.read_bytes()
    c=comptes.coffre.ouvrir();c.execute('DELETE FROM secret');c.commit();c.close()
    s.restaurer(p)
    c=comptes.coffre.ouvrir();assert c.execute('SELECT COUNT(*) FROM secret').fetchone()[0]==1;c.close()
    assert list((tmp_path/'copies').glob('*avant-restauration.pebackup'))

def test_corruption_ne_modifie_pas_base(comptes,tmp_path):
    s=GestionSauvegardes(comptes);s.configurer(tmp_path/'copies');p=s.creer();b=bytearray(p.read_bytes());b[-1]^=1;p.write_bytes(b)
    avant=comptes.base.chemin.read_bytes()
    with pytest.raises(ValueError):s.restaurer(p)
    assert comptes.base.chemin.read_bytes()==avant

def test_user_sauvegarde_mais_ne_restaure_pas(comptes,tmp_path):
    s=GestionSauvegardes(comptes);s.configurer(tmp_path/'copies');comptes.creer_utilisateur('employe','une phrase utilisateur');comptes.authentifier('employe','une phrase utilisateur')
    p=s.creer()
    with pytest.raises(PermissionError):s.restaurer(p)
    with pytest.raises(PermissionError):s.configurer(tmp_path/'autre')

def test_migration_preserve_ancien_compte_et_donnees(tmp_path):
    coffre.ACTIF=None;p=tmp_path/'legacy.db';sel=b'12345678901234567890123456789012';secret='ancien mot de passe';empreinte=hashlib.pbkdf2_hmac('sha256',secret.encode(),sel,600000)
    with sqlite3.connect(p) as c:
        c.execute('CREATE TABLE comptes (id INTEGER,identifiant TEXT,role TEXT,sel BLOB,empreinte BLOB,iterations INTEGER,actif INTEGER,echecs INTEGER,bloque_jusqua REAL)')
        c.execute('INSERT INTO comptes VALUES (1,?,?,?,?,?,1,0,0)',('ancien','admin',sel,empreinte,600000))
        c.execute('CREATE TABLE secret (contenu TEXT)');c.execute("INSERT INTO secret VALUES ('ancien client')")
    comptes=GestionComptes(BaseDonnees(p));assert not comptes.premier_compte_requis();assert comptes.authentifier('ancien',secret)
    assert b'ancien client' not in p.read_bytes()
    c=comptes.coffre.ouvrir();assert c.execute('SELECT contenu FROM secret').fetchone()[0]=='ancien client';c.close();comptes.coffre.verrouiller()


def test_role_modifie_ne_deverrouille_pas(comptes):
    comptes.creer_utilisateur('employe','une phrase utilisateur')
    m=comptes.coffre.lire();m['comptes'][1]['role']='admin'
    coffre.ecrire_json(comptes.coffre.metadata,m)
    assert comptes.authentifier('employe','une phrase utilisateur') is None
