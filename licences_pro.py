# SPDX-License-Identifier: GPL-3.0-or-later
"""Vérification locale du protocole public SKA, sans clé privée embarquée."""
import base64
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MODULES = ('finance_tva', 'administratif')

def utc():
    return datetime.now(timezone.utc)

def date_utc(s):
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if d.tzinfo is None: raise ValueError('Date de licence sans fuseau.')
    return d.astimezone(timezone.utc)

def json_unique(texte):
    def unique(paires):
        d = {}
        for k, v in paires:
            if k in d: raise ValueError('Champ JSON dupliqué.')
            d[k] = v
        return d
    if len(texte.encode('utf-8')) > 65536: raise ValueError('Licence trop volumineuse.')
    return json.loads(texte, object_pairs_hook=unique)

def verifier(licence, publique, entreprise, *, maintenant=None, dernier=''):
    now = maintenant or utc()
    resultat = {'active': False, 'message': 'Licence annuelle requise.', 'modules': []}
    if not publique:
        return {**resultat, 'message': 'Clé publique de ska_987 non configurée. Activation indisponible.'}
    try:
        if not isinstance(licence, dict) or set(licence) != {'payload', 'signature'}: raise ValueError()
        p = licence['payload']
        if p.get('schema') != 'ska-license-v1' or p.get('app_id') != 'patenteasy': raise ValueError('Licence destinée à une autre application.')
        signature = licence['signature']
        if not isinstance(signature, str) or not re.fullmatch(r'[A-Za-z0-9_-]{86}', signature): raise ValueError()
        contenu = json.dumps(p, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        Ed25519PublicKey.from_public_bytes(base64.b64decode(publique, validate=True)).verify(base64.urlsafe_b64decode(signature+'=='), contenu)
        if not p.get('license_id') or not p.get('customer_id'): raise ValueError()
        if not isinstance(p.get('features'), list) or not all(isinstance(x, str) for x in p['features']): raise ValueError()
        limites = p['limits']
        if any(type(limites.get(k)) is not int or limites[k] < 1 for k in ('employees', 'sites')): raise ValueError()
        debut, fin = date_utc(p['not_before']), date_utc(p['expires_at'])
        emission = date_utc(p['issued_at'])
        if fin <= debut or emission > fin: raise ValueError()
        if ' '.join(p['customer_name'].split()).casefold() != ' '.join(entreprise.split()).casefold() or not entreprise.strip():
            raise ValueError('Cette licence ne correspond pas au nom de votre entreprise.')
        infos = {**resultat, 'titulaire': p['customer_name'], 'expiration': p['expires_at'], 'id': p['license_id']}
        if dernier and now < date_utc(dernier)-timedelta(minutes=5):
            return {**infos, 'message': 'Horloge reculée. Vérifiez la date de cet appareil.'}
        if now < debut or now < emission: return {**infos, 'message': 'Licence pas encore active.'}
        if now >= fin: return {**infos, 'message': 'Licence expirée. La facturation gratuite reste disponible.'}
        modules = [x for x in MODULES if x in p['features']]
        return {**infos, 'active': True, 'message': 'Licence active.', 'modules': modules, 'jours': max(0, (fin-now).days)}
    except Exception as e:
        return {**resultat, 'message': str(e) or 'Signature ou contenu de licence invalide.'}

def admin_connecte():
    from coffre import ACTIF
    if ACTIF is None or ACTIF.compte.get('role') != 'admin':
        raise PermissionError('Cette action est réservée à l’administrateur.')

class LicencePro:
    def __init__(self, base, *, config=None, horloge=utc, autoriser=admin_connecte):
        self.base, self.horloge, self.autoriser = base, horloge, autoriser
        self.config = config if config is not None else json.loads((Path(__file__).parent/'licence_editeur.json').read_text())

    def etat(self):
        with self.base.session() as c:
            r = c.execute('SELECT contenu,dernier FROM licence_pro WHERE id=1').fetchone()
        if not r: return {'active':False, 'modules':[], 'message':'Licence annuelle requise.' if self.config['cle_publique_ed25519'] else 'Clé publique de ska_987 non configurée.'}
        e = self.base.obtenir_entreprise() or {}
        s = verifier(json_unique(r['contenu']), self.config['cle_publique_ed25519'], e.get('nom',''), maintenant=self.horloge(), dernier=r['dernier'])
        if s['active']:
            with self.base.session() as c:
                c.execute('UPDATE licence_pro SET dernier=? WHERE id=1', (max(self.horloge(), date_utc(r['dernier'])).isoformat(),))
        return s

    def importer(self, texte):
        self.autoriser()
        with self.base.session() as c:
            ancien = c.execute('SELECT dernier FROM licence_pro WHERE id=1').fetchone()
        dernier = ancien[0] if ancien else ''
        s = verifier(json_unique(texte), self.config['cle_publique_ed25519'], (self.base.obtenir_entreprise() or {}).get('nom',''), maintenant=self.horloge(), dernier=dernier)
        if not s['active']: raise ValueError(s['message'])
        with self.base.session() as c:
            c.execute('INSERT OR REPLACE INTO licence_pro VALUES(1,?,?)', (texte,max(self.horloge(), date_utc(dernier) if dernier else self.horloge()).isoformat()))
        return s

    def exiger(self, module):
        self.autoriser()
        s = self.etat()
        if not s['active'] or module not in s['modules']:
            raise PermissionError('Licence annuelle requise pour ce module. Demandez une licence à ska_987 ou activez-la dans Licence.')
        return s
