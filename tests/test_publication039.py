# SPDX-License-Identifier: GPL-3.0-or-later
import base64
import hashlib
import json
from pathlib import Path
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import publication_release as publication
from mises_a_jour import valider
from version import VERSION


def test_catalogue_signe_et_installateur_modifie_refuse(tmp_path, monkeypatch):
    key = Ed25519PrivateKey.generate()
    public = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    (tmp_path/'configuration_editeur.json').write_text(json.dumps({'cle_publique_mises_a_jour':public,'catalogue_mises_a_jour':'https://updates.example/catalogue.json'}))
    secret = tmp_path/'ska_987'/'signature-patenteasy'/'cle-privee.pem'
    secret.parent.mkdir(parents=True)
    secret.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.setattr(publication, 'ROOT', tmp_path)
    exe=tmp_path/f'Patenteasy-Windows-{VERSION}-Installation.exe'
    exe.write_bytes(b'MZ-test-integration')
    manifest={'version':VERSION,'taille':exe.stat().st_size,'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
    (tmp_path/'version-verifiee.json').write_text(json.dumps(manifest),encoding='utf-8-sig')
    output=publication.preparer(tmp_path)
    catalogue=json.loads(output.read_text())
    assert valider(catalogue, public, 'windows')['version'] == VERSION
    assert valider(catalogue, public, 'android')['version'] == '0.3.7'
    exe.write_bytes(b'MZ-corrompu')
    with pytest.raises(ValueError,match='modifié'): publication.preparer(tmp_path)
    exe.write_bytes(b'MZ-test-integration')
    other=Ed25519PrivateKey.generate()
    secret.write_bytes(other.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    with pytest.raises(ValueError,match='ne correspond pas'): publication.preparer(tmp_path)
