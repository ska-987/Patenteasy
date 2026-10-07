# SPDX-License-Identifier: GPL-3.0-or-later
"""Signer avec une clé PEM existante, jamais en générer une de remplacement."""
import argparse,base64,json
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
p=argparse.ArgumentParser();p.add_argument('catalogue');p.add_argument('cle_privee');p.add_argument('sortie');a=p.parse_args()
cle=serialization.load_pem_private_key(Path(a.cle_privee).read_bytes(),password=None)
if not isinstance(cle,Ed25519PrivateKey):raise ValueError('Clé Ed25519 PEM existante requise.')
publique=base64.b64encode(cle.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode('ascii')
if publique!='B3yqsEr0OHYgpkAMnmool2zH29gXWMrWZtUdK6f9vtY=':raise ValueError('Clé différente de celle des applications officielles.')
donnees=json.loads(Path(a.catalogue).read_text(encoding='utf-8'));contenu=json.dumps(donnees,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8');sig=cle.sign(contenu);cle.public_key().verify(sig,contenu)
Path(a.sortie).write_text(json.dumps({'versions':donnees,'signature':base64.b64encode(sig).decode('ascii')},ensure_ascii=False,indent=2),encoding='utf-8')
print('Catalogue signé avec la clé officielle existante.')
