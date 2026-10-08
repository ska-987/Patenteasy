# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import io
import json
import pytest
from distribution import publier_automatique as module


class Absent(Exception):
    response={'Error':{'Code':'NoSuchKey'}}


class R2:
    def __init__(self):self.objets={'catalogue.json':b'ancien'};self.ecritures=[]
    def get_object(self,**args):
        if args['Key'] not in self.objets:raise Absent()
        return {'Body':io.BytesIO(self.objets[args['Key']])}
    def put_object(self,**args):
        contenu=args['Body'];self.objets[args['Key']]=contenu.read() if hasattr(contenu,'read') else contenu
        self.ecritures.append(args['Key'])


def preparer(tmp_path,monkeypatch):
    versions={}
    for plateforme,nom,contenu in [('windows','windows.exe',b'MZ-installer'),('android','android.apk',b'APK-signee')]:
        (tmp_path/nom).write_bytes(contenu)
        versions[plateforme]={'url':'https://updates.example/fichiers/'+nom,'taille':len(contenu),'sha256':hashlib.sha256(contenu).hexdigest()}
    fichier=tmp_path/'catalogue.json';fichier.write_text(json.dumps({'versions':versions,'signature':'test'}))
    monkeypatch.setattr(module.publication,'preparer',lambda dossier:fichier)
    monkeypatch.setattr(module.publication,'ROOT',tmp_path)
    (tmp_path/'configuration_editeur.json').write_text(json.dumps({'catalogue_mises_a_jour':'https://updates.example/catalogue.json'}))
    monkeypatch.setattr(module.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(fichier.read_bytes()))
    return R2()


def test_catalogue_envoye_seulement_apres_les_deux_telechargements(tmp_path,monkeypatch):
    client=preparer(tmp_path,monkeypatch);lectures=[]
    module.publier(tmp_path,client,lambda url,version:lectures.append((url,list(client.ecritures))))
    assert client.ecritures==['windows.exe','android.apk','catalogue.json']
    assert len(lectures)==2
    assert all('catalogue.json' not in etapes for _,etapes in lectures)


def test_echec_telechargement_conserve_ancien_catalogue(tmp_path,monkeypatch):
    client=preparer(tmp_path,monkeypatch)
    def echec(url,version):raise ValueError('Réponse publique incorrecte')
    with pytest.raises(ValueError):module.publier(tmp_path,client,echec)
    assert client.objets['catalogue.json']==b'ancien'
    assert 'catalogue.json' not in client.ecritures


def test_version_deja_publiee_ne_peut_pas_etre_ecrasee(tmp_path,monkeypatch):
    client=preparer(tmp_path,monkeypatch);client.objets['android.apk']=b'autre APK'
    with pytest.raises(ValueError,match='existe déjà'):module.publier(tmp_path,client,lambda *a:None)
    assert client.ecritures==[]
    assert client.objets['catalogue.json']==b'ancien'
