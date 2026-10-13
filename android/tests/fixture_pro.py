# SPDX-License-Identifier: GPL-3.0-or-later
import base64,json
from datetime import datetime,timezone,timedelta
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

def fixture():
    key=Ed25519PrivateKey.generate();now=datetime.now(timezone.utc)
    p={'schema':'ska-license-v1','app_id':'patenteasy','license_id':'L-TEST','customer_id':'C-TEST','customer_name':'Entreprise','features':['finance_tva','administratif'],'limits':{'employees':1,'sites':1},'issued_at':(now-timedelta(minutes=1)).isoformat().replace('+00:00','Z'),'not_before':(now-timedelta(minutes=1)).isoformat().replace('+00:00','Z'),'expires_at':(now+timedelta(days=365)).isoformat().replace('+00:00','Z')}
    licence={'payload':p,'signature':base64.urlsafe_b64encode(key.sign(json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())).decode().rstrip('=')}
    vide={'schema':2,'entreprise':{'nom':'Entreprise','regime':'reel','validite':30,'pays':'PF','devise':'XPF','decimales':0},'clients':[],'articles':[],'devis':[],'factures':[],'journal':[],'sequences':{'dev':0,'fact':0,'av':0}}
    data=json.loads(json.dumps(vide));data['factures']=[{'id':'F1','type':'facture','instantane':{'numero':'TEST','date':'2026-10-01','regime':'reel','lignes':[{'prix':10000,'quantite':100,'taux':1600}],'totaux':{'ttc':11600}},'paiements':[{'date':'2026-10-02','montant':5800}]}]
    data['qualifications_pro']={'F1':{'natures':['service'],'livraison':''}}
    data['achats_pro']=[{'id':'A1','date':'2026-10-01','livraison':'2026-10-01','fournisseur':'FOUR','reference':'TEST','justificatif':True,'lignes':[{'ht':10000,'tva':1600,'ttc':11600,'taux':1600,'deduction':10000,'nature':'bien','categorie':'autres'}],'paiements':[{'date':'2026-10-02','montant':11600,'journalId':'J2'}]}]
    data['journal']=[{'id':'J1','date':'2026-10-02','type':'recette','montant':5800,'libelle':'Encaissement'},{'id':'J2','date':'2026-10-02','type':'depense','montant':11600,'libelle':'Fournisseur','achatId':'A1'}]
    return {'publique':base64.b64encode(key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode(),'licence':licence,'now':int(now.timestamp()*1000),'vide':vide,'donnees':data}
