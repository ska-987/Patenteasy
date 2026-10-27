import base64,json,hashlib,io
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from distribution import signer_windows as signer
from mises_a_jour import valider

def test_signature_windows_conserve_android_et_refuse_downgrade(tmp_path,monkeypatch):
    key=Ed25519PrivateKey.generate();pub=base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
    cfg={'catalogue_mises_a_jour':'https://exemple.invalid/catalogue.json','cle_publique_mises_a_jour':pub}
    (tmp_path/'configuration_editeur.json').write_text(json.dumps(cfg))
    private=tmp_path/'editeur.pem';private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    monkeypatch.setattr(signer,'ROOT',tmp_path);monkeypatch.setenv('PATENTEASY_CATALOGUE_KEY_FILE',str(private))
    exe=tmp_path/f'Patenteasy-Windows-{signer.VERSION}-Installation.exe';exe.write_bytes(b'construction-test')
    (tmp_path/'version-verifiee.json').write_text(json.dumps({'version':signer.VERSION,'taille':exe.stat().st_size,'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}))
    versions={'windows':{'version':'0.4.4','url':'https://exemple.invalid/ancien.exe','taille':1,'sha256':'0'*64,'format':'exe'},'android':{'version':'0.4.4','url':'https://exemple.invalid/android.apk','taille':123,'sha256':'1'*64,'format':'apk'}}
    def catalogue():
        raw=json.dumps(versions,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        return json.dumps({'versions':versions,'signature':base64.b64encode(key.sign(raw)).decode()}).encode()
    monkeypatch.setattr(signer,'ouvrir_https',lambda *a,**k:io.BytesIO(catalogue()))
    sortie=signer.preparer(tmp_path)
    assert sortie['versions']['android']==versions['android']
    assert valider(sortie,pub,'windows')['version']==signer.VERSION
    avant=(tmp_path/'catalogue.json').read_bytes();versions['windows']['version']='99.0.0'
    with pytest.raises(ValueError):signer.preparer(tmp_path)
    assert (tmp_path/'catalogue.json').read_bytes()==avant
