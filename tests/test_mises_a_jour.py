# SPDX-License-Identifier: GPL-3.0-or-later
import base64,json,hashlib
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
import mises_a_jour as m

def test_versions_correctives_quatre_nombres():
    assert m.version('0.4.5') < m.version('0.4.5.1') < m.version('0.4.6')
    assert m.version('0.4.5.1') < m.version('0.4.5.10')
    assert m.version('0.4.5') == m.version('0.4.5.0')
    for invalide in ('0.4', '0.4.5.1.2', '0.4.5-beta', '0.4.-5', '0.4.5.'):
        with pytest.raises(ValueError):
            m.version(invalide)

def test_catalogue_authentique_et_modification_refusee():
    cle=Ed25519PrivateKey.generate();pub=base64.b64encode(cle.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
    versions={'windows':{'version':'99.0.0','url':'https://example.org/installer.exe','sha256':'a'*64,'taille':123,'notes':'Test'}}
    enveloppe={'versions':versions,'signature':base64.b64encode(cle.sign(json.dumps(versions,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())).decode()}
    assert m.valider(enveloppe,pub,'windows')['nouvelle']
    versions['windows']['url']='https://example.org/autre.exe'
    with pytest.raises(InvalidSignature):m.valider(enveloppe,pub,'windows')


def test_telechargement_corrompu_refuse(tmp_path,monkeypatch):
    import io
    monkeypatch.setattr(m,'ouvrir_https',lambda *a,**kw:io.BytesIO(b'alteration'))
    r={'version':'99.0.0','url':'https://example.org/installer.exe','sha256':hashlib.sha256(b'original').hexdigest(),'taille':10}
    with pytest.raises(ValueError):m.telecharger(r,tmp_path)
    assert list(tmp_path.iterdir())==[]


def test_redirection_http_refusee():
    from urllib.request import Request
    with pytest.raises(ValueError):
        m.RedirectionsHTTPS().redirect_request(Request('https://example.org'),None,302,'',{},'http://example.org/fichier.exe')
