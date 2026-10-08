# SPDX-License-Identifier: GPL-3.0-or-later
"""Archives récupérables avec les secrets du propriétaire, sans l'ancien PC."""
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import zipfile
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from coffre import Coffre, desenvelopper, ecrire_json

MAGIC = b'PATENTEASY-BACKUP-2\n'
MAX_SIZE = 500_000_000


def emballer(flux, cle, metadata):
    header = {'format': 2, 'date': datetime.now().isoformat(),
              'admins': [dict(c) for c in metadata['comptes'] if c['role'] == 'admin' and c['actif']],
              'recuperation': metadata['recuperation']}
    # Préférences, journal et données métier restent dans le contenu chiffré.
    for c in header['admins']:
        for key in list(c):
            if key not in ('id','identifiant','role','actif','enveloppe'): del c[key]
    texte = json.dumps(header, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    prefixe = MAGIC + len(texte).to_bytes(4, 'big') + texte
    nonce = secrets.token_bytes(12)
    return prefixe + nonce + AESGCM(cle).encrypt(nonce, flux, prefixe)


def _lire(fichier):
    p = Path(fichier)
    if p.stat().st_size > MAX_SIZE: raise ValueError('Sauvegarde trop volumineuse.')
    return p.read_bytes()


def _entete(contenu):
    if not contenu.startswith(MAGIC): raise ValueError('Sauvegarde au format portable requise.')
    debut = len(MAGIC)
    taille = int.from_bytes(contenu[debut:debut+4], 'big')
    if not 1 <= taille <= 500_000 or len(contenu) < debut + 4 + taille + 28:
        raise ValueError('Sauvegarde incomplète.')
    fin = debut + 4 + taille
    header = json.loads(contenu[debut+4:fin])
    return header, contenu[:fin], fin


def preparer(fichier, secret, mode='mot_de_passe', identifiant='', ancien_acces=None, cle_existante=None):
    contenu = _lire(fichier)
    from sauvegardes import MAGIC as ANCIEN
    if contenu.startswith(MAGIC):
        header, prefixe, debut = _entete(contenu)
    elif contenu.startswith(ANCIEN):
        if cle_existante is None and ancien_acces is None:
            raise ValueError('Cette ancienne sauvegarde nécessite aussi le fichier acces.json de l’ancien ordinateur. Les nouvelles sauvegardes 0.4.0 sont autonomes.')
        metadata = json.loads(Path(ancien_acces).read_text(encoding='utf-8')) if ancien_acces else None
        header = {'admins': [c for c in metadata['comptes'] if c['role']=='admin'], 'recuperation':metadata['recuperation']} if metadata else {}
        prefixe, debut = ANCIEN, len(ANCIEN)
    else: raise ValueError('Sauvegarde Patenteasy requise.')
    compte = None
    if cle_existante is not None:
        cle = cle_existante
    else:
        try:
            if mode == 'code':
                cle = desenvelopper(header['recuperation'], secret.strip(), 'recuperation')
                compte = next(c for c in header['admins'] if c['actif'])
            else:
                candidats = [c for c in header['admins'] if c['actif'] and (not identifiant or c['identifiant'].casefold()==identifiant.strip().casefold())]
                cle = None
                for c in candidats:
                    try:
                        cle = desenvelopper(c['enveloppe'], secret, c['identifiant'].casefold()+':admin')
                        compte = c; break
                    except Exception: continue
                if cle is None: raise ValueError()
        except Exception:
            raise ValueError('Mot de passe administrateur ou code de récupération incorrect.') from None
    try:
        flux = AESGCM(cle).decrypt(contenu[debut:debut+12], contenu[debut+12:], prefixe)
        with zipfile.ZipFile(io.BytesIO(flux)) as archive:
            if set(archive.namelist()) != {'base.db','acces.json'}: raise ValueError()
            if sum(i.file_size for i in archive.infolist()) > MAX_SIZE: raise ValueError()
            base = archive.read('base.db'); metadata = json.loads(archive.read('acces.json'))
        if metadata.get('format') != 1: raise ValueError()
        admins = [c for c in metadata['comptes'] if c['role']=='admin' and c['actif']]
        if compte and not any(c['id']==compte['id'] and c['enveloppe']==compte['enveloppe'] for c in admins): raise ValueError()
        compte = next((c for c in admins if not compte or c['id']==compte['id']), None)
        if compte is None: raise ValueError()
    except Exception:
        raise ValueError('Sauvegarde endommagée ou accès incorrect. Aucun fichier remplacé.') from None
    return {'base':base,'metadata':metadata,'cle':cle,'compte':{k:compte[k] for k in ('id','identifiant','role')},'date':header.get('date','')}


def verifier(preparation, dossier):
    import tempfile
    dossier = Path(dossier); dossier.mkdir(parents=True, exist_ok=True)
    fd, nom = tempfile.mkstemp(prefix='verification-', suffix='.db', dir=dossier); os.close(fd)
    p = Path(nom)
    coffre = Coffre(p); coffre.cle = preparation['cle']
    try:
        p.write_bytes(preparation['base'])
        c = coffre.ouvrir()
        try:
            if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or c.execute('PRAGMA cipher_integrity_check').fetchall(): raise ValueError('Sauvegarde invalide.')
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            entreprise = dict(c.execute('SELECT * FROM entreprise WHERE id=1').fetchone()) if 'entreprise' in tables else {'nom':''}
            total = lambda table: c.execute(f'SELECT count(*) FROM {table}').fetchone()[0] if table in tables else 0
            return {'entreprise':entreprise['nom'], 'clients':total('clients'),'devis':total('devis'),'factures':c.execute("SELECT count(*) FROM documents WHERE type='facture'").fetchone()[0] if 'documents' in tables else 0}
        finally: c.close()
    finally: p.unlink(missing_ok=True)


def installer(preparation, coffre, configuration=None):
    metadata = json.loads(json.dumps(preparation['metadata']))
    if configuration is None:
        metadata['sauvegardes'].update(dossier='',derniere='',dernier_jour='',erreur='')
    else: metadata['sauvegardes'] = configuration
    temp = coffre.chemin.parent/'restauration.db'
    pending = coffre.chemin.parent/'restauration-acces.json'
    coffre.chemin.parent.mkdir(parents=True,exist_ok=True)
    with temp.open('wb') as output:
        output.write(preparation['base']); output.flush(); os.fsync(output.fileno())
    metadata['_restauration_sha256'] = hashlib.sha256(preparation['base']).hexdigest()
    ecrire_json(pending,metadata)
    os.replace(temp,coffre.chemin)
    metadata.pop('_restauration_sha256')
    ecrire_json(coffre.metadata,metadata)
    pending.unlink(missing_ok=True)


def reprendre(coffre):
    pending = coffre.chemin.parent/'restauration-acces.json'
    temp = coffre.chemin.parent/'restauration.db'
    if not pending.exists(): return
    metadata = json.loads(pending.read_text(encoding='utf-8'))
    attendu = metadata.get('_restauration_sha256')
    if attendu:
        if temp.exists() and hashlib.sha256(temp.read_bytes()).hexdigest() == attendu:
            os.replace(temp,coffre.chemin)
        if not coffre.chemin.exists() or hashlib.sha256(coffre.chemin.read_bytes()).hexdigest() != attendu:
            raise ValueError('Restauration interrompue. Les fichiers à reprendre ne correspondent pas.')
        metadata.pop('_restauration_sha256')
        ecrire_json(coffre.metadata,metadata);pending.unlink()
    elif not temp.exists(): os.replace(pending,coffre.metadata)
