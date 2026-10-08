# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import datetime,timedelta
from types import SimpleNamespace
import json
import pytest
import beta_fonctions as bf

class Comptes:
    def __init__(self,role='admin'):self.role=role
    def exiger_admin(self):
        if self.role!='admin':raise PermissionError('Administrateur requis')
    def tracer(self,*args):pass

def test_csv_exact_et_cellules_protegees(tmp_path,monkeypatch):
    monkeypatch.setattr(bf.db,'lister_operations',lambda annee:[{'date_operation':'2026-10-01','libelle':'=HYPERLINK("test")\nligne','type_operation':'depense','montant_centiemes':12345}])
    s=bf.ServicesBeta(Comptes(),None);p=s.exporter_csv(2026,tmp_path/'operations.csv');texte=p.read_text(encoding='utf-8-sig');assert '123,45' in texte;assert "'=HYPERLINK" in texte
    with pytest.raises(PermissionError):bf.ServicesBeta(Comptes('utilisateur'),None).exporter_csv(2026,tmp_path/'interdit.csv')

def test_relance_sans_envoi_et_reste_exact(monkeypatch):
    monkeypatch.setattr(bf.g,'document',lambda ident:{'type':'facture','reste':250000,'numero':'fact-00001','echeance':'2026-10-20','contenu':{'client':{'nom':'Jean','email':'jean@example.org'},'entreprise':{'nom':'Atelier'}}})
    email,body,lien=bf.ServicesBeta(Comptes(),None).relance(1);assert email=='jean@example.org';assert '2 500 XPF' in body;assert 'arrivée' not in body;assert lien.startswith('mailto:')
    with pytest.raises(PermissionError):bf.ServicesBeta(Comptes('utilisateur'),None).relance(1)

def test_alerte_et_sauvegarde_recente(tmp_path):
    config={'dossier':'','derniere':''};s=bf.ServicesBeta(Comptes(),SimpleNamespace(configuration=lambda:config))
    assert s.etat_sauvegarde();config.update(dossier=str(tmp_path),derniere=datetime.now().isoformat());assert not s.etat_sauvegarde()
    config['derniere']=(datetime.now()-timedelta(days=3)).isoformat();assert s.etat_sauvegarde()
    config['derniere']=datetime.now().isoformat();config['erreur']='échec';assert s.etat_sauvegarde()
