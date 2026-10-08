# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
"""Documents immuables, règlements et réglages de Patenteasy."""
import json
from coffre import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
import regional
import database as db

class GestionDocuments:
    """Émission, numérotation, paiements et avoirs."""

    def __init__(self, base=None):
        self.base = base if base is not None else db.base

    def aujourd_hui(self):
        return date.today()

    @contextmanager
    def connexion(self):
        c = sqlite3.connect(self.base.chemin, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys = ON')
        try:
            c.execute('BEGIN IMMEDIATE')
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def migrer(self):
        ancien = False
        if self.base.chemin.exists():
            ancien = bool(self.liste("SELECT name FROM sqlite_master WHERE name='entreprise'"))
        self.base.initialiser_base()
        with self.connexion() as c:
            champs = {'entreprise': {'validite_devis_jours': 'INTEGER NOT NULL DEFAULT 30', 'conditions_vente': "TEXT NOT NULL DEFAULT ''", 'conditions_reglement': "TEXT NOT NULL DEFAULT ''", 'mention_complementaire': "TEXT NOT NULL DEFAULT ''", 'solde_depart_centiemes': 'INTEGER NOT NULL DEFAULT 0', 'date_solde_depart': "TEXT NOT NULL DEFAULT ''", 'periodicite_tva': "TEXT NOT NULL DEFAULT ''"}, 'devis': {'conditions_vente': "TEXT NOT NULL DEFAULT ''", 'conditions_reglement': "TEXT NOT NULL DEFAULT ''", 'mention_complementaire': "TEXT NOT NULL DEFAULT ''", 'regime_document': "TEXT NOT NULL DEFAULT ''", 'numero': 'TEXT', 'instantane': 'TEXT'}, 'fiscalite_annuelle': {'regime_confirme': "TEXT NOT NULL DEFAULT ''", 'date_confirmation': "TEXT NOT NULL DEFAULT ''", 'ca_annee_centiemes': 'INTEGER', 'date_ca': "TEXT NOT NULL DEFAULT ''"}}
            for table, colonnes in champs.items():
                existants = {r[1] for r in c.execute(f'PRAGMA table_info({table})')}
                for nom, definition in colonnes.items():
                    if nom not in existants:
                        c.execute(f'ALTER TABLE {table} ADD COLUMN {nom} {definition}')
            existants = {r[1] for r in c.execute('PRAGMA table_info(entreprise)')}
            nouveaux = 'devise' not in existants
            definitions = {'pays': "TEXT NOT NULL DEFAULT ''", 'devise': "TEXT NOT NULL DEFAULT 'EUR'",
                'decimales': 'INTEGER NOT NULL DEFAULT 2', 'format_date': "TEXT NOT NULL DEFAULT 'dd/MM/yy'",
                'langue': "TEXT NOT NULL DEFAULT 'fr'", 'nom_taxe': "TEXT NOT NULL DEFAULT 'Taxe'",
                'mention_sans_taxe': "TEXT NOT NULL DEFAULT ''", 'libelle_identifiant': "TEXT NOT NULL DEFAULT 'Identifiant professionnel'"}
            for nom, definition in definitions.items():
                if nom not in existants: c.execute(f'ALTER TABLE entreprise ADD COLUMN {nom} {definition}')
            if nouveaux and ancien:
                c.execute("UPDATE entreprise SET pays='PF',devise='XPF',nom_taxe='TVA',libelle_identifiant='N° TAHITI',mention_sans_taxe='TVA non applicable, franchise en base' WHERE id=1")
            c.execute("CREATE TABLE IF NOT EXISTS brouillons_ui (devis_id INTEGER PRIMARY KEY REFERENCES devis(id) ON DELETE CASCADE, contenu TEXT NOT NULL)")
            c.execute("""CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY, type TEXT NOT NULL CHECK(type IN ('facture','avoir')),
            numero TEXT NOT NULL UNIQUE, date_document TEXT NOT NULL,
            echeance TEXT NOT NULL, devis_id INTEGER UNIQUE REFERENCES devis(id),
            origine_id INTEGER REFERENCES documents(id), instantane TEXT NOT NULL,
            total_centiemes INTEGER NOT NULL CHECK(total_centiemes >= 0))""")
            c.execute("""CREATE TABLE IF NOT EXISTS sequences (
            type TEXT NOT NULL, annee INTEGER NOT NULL, compteur INTEGER NOT NULL,
            PRIMARY KEY(type, annee))""")
            c.execute("""CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id),
            date_paiement TEXT NOT NULL, montant_centiemes INTEGER NOT NULL CHECK(montant_centiemes>0),
            mode TEXT NOT NULL, reference TEXT NOT NULL DEFAULT '',
            operation_id INTEGER UNIQUE REFERENCES operations(id))""")
            c.execute("""CREATE TABLE IF NOT EXISTS remboursements (
            id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id),
            date_remboursement TEXT NOT NULL, montant_centiemes INTEGER NOT NULL CHECK(montant_centiemes>0),
            mode TEXT NOT NULL, operation_id INTEGER UNIQUE REFERENCES operations(id))""")
            c.execute("""CREATE TABLE IF NOT EXISTS rappels (
            id INTEGER PRIMARY KEY, titre TEXT NOT NULL, echeance TEXT NOT NULL,
            fait INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT '',
            UNIQUE(titre,echeance))""")
            c.execute("""CREATE TABLE IF NOT EXISTS stock_mouvements (
            id INTEGER PRIMARY KEY, article_id INTEGER NOT NULL REFERENCES articles(id),
            date_mouvement TEXT NOT NULL, quantite_centiemes INTEGER NOT NULL,
            motif TEXT NOT NULL)""")

    def liste(self, sql, params=()):
        c = sqlite3.connect(self.base.chemin)
        c.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in c.execute(sql, params)]
        finally:
            c.close()

    def nombre_jours(self, valeur):
        try:
            n = int(str(valeur))
        except ValueError:
            raise ValueError('Saisissez une durée entière.') from None
        if not 1 <= n <= 365:
            raise ValueError('La validité doit être comprise entre 1 et 365 jours.')
        return n

    def date_valide(self, texte):
        try:
            return date.fromisoformat(texte).isoformat()
        except (ValueError, TypeError):
            raise ValueError('Date invalide.') from None

    def creer_devis(self, client_id, date_devis, objet=''):
        date_devis = self.date_valide(date_devis)
        with self.connexion() as c:
            if not c.execute('SELECT id FROM clients WHERE id=?', (client_id,)).fetchone():
                raise ValueError('Choisissez un client existant.')
            e = dict(c.execute('SELECT * FROM entreprise WHERE id=1').fetchone())
            return c.execute("""INSERT INTO devis
            (client_id,date_devis,objet,validite_jours)
            VALUES(?,?,?,?)""", (client_id, date_devis, objet.strip(), e['validite_devis_jours'])).lastrowid

    def modifier_devis(self, identifiant, client_id, date_devis, objet, validite, vente='', reglement='', mention=''):
        # Les arguments historiques restent compatibles ; seules les préférences
        # de l'entreprise peuvent désormais définir les conditions des documents.
        date_devis = self.date_valide(date_devis)
        with self.connexion() as c:
            d = c.execute('SELECT * FROM devis WHERE id=?', (identifiant,)).fetchone()
            if not d or d['statut'] != 'brouillon':
                raise ValueError('Seul un brouillon peut être modifié.')
            if not c.execute('SELECT id FROM clients WHERE id=?', (client_id,)).fetchone():
                raise ValueError('Client introuvable.')
            c.execute("""UPDATE devis SET client_id=?,date_devis=?,objet=?,validite_jours=?
            WHERE id=?""", (client_id, date_devis, objet.strip(), self.nombre_jours(validite), identifiant))

    def conditions_documents(self):
        """Textes actuels des Réglages, indépendants des instantanés comptables."""
        e = self.base.obtenir_entreprise() or {}
        return {champ: e.get(champ, '').strip() for champ in
                ('conditions_vente', 'conditions_reglement', 'mention_complementaire')}

    def regler_conditions_documents(self, vente, reglement, mention):
        """Enregistre les textes des Réglages sans dépendre des autres champs."""
        with self.connexion() as c:
            c.execute("""UPDATE entreprise SET conditions_vente=?,conditions_reglement=?,
            mention_complementaire=? WHERE id=1""", (vente.strip(), reglement.strip(), mention.strip()))

    def regler_entreprise(self, validite, vente, reglement, mention, periodicite, solde, date_solde):
        if periodicite not in ('', 'mensuelle', 'trimestrielle'):
            raise ValueError('Périodicité invalide.')
        valeur = regional.convertir_montant(solde, self.base.obtenir_entreprise(), signe=True)
        if date_solde:
            date_solde = self.date_valide(date_solde)
        with self.connexion() as c:
            c.execute("""UPDATE entreprise SET validite_devis_jours=?,conditions_vente=?,conditions_reglement=?,
            mention_complementaire=?,periodicite_tva=?,solde_depart_centiemes=?,date_solde_depart=? WHERE id=1""", (self.nombre_jours(validite), vente.strip(), reglement.strip(), mention.strip(), periodicite, valeur, date_solde))

    def confirmer_fiscalite(self, annee, regime, date_confirmation='', ca='', date_ca=''):
        if regime not in ('', 'franchise', 'reel'):
            raise ValueError('Régime invalide.')
        montant = self.base.convertir_montant(ca) if ca.strip() else None
        # Les anciennes colonnes restent pour la compatibilité des sauvegardes.
        # Le choix annuel est libre, sans attestation ni date obligatoire.
        date_confirmation = date_ca = ''
        with self.connexion() as c:
            c.execute("""INSERT INTO fiscalite_annuelle(annee,regime_confirme,date_confirmation,ca_annee_centiemes,date_ca)
            VALUES(?,?,?,?,?) ON CONFLICT(annee) DO UPDATE SET regime_confirme=excluded.regime_confirme,
            date_confirmation=excluded.date_confirmation,ca_annee_centiemes=excluded.ca_annee_centiemes,date_ca=excluded.date_ca""", (annee, regime, date_confirmation, montant, date_ca))

    def regime_a_la_date(self, jour):
        f = self.base.obtenir_fiscalite_annuelle(date.fromisoformat(jour).year) or {}
        # Ne jamais changer le calcul choisi à partir du CA ou d'une ancienne date.
        # Un choix vide signifie sans TVA calculée, sans affirmer une franchise.
        return f.get('regime_confirme', '')

    def rappel_seuil_ca(self, annee):
        cfg = regional.configuration(self.base.obtenir_entreprise())
        if cfg['pays'] != 'PF' or cfg['devise'] != 'XPF': return ''
        f = self.base.obtenir_fiscalite_annuelle(annee) or {}
        if (f.get('ca_annee_centiemes') or 0) > 10000000 * (10 ** cfg['decimales']):
            return ('CA supérieur à 10 000 000 F CFP : déclarez le dépassement à la DICP '
                    'dans le mois qui suit. Votre choix de TVA reste modifiable.')
        return ''

    def calculer(self, devis_id):
        d = self.base.obtenir_devis(devis_id)
        if not d:
            raise ValueError('Devis introuvable.')
        if d.get('instantane'):
            return json.loads(d['instantane'])
        regime = self.regime_a_la_date(d['date_devis'])
        lignes = self.base.lister_lignes_devis(devis_id)
        groupes = {}
        for l in lignes:
            l['ht'] = (l['quantite_centiemes'] * l['prix_unitaire_centiemes'] + 50) // 100
            l['tva'] = (l['ht'] * l['taxe_centiemes'] + 5000) // 10000 if regime == 'reel' else 0
            l['ttc'] = l['ht'] + l['tva']
            if regime == 'reel':
                g = groupes.setdefault(str(l['taxe_centiemes']), {'taux': l['taxe_centiemes'], 'base': 0, 'tva': 0})
                g['base'] += l['ht']
                g['tva'] += l['tva']
        ht = sum((l['ht'] for l in lignes))
        tva = sum((l['tva'] for l in lignes))
        return {'devis': d, 'entreprise': self.base.obtenir_entreprise(), 'client': self.base.obtenir_client(d['client_id']), 'lignes': lignes, 'regime': regime, 'groupes': list(groupes.values()), 'ht': ht, 'tva': tva, 'ttc': ht + tva, 'validite': (date.fromisoformat(d['date_devis']) + timedelta(days=d['validite_jours'])).isoformat(), 'mention_tva': self.base.obtenir_entreprise().get('mention_sans_taxe', '') if regime == 'franchise' else '', 'conditions_vente': d['conditions_vente'], 'conditions_reglement': d['conditions_reglement'], 'mention_complementaire': d['mention_complementaire']}

    def verifier_emission(self, s):
        e = s['entreprise']
        if not e['nom'].strip():
            raise ValueError('Renseignez le nom de votre entreprise.')
        if not s['lignes']:
            raise ValueError('Ajoutez au moins une ligne.')

    def enregistrer_brouillon_ui(self, identifiant, contenu):
        with self.connexion() as c:
            row = c.execute('SELECT statut FROM devis WHERE id=?', (identifiant,)).fetchone()
            if not row or row['statut'] != 'brouillon': return
            c.execute('INSERT OR REPLACE INTO brouillons_ui VALUES(?,?)', (identifiant, json.dumps(contenu, ensure_ascii=False)))

    def lire_brouillon_ui(self, identifiant):
        rows = self.liste('SELECT contenu FROM brouillons_ui WHERE devis_id=?', (identifiant,))
        return json.loads(rows[0]['contenu']) if rows else None

    def regler_region(self, pays, devise, decimales, format_date, langue, nom_taxe, mention_sans_taxe, libelle_identifiant):
        import re
        pays, devise = pays.strip().upper(), devise.strip().upper()
        if pays and not re.fullmatch('[A-Z]{2}', pays): raise ValueError('Choisissez un pays.')
        if not re.fullmatch('[A-Z]{3}', devise): raise ValueError('Devise : code de trois lettres, par exemple EUR, USD, XPF.')
        if decimales not in (0,1,2,3,4) or format_date not in regional.FORMATS or langue not in ('fr','en'):
            raise ValueError('Réglage de format invalide.')
        with self.connexion() as c:
            e = dict(c.execute('SELECT * FROM entreprise WHERE id=1').fetchone())
            if devise != e['devise'] or decimales != e['decimales']:
                utilise = any(c.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone() for table in ('articles','devis_lignes','operations','documents','reprise_mensuelle'))
                utilise = utilise or e['solde_depart_centiemes'] != 0 or bool(c.execute('SELECT 1 FROM fiscalite_annuelle WHERE ca_n1_centiemes IS NOT NULL OR ca_annee_centiemes IS NOT NULL LIMIT 1').fetchone())
                if utilise: raise ValueError('Cette devise est déjà utilisée dans les montants enregistrés. Conservez sa devise et sa précision ; aucune conversion automatique n’est effectuée.')
            c.execute('UPDATE entreprise SET pays=?,devise=?,decimales=?,format_date=?,langue=?,nom_taxe=?,mention_sans_taxe=?,libelle_identifiant=? WHERE id=1',
                (pays,devise,decimales,format_date,langue,nom_taxe.strip() or 'Taxe',mention_sans_taxe.strip(),libelle_identifiant.strip()))

    def numero(self, c, type_doc, annee):
        import re
        prefix = {'devis': 'dev', 'facture': 'fact', 'avoir': 'av'}[type_doc]
        c.execute('INSERT OR IGNORE INTO sequences VALUES(?,?,0)', (type_doc, 0))
        compteur = c.execute('SELECT compteur FROM sequences WHERE type=? AND annee=0', (type_doc,)).fetchone()[0]
        table = 'devis' if type_doc == 'devis' else 'documents'
        for r in c.execute(f'SELECT numero FROM {table} WHERE numero IS NOT NULL'):
            match = re.fullmatch(re.escape(prefix) + '-(\\d+)', r['numero'])
            if match:
                compteur = max(compteur, int(match.group(1)))
        compteur += 1
        c.execute('UPDATE sequences SET compteur=? WHERE type=? AND annee=0', (compteur, type_doc))
        return f'{prefix}-{compteur:05d}'

    def emettre_devis(self, identifiant):
        with self.connexion() as c:
            d = c.execute('SELECT * FROM devis WHERE id=?', (identifiant,)).fetchone()
            if not d or d['statut'] != 'brouillon':
                raise ValueError('Ce devis n’est plus un brouillon.')
            s = self.calculer(identifiant)
            self.verifier_emission(s)
            c.execute('DELETE FROM brouillons_ui WHERE devis_id=?', (identifiant,))
            n = self.numero(c, 'devis', int(d['date_devis'][:4]))
            s['numero'] = n
            c.execute("UPDATE devis SET numero=?,instantane=?,statut='envoye' WHERE id=?", (n, json.dumps(s, ensure_ascii=False), identifiant))

    def decision_devis(self, identifiant, statut):
        if statut not in ('accepte', 'refuse'):
            raise ValueError('Décision invalide.')
        with self.connexion() as c:
            d = c.execute('SELECT * FROM devis WHERE id=?', (identifiant,)).fetchone()
            if not d or d['statut'] != 'envoye':
                raise ValueError('Enregistrez la décision sur un devis émis.')
            if statut == 'accepte' and self.aujourd_hui() > date.fromisoformat(json.loads(d['instantane'])['validite']):
                raise ValueError('Le devis est expiré. Créez une nouvelle version.')
            c.execute('UPDATE devis SET statut=? WHERE id=?', (statut, identifiant))

    def dupliquer_devis(self, identifiant):
        with self.connexion() as c:
            d = c.execute('SELECT * FROM devis WHERE id=?', (identifiant,)).fetchone()
            if not d:
                raise ValueError('Devis introuvable.')
            nid = c.execute("""INSERT INTO devis(client_id,date_devis,objet,validite_jours,conditions_vente,
            conditions_reglement,mention_complementaire) VALUES(?,?,?,?,?,?,?)""", (d['client_id'], self.aujourd_hui().isoformat(), d['objet'], d['validite_jours'], d['conditions_vente'], d['conditions_reglement'], d['mention_complementaire'])).lastrowid
            c.execute("""INSERT INTO devis_lignes(devis_id,reference,designation,unite,quantite_centiemes,prix_unitaire_centiemes,taxe_centiemes)
            SELECT ?,reference,designation,unite,quantite_centiemes,prix_unitaire_centiemes,taxe_centiemes FROM devis_lignes WHERE devis_id=?""", (nid, identifiant))
            return nid

    def creer_facture(self, devis_id, jour, echeance):
        jour = self.date_valide(jour)
        echeance = self.date_valide(echeance)
        if jour > self.aujourd_hui().isoformat() or echeance < jour:
            raise ValueError('Date future ou échéance antérieure à la facture.')
        with self.connexion() as c:
            d = c.execute('SELECT * FROM devis WHERE id=?', (devis_id,)).fetchone()
            if not d or d['statut'] != 'accepte':
                raise ValueError('Enregistrez d’abord l’acceptation du devis.')
            if c.execute('SELECT id FROM documents WHERE devis_id=?', (devis_id,)).fetchone():
                raise ValueError('Une facture existe déjà pour ce devis.')
            s = json.loads(d['instantane'])
            regime = self.regime_a_la_date(jour)
            if regime != s['regime']:
                raise ValueError('Le régime a changé ou reste inconnu à la date de facture. Établissez un nouveau devis adapté.')
            if jour < d['date_devis']:
                raise ValueError('La facture ne peut pas précéder le devis.')
            n = self.numero(c, 'facture', int(jour[:4]))
            s.update(numero=n, date_document=jour, echeance=echeance, type='facture', numero_devis=d['numero'])
            return c.execute("""INSERT INTO documents(type,numero,date_document,echeance,devis_id,instantane,total_centiemes)
            VALUES('facture',?,?,?,?,?,?)""", (n, jour, echeance, devis_id, json.dumps(s, ensure_ascii=False), s['ttc'])).lastrowid

    def documents(self):
        return self.liste("""SELECT d.*, COALESCE((SELECT SUM(montant_centiemes) FROM paiements WHERE document_id=d.id),0) AS paye,
        COALESCE((SELECT SUM(total_centiemes) FROM documents WHERE origine_id=d.id),0) AS credite
        FROM documents d ORDER BY date_document DESC,id DESC""")

    def document(self, identifiant):
        for d in self.documents():
            if d['id'] == identifiant:
                d['contenu'] = json.loads(d['instantane'])
                d['reste'] = max(0, d['total_centiemes'] - d['paye'] - d['credite'])
                d['remboursements'] = self.liste('SELECT * FROM remboursements WHERE document_id=? ORDER BY id', (identifiant,))
                d['a_rembourser'] = max(0, d['paye'] - (d['total_centiemes'] - d['credite'])) - sum((r['montant_centiemes'] for r in d['remboursements']))
                d['paiements'] = self.liste('SELECT * FROM paiements WHERE document_id=? ORDER BY date_paiement,id', (identifiant,))
                return d
        raise ValueError('Document introuvable.')

    def payer(self, identifiant, jour, montant, mode, reference):
        jour = self.date_valide(jour)
        m = self.base.convertir_montant(montant)
        if mode not in ('virement', 'carte', 'especes', 'cheque', 'autre') or m <= 0:
            raise ValueError('Montant ou moyen de paiement invalide.')
        cfg = regional.configuration(self.base.obtenir_entreprise())
        if mode == 'especes' and cfg['pays'] == 'PF' and cfg['devise'] == 'XPF' and m % (5 * 10 ** cfg['decimales']):
            raise ValueError('En espèces, saisissez le montant effectivement encaissé, multiple de 5 F CFP. Utilisez un ajustement documenté si nécessaire.')
        with self.connexion() as c:
            d = self.document(identifiant)
            if d['type'] != 'facture' or m > d['reste']:
                raise ValueError('Le paiement dépasse le reste dû ou le document n’est pas une facture.')
            if jour < d['date_document'] or jour > self.aujourd_hui().isoformat():
                raise ValueError('Date de paiement invalide.')
            f = self.base.obtenir_fiscalite_annuelle(int(jour[:4])) or {}
            fin = f.get('date_fin_reprise', '')
            if fin and jour <= fin:
                raise ValueError('Paiement compris dans la reprise : ne le saisissez pas une seconde fois. Corrigez d’abord la reprise.')
            op = c.execute('INSERT INTO operations(date_operation,libelle,type_operation,montant_centiemes) VALUES(?,?,?,?)', (jour, 'Paiement ' + d['numero'], 'recette', m)).lastrowid
            c.execute('INSERT INTO paiements(document_id,date_paiement,montant_centiemes,mode,reference,operation_id) VALUES(?,?,?,?,?,?)', (identifiant, jour, m, mode, reference.strip(), op))

    def creer_avoir(self, identifiant, motif, quantites=None):
        from coffre import ACTIF
        if ACTIF is not None and ACTIF.compte.get('role') != 'admin':
            raise PermissionError('Action réservée à l’administrateur.')
        if not motif.strip():
            raise ValueError('Indiquez le motif de l’avoir.')
        with self.connexion() as c:
            d = self.document(identifiant)
            if d['type'] != 'facture':
                raise ValueError('Choisissez une facture.')
            if d['credite'] >= d['total_centiemes']:
                raise ValueError('La facture est déjà entièrement créditée.')
            deja = {}
            for r in c.execute('SELECT instantane FROM documents WHERE origine_id=?', (identifiant,)):
                for l in json.loads(r[0])['lignes']:
                    deja[l['id']] = deja.get(l['id'], 0) + l['quantite_centiemes']
            s = json.loads(d['instantane'])
            lignes = []
            groupes = {}
            for l in s['lignes']:
                restant = l['quantite_centiemes'] - deja.get(l['id'], 0)
                q = restant if quantites is None else self.base.convertir_en_centiemes(quantites.get(str(l['id']), '0') or '0')
                if q > restant:
                    raise ValueError('La quantité à créditer dépasse la quantité restante de ' + l['designation'])
                if not q:
                    continue
                l['quantite_centiemes'] = q
                l['ht'] = (q * l['prix_unitaire_centiemes'] + 50) // 100
                l['tva'] = (l['ht'] * l['taxe_centiemes'] + 5000) // 10000 if s['regime'] == 'reel' else 0
                l['ttc'] = l['ht'] + l['tva']
                lignes.append(l)
                gr = groupes.setdefault(str(l['taxe_centiemes']), {'taux': l['taxe_centiemes'], 'base': 0, 'tva': 0})
                gr['base'] += l['ht']
                gr['tva'] += l['tva']
            if not lignes:
                raise ValueError('Indiquez au moins une quantité à créditer.')
            ht = sum((l['ht'] for l in lignes))
            tva = sum((l['tva'] for l in lignes))
            if ht + tva > d['total_centiemes'] - d['credite']:
                raise ValueError('Les arrondis dépassent le montant restant à créditer. Regroupez les quantités dans un seul avoir.')
            jour = self.aujourd_hui().isoformat()
            n = self.numero(c, 'avoir', int(jour[:4]))
            s.update(numero=n, type='avoir', date_document=jour, echeance=jour, origine_numero=d['numero'], motif=motif.strip(), lignes=lignes, ht=ht, tva=tva, ttc=ht + tva, groupes=list(groupes.values()))
            return c.execute("""INSERT INTO documents(type,numero,date_document,echeance,origine_id,instantane,total_centiemes)
            VALUES('avoir',?,?,?,?,?,?)""", (n, jour, jour, identifiant, json.dumps(s, ensure_ascii=False), ht + tva)).lastrowid

    def rembourser(self, identifiant, jour, montant, mode):
        from coffre import ACTIF
        if ACTIF is not None and ACTIF.compte.get('role') != 'admin':
            raise PermissionError('Action réservée à l’administrateur.')
        jour = self.date_valide(jour)
        m = self.base.convertir_montant(montant)
        if m <= 0 or mode not in ('virement', 'carte', 'especes', 'cheque', 'autre'):
            raise ValueError('Montant ou moyen de remboursement invalide.')
        cfg = regional.configuration(self.base.obtenir_entreprise())
        if mode == 'especes' and cfg['pays'] == 'PF' and cfg['devise'] == 'XPF' and m % (5 * 10 ** cfg['decimales']):
            raise ValueError('Le montant en espèces doit être un multiple de 5 F CFP.')
        with self.connexion() as c:
            d = self.document(identifiant)
            deja = c.execute('SELECT COALESCE(SUM(montant_centiemes),0) FROM remboursements WHERE document_id=?', (identifiant,)).fetchone()[0]
            maximum = max(0, d['paye'] - (d['total_centiemes'] - d['credite'])) - deja
            if d['type'] != 'facture' or m > maximum:
                raise ValueError('Le remboursement dépasse le montant disponible après avoir.')
            if jour < d['date_document'] or jour > self.aujourd_hui().isoformat():
                raise ValueError('Date invalide.')
            f = self.base.obtenir_fiscalite_annuelle(int(jour[:4])) or {}
            if f.get('date_fin_reprise', '') and jour <= f['date_fin_reprise']:
                raise ValueError('Date comprise dans la reprise.')
            op = c.execute('INSERT INTO operations(date_operation,libelle,type_operation,montant_centiemes) VALUES(?,?,?,?)', (jour, 'Remboursement ' + d['numero'], 'depense', m)).lastrowid
            c.execute('INSERT INTO remboursements(document_id,date_remboursement,montant_centiemes,mode,operation_id) VALUES(?,?,?,?,?)', (identifiant, jour, m, mode, op))

    def stock(self):
        return self.liste("""SELECT a.*,COALESCE(SUM(s.quantite_centiemes),0) AS stock FROM articles a
        LEFT JOIN stock_mouvements s ON s.article_id=a.id WHERE a.type_article='produit' GROUP BY a.id ORDER BY designation""")

    def bouger_stock(self, article_id, jour, quantite, sens, motif):
        q = self.base.convertir_en_centiemes(quantite)
        jour = self.date_valide(jour)
        if q <= 0 or sens not in ('entree', 'sortie') or (not motif.strip()) or (jour > self.aujourd_hui().isoformat()):
            raise ValueError('Renseignez une quantité positive, une date passée et un motif.')
        with self.connexion() as c:
            a = c.execute('SELECT * FROM articles WHERE id=?', (article_id,)).fetchone()
            if not a or a['type_article'] != 'produit':
                raise ValueError('Choisissez un produit.')
            total = c.execute('SELECT COALESCE(SUM(quantite_centiemes),0) FROM stock_mouvements WHERE article_id=?', (article_id,)).fetchone()[0]
            if sens == 'sortie' and q > total:
                raise ValueError('Stock insuffisant.')
            c.execute('INSERT INTO stock_mouvements(article_id,date_mouvement,quantite_centiemes,motif) VALUES(?,?,?,?)', (article_id, jour, q if sens == 'entree' else -q, motif.strip()))

gestion = GestionDocuments()

def __getattr__(nom):
    return getattr(gestion, nom)
