# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from database import BaseDonnees
from gestion import GestionDocuments
from editeur import ConfigurationEditeur
import json

def test_bases_isolees_et_parcours_vide(tmp_path):
    a=BaseDonnees(tmp_path/'a.db');b=BaseDonnees(tmp_path/'b.db')
    GestionDocuments(a).migrer();GestionDocuments(b).migrer()
    a.ajouter_client('Premier')
    assert len(a.lister_clients())==1
    assert b.lister_clients()==[]
    assert GestionDocuments(b).documents()==[]
    assert b.obtenir_entreprise()['nom']==''

def test_liens_drive_paypal_et_persistance(tmp_path):
    source=tmp_path/'configuration.json';source.write_text(json.dumps({'paypal_url':'','telechargements_url':''}))
    editeur=ConfigurationEditeur(source,tmp_path/'local.json')
    drive='https://drive.proton.me/urls/public#fragment-secret-du-lien'
    paypal='https://www.paypal.com/ncp/payment/A3ELC2Q8GM82N'
    editeur.enregistrer(drive,paypal)
    assert editeur.lire()['telechargements_url']==drive
    assert json.loads(source.read_text())['telechargements_url']==''
    for mauvais in ['https://drive.proton.me.evil.org/','http://drive.proton.me/','https://x@drive.proton.me/']:
        with pytest.raises(ValueError):editeur.enregistrer(mauvais,paypal)
