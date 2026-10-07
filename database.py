# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
from contextlib import contextmanager
from pathlib import Path
import os
import sys
from decimal import Decimal, InvalidOperation
from coffre import sqlite3
from datetime import date
BASE_DIR = Path(os.environ['PATENTEASY_DATA_DIR']) if os.environ.get('PATENTEASY_DATA_DIR') else Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'PatenteasyLocal' if getattr(sys, 'frozen', False) or os.environ.get('PATENTEASY_INSTALLE') == '1' else Path(__file__).resolve().parent
BASE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'patenteeasy.db'

class BaseDonnees:
    """Accès SQLite et règles fiscales."""

    def __init__(self, chemin=None):
        self._chemin = Path(chemin) if chemin is not None else None

    @property
    def chemin(self):
        return self._chemin if self._chemin is not None else DB_PATH

    @property
    def dossier(self):
        return self.chemin.parent

    @property
    def repertoire(self):
        return self.dossier.parent if self._chemin is not None else BASE_DIR

    def ouvrir(self):
        connexion = sqlite3.connect(self.chemin, timeout=15)
        connexion.row_factory = sqlite3.Row
        connexion.execute('PRAGMA foreign_keys = ON')
        return connexion

    @contextmanager
    def session(self):
        connexion = self.ouvrir()
        try:
            yield connexion
            connexion.commit()
        except Exception:
            connexion.rollback()
            raise
        finally:
            connexion.close()

    def initialiser_base(self):
        self.dossier.mkdir(exist_ok=True)
        with self.session() as connexion:
            connexion.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY,
                nom TEXT NOT NULL CHECK (length(trim(nom)) > 0),
                telephone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                adresse TEXT NOT NULL DEFAULT ''
            )
        """)
            connexion.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY,
                reference TEXT NOT NULL COLLATE NOCASE UNIQUE
                    CHECK (length(trim(reference)) > 0),
                designation TEXT NOT NULL
                    CHECK (length(trim(designation)) > 0),
                type_article TEXT NOT NULL
                    CHECK (type_article IN ('produit', 'service')),
                unite TEXT NOT NULL
                    CHECK (length(trim(unite)) > 0),
                prix_achat_centiemes INTEGER NOT NULL DEFAULT 0
                    CHECK (prix_achat_centiemes >= 0),
                prix_vente_centiemes INTEGER NOT NULL DEFAULT 0
                    CHECK (prix_vente_centiemes >= 0),
                taxe_centiemes INTEGER NOT NULL DEFAULT 0
                    CHECK (taxe_centiemes BETWEEN 0 AND 10000)
            )
        """)
            connexion.execute("""
            CREATE TABLE IF NOT EXISTS entreprise (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                nom TEXT NOT NULL DEFAULT '',
                responsable TEXT NOT NULL DEFAULT '',
                telephone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                adresse TEXT NOT NULL DEFAULT '',
                numero_tahiti TEXT NOT NULL DEFAULT '',
                monnaie TEXT NOT NULL DEFAULT 'XPF'
                    CHECK (monnaie = 'XPF')
            )
        """)
            connexion.execute("""
            INSERT OR IGNORE INTO entreprise (id)
            VALUES (1)
        """)
            colonnes = {ligne[1] for ligne in connexion.execute('PRAGMA table_info(entreprise)')}
            if 'numero_rcs' not in colonnes:
                connexion.execute("\n                ALTER TABLE entreprise\n                ADD COLUMN numero_rcs TEXT NOT NULL DEFAULT ''\n            ")
            colonnes_entreprise = {ligne[1] for ligne in connexion.execute('PRAGMA table_info(entreprise)')}
            if 'date_debut_activite' not in colonnes_entreprise:
                connexion.execute("\n                ALTER TABLE entreprise\n                ADD COLUMN date_debut_activite\n                TEXT NOT NULL DEFAULT ''\n            ")
            connexion.execute("""
            CREATE TABLE IF NOT EXISTS fiscalite_annuelle (
                annee INTEGER PRIMARY KEY,
                ca_n1_centiemes INTEGER
                    CHECK (ca_n1_centiemes >= 0),
                date_effet_option_reel TEXT NOT NULL DEFAULT '',
                date_depassement TEXT NOT NULL DEFAULT ''
            )
        """)
            connexion.execute("""
            CREATE TABLE IF NOT EXISTS reprise_mensuelle (
                annee INTEGER NOT NULL,
                mois INTEGER NOT NULL CHECK (mois BETWEEN 1 AND 12),
                recettes_centiemes INTEGER
                    CHECK (recettes_centiemes >= 0),
                depenses_centiemes INTEGER
                    CHECK (depenses_centiemes >= 0),
                verifie INTEGER NOT NULL DEFAULT 0
                    CHECK (verifie IN (0, 1)),
                PRIMARY KEY (annee, mois),
                CHECK (
                    verifie = 0 OR (
                        recettes_centiemes IS NOT NULL
                        AND depenses_centiemes IS NOT NULL
                    )
                )
            )
        """)
            colonnes_fiscalite = {ligne[1] for ligne in connexion.execute('PRAGMA table_info(fiscalite_annuelle)')}
            if 'date_fin_reprise' not in colonnes_fiscalite:
                connexion.execute("\n                ALTER TABLE fiscalite_annuelle\n                ADD COLUMN date_fin_reprise TEXT NOT NULL DEFAULT ''\n            ")
            connexion.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY,
                date_operation TEXT NOT NULL,
                libelle TEXT NOT NULL
                    CHECK (length(trim(libelle)) > 0),
                type_operation TEXT NOT NULL
                    CHECK (type_operation IN ('recette', 'depense')),
                montant_centiemes INTEGER NOT NULL
                    CHECK (montant_centiemes > 0)
            )
        """)
            connexion.execute("""
            CREATE TABLE IF NOT EXISTS devis (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                date_devis TEXT NOT NULL,
                objet TEXT NOT NULL DEFAULT '',
                statut TEXT NOT NULL DEFAULT 'brouillon'
                    CHECK (
                        statut IN (
                            'brouillon',
                            'envoye',
                            'accepte',
                            'refuse'
                        )
                    ),
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)
            connexion.execute("""
            CREATE TABLE IF NOT EXISTS devis_lignes (
                id INTEGER PRIMARY KEY,
                devis_id INTEGER NOT NULL,
                reference TEXT NOT NULL DEFAULT '',
                designation TEXT NOT NULL
                    CHECK (length(trim(designation)) > 0),
                unite TEXT NOT NULL
                    CHECK (length(trim(unite)) > 0),
                quantite_centiemes INTEGER NOT NULL
                    CHECK (quantite_centiemes > 0),
                prix_unitaire_centiemes INTEGER NOT NULL
                    CHECK (prix_unitaire_centiemes >= 0),
                taxe_centiemes INTEGER NOT NULL
                    CHECK (taxe_centiemes BETWEEN 0 AND 10000),
                FOREIGN KEY (devis_id) REFERENCES devis(id)
            )
        """)
            colonnes_devis = {ligne[1] for ligne in connexion.execute('PRAGMA table_info(devis)')}
            if 'validite_jours' not in colonnes_devis:
                connexion.execute('\n                ALTER TABLE devis\n                ADD COLUMN validite_jours INTEGER NOT NULL DEFAULT 30\n                CHECK (validite_jours BETWEEN 1 AND 365)\n            ')

    def ajouter_client(self, nom, telephone='', email='', adresse=''):
        nom = nom.strip()
        if not nom:
            raise ValueError('Le nom du client est obligatoire.')
        with self.session() as connexion:
            curseur = connexion.execute("""
            INSERT INTO clients (nom, telephone, email, adresse)
            VALUES (?, ?, ?, ?)
        """, (nom, telephone.strip(), email.strip(), adresse.strip()))
            return curseur.lastrowid

    def lister_clients(self):
        with self.session() as connexion:
            curseur = connexion.execute("""
            SELECT id, nom, telephone, email, adresse
            FROM clients
            ORDER BY nom, id
        """)
            return [dict(ligne) for ligne in curseur.fetchall()]

    def obtenir_client(self, client_id):
        with self.session() as connexion:
            curseur = connexion.execute("""
            SELECT id, nom, telephone, email, adresse
            FROM clients
            WHERE id = ?
        """, (client_id,))
            ligne = curseur.fetchone()
            if ligne is None:
                return None
            return dict(ligne)

    def modifier_client(self, client_id, nom, telephone='', email='', adresse=''):
        nom = nom.strip()
        if not nom:
            raise ValueError('Le nom du client est obligatoire.')
        with self.session() as connexion:
            curseur = connexion.execute("""
            UPDATE clients
            SET nom = ?, telephone = ?, email = ?, adresse = ?
            WHERE id = ?
        """, (nom, telephone.strip(), email.strip(), adresse.strip(), client_id))
            if curseur.rowcount == 0:
                raise ValueError('Client introuvable.')

    def convertir_en_centiemes(self, valeur):
        texte = str(valeur).strip().replace(',', '.')
        try:
            nombre = Decimal(texte)
        except InvalidOperation:
            raise ValueError('Saisissez une valeur numérique.') from None
        if not nombre.is_finite():
            raise ValueError('Saisissez une valeur numérique finie.')
        if nombre < 0:
            raise ValueError('La valeur ne peut pas être négative.')
        if nombre > Decimal('999999999999.99'):
            raise ValueError('La valeur est trop élevée.')
        nombre_precis = nombre.quantize(Decimal('0.01'))
        if nombre != nombre_precis:
            raise ValueError('La précision maximale est de deux décimales.')
        return int(nombre_precis * 100)

    def ajouter_article(self, reference, designation, type_article='produit', unite='pièce', prix_achat='0', prix_vente='0', taxe='0'):
        reference = reference.strip().upper()
        designation = designation.strip()
        type_article = type_article.strip().lower()
        unite = unite.strip()
        if not reference or not designation or (not unite):
            raise ValueError('Référence, désignation et unité obligatoires.')
        if type_article not in ('produit', 'service'):
            raise ValueError('Le type doit être produit ou service.')
        achat = self.convertir_en_centiemes(prix_achat)
        vente = self.convertir_en_centiemes(prix_vente)
        taux = self.convertir_en_centiemes(taxe)
        if taux > 10000:
            raise ValueError('Le taux de taxe doit être compris entre 0 et 100 %.')
        with self.session() as connexion:
            try:
                curseur = connexion.execute("""
            INSERT INTO articles (
                reference,
                designation,
                type_article,
                unite,
                prix_achat_centiemes,
                prix_vente_centiemes,
                taxe_centiemes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (reference, designation, type_article, unite, achat, vente, taux))
                return curseur.lastrowid
            except sqlite3.IntegrityError as erreur:
                if 'UNIQUE constraint failed: articles.reference' in str(erreur):
                    raise ValueError('Cette référence est déjà utilisée.') from None
                raise

    def lister_articles(self):
        with self.session() as connexion:
            curseur = connexion.execute("""
            SELECT id, reference, designation, type_article, unite,
                   prix_achat_centiemes, prix_vente_centiemes,
                   taxe_centiemes
            FROM articles
            ORDER BY designation, id
        """)
            return [dict(ligne) for ligne in curseur.fetchall()]

    def obtenir_article(self, article_id):
        with self.session() as connexion:
            ligne = connexion.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
            return dict(ligne) if ligne else None

    def modifier_article(self, article_id, reference, designation, type_article, unite, prix_achat, prix_vente, taxe):
        reference = reference.strip().upper()
        designation = designation.strip()
        type_article = type_article.strip().lower()
        unite = unite.strip()
        if not reference or not designation or (not unite):
            raise ValueError('Référence, désignation et unité obligatoires.')
        if type_article not in ('produit', 'service'):
            raise ValueError('Le type doit être produit ou service.')
        achat = self.convertir_en_centiemes(prix_achat)
        vente = self.convertir_en_centiemes(prix_vente)
        taux = self.convertir_en_centiemes(taxe)
        if taux > 10000:
            raise ValueError('Le taux de taxe doit être compris entre 0 et 100 %.')
        with self.session() as connexion:
            try:
                curseur = connexion.execute("""
            UPDATE articles
            SET reference = ?,
                designation = ?,
                type_article = ?,
                unite = ?,
                prix_achat_centiemes = ?,
                prix_vente_centiemes = ?,
                taxe_centiemes = ?
            WHERE id = ?
            """, (reference, designation, type_article, unite, achat, vente, taux, article_id))
                if curseur.rowcount == 0:
                    raise ValueError('Article introuvable.')
            except sqlite3.IntegrityError as erreur:
                if 'UNIQUE constraint failed: articles.reference' in str(erreur):
                    raise ValueError('Cette référence est déjà utilisée.') from None
                raise

    def supprimer_article(self, article_id):
        with self.session() as connexion:
            curseur = connexion.execute('DELETE FROM articles WHERE id = ?', (article_id,))
            if curseur.rowcount == 0:
                raise ValueError('Article introuvable.')

    def obtenir_entreprise(self):
        with self.session() as connexion:
            ligne = connexion.execute('SELECT * FROM entreprise WHERE id = 1').fetchone()
            return dict(ligne) if ligne else None

    def modifier_entreprise(self, nom, responsable='', telephone='', email='', adresse='', numero_tahiti='', numero_rcs=''):
        nom = nom.strip()
        if not nom:
            raise ValueError('Le nom de l’entreprise est obligatoire.')
        with self.session() as connexion:
            curseur = connexion.execute("""
            UPDATE entreprise
            SET nom = ?,
                responsable = ?,
                telephone = ?,
                email = ?,
                adresse = ?,
                numero_tahiti = ?,
                numero_rcs = ?
            WHERE id = 1
            """, (nom, responsable.strip(), telephone.strip(), email.strip(), adresse.strip(), numero_tahiti.strip(), numero_rcs.strip()))
            if curseur.rowcount == 0:
                raise ValueError('La fiche entreprise est introuvable.')

    def verifier_date_fiscale(self, valeur, libelle):
        texte = valeur.strip()
        if not texte:
            return ''
        try:
            date_valide = date.fromisoformat(texte)
        except ValueError:
            raise ValueError(f'{libelle} : date invalide.') from None
        return date_valide.isoformat()

    def enregistrer_debut_activite(self, valeur):
        texte = self.verifier_date_fiscale(valeur, 'Début d’activité')
        if not texte:
            raise ValueError('La date de début d’activité est obligatoire.')
        if date.fromisoformat(texte) > date.today():
            raise ValueError('Le début d’activité ne peut pas être futur.')
        with self.session() as connexion:
            curseur = connexion.execute("""
            UPDATE entreprise
            SET date_debut_activite = ?
            WHERE id = 1
            """, (texte,))
            if curseur.rowcount == 0:
                raise ValueError('Fiche entreprise introuvable.')

    def obtenir_fiscalite_annuelle(self, annee):
        with self.session() as connexion:
            ligne = connexion.execute("""
            SELECT *
            FROM fiscalite_annuelle
            WHERE annee = ?
            """, (annee,)).fetchone()
            return dict(ligne) if ligne else None

    def enregistrer_fiscalite_annuelle(self, annee, ca_n1='', date_effet_option_reel='', date_depassement=''):
        try:
            annee = int(str(annee).strip())
        except ValueError:
            raise ValueError('L’année est invalide.') from None
        if not 1900 <= annee <= 9999:
            raise ValueError('L’année est invalide.')
        ca_texte = str(ca_n1).strip()
        ca_centiemes = self.convertir_en_centiemes(ca_texte) if ca_texte else None
        option = self.verifier_date_fiscale(date_effet_option_reel, 'Date d’effet de l’option pour le réel')
        depassement = self.verifier_date_fiscale(date_depassement, 'Date de dépassement')
        if depassement:
            jour = date.fromisoformat(depassement)
            if jour.year != annee:
                raise ValueError('Le dépassement doit appartenir à l’année indiquée.')
            if jour > date.today():
                raise ValueError('Un dépassement constaté ne peut pas être futur.')
        with self.session() as connexion:
            connexion.execute("""
            INSERT INTO fiscalite_annuelle (
                annee,
                ca_n1_centiemes,
                date_effet_option_reel,
                date_depassement
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(annee) DO UPDATE SET
                ca_n1_centiemes = excluded.ca_n1_centiemes,
                date_effet_option_reel =
                    excluded.date_effet_option_reel,
                date_depassement = excluded.date_depassement
            """, (annee, ca_centiemes, option, depassement))

    def enregistrer_reprise_mensuelle(self, annee, mois, recettes='', depenses='', verifie=False):
        try:
            annee = int(str(annee).strip())
            mois = int(str(mois).strip())
        except ValueError:
            raise ValueError('Année ou mois invalide.') from None
        if not 1900 <= annee <= 9999:
            raise ValueError('Année invalide.')
        if not 1 <= mois <= 12:
            raise ValueError('Mois invalide.')
        recettes_texte = str(recettes).strip()
        depenses_texte = str(depenses).strip()
        recettes_centiemes = self.convertir_en_centiemes(recettes_texte) if recettes_texte else None
        depenses_centiemes = self.convertir_en_centiemes(depenses_texte) if depenses_texte else None
        if verifie and (recettes_centiemes is None or depenses_centiemes is None):
            raise ValueError('Renseignez les recettes et les dépenses avant de valider le mois. Saisissez 0 si le montant est réellement nul.')
        with self.session() as connexion:
            connexion.execute("""
            INSERT INTO reprise_mensuelle (
                annee,
                mois,
                recettes_centiemes,
                depenses_centiemes,
                verifie
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(annee, mois) DO UPDATE SET
                recettes_centiemes = excluded.recettes_centiemes,
                depenses_centiemes = excluded.depenses_centiemes,
                verifie = excluded.verifie
            """, (annee, mois, recettes_centiemes, depenses_centiemes, int(bool(verifie))))

    def lister_reprise_mensuelle(self, annee):
        with self.session() as connexion:
            lignes = connexion.execute("""
            SELECT *
            FROM reprise_mensuelle
            WHERE annee = ?
            ORDER BY mois
            """, (annee,)).fetchall()
            return [dict(ligne) for ligne in lignes]

    def enregistrer_fin_reprise(self, annee, valeur):
        texte = self.verifier_date_fiscale(valeur, 'Date de fin de reprise')
        if not texte:
            raise ValueError('La date de fin de reprise est obligatoire.')
        fin = date.fromisoformat(texte)
        if fin.year != annee:
            raise ValueError('La date doit appartenir à l’année affichée.')
        if fin > date.today():
            raise ValueError('La date ne peut pas être future.')
        entreprise = self.obtenir_entreprise()
        if entreprise and entreprise['date_debut_activite']:
            debut = date.fromisoformat(entreprise['date_debut_activite'])
            if fin < debut:
                raise ValueError('La reprise ne peut pas finir avant le début d’activité.')
        with self.session() as connexion:
            connexion.execute("""
            INSERT INTO fiscalite_annuelle (
                annee, date_fin_reprise
            )
            VALUES (?, ?)
            ON CONFLICT(annee) DO UPDATE SET
                date_fin_reprise = excluded.date_fin_reprise
            """, (annee, texte))

    def verifier_reprise(self, annee):
        entreprise = self.obtenir_entreprise()
        fiscalite = self.obtenir_fiscalite_annuelle(annee)
        if not entreprise or not entreprise['date_debut_activite']:
            return {'complete': False, 'message': 'Renseignez la date de début d’activité.', 'mois_manquants': []}
        if not fiscalite or not fiscalite['date_fin_reprise']:
            return {'complete': False, 'message': 'Renseignez la date de fin de reprise.', 'mois_manquants': []}
        debut = date.fromisoformat(entreprise['date_debut_activite'])
        fin = date.fromisoformat(fiscalite['date_fin_reprise'])
        if fin.year != annee or fin < debut:
            return {'complete': False, 'message': 'La période de reprise est incohérente.', 'mois_manquants': []}
        premier_mois = debut.month if debut.year == annee else 1
        lignes = {ligne['mois']: ligne for ligne in self.lister_reprise_mensuelle(annee)}
        manquants = []
        for mois in range(premier_mois, fin.month + 1):
            ligne = lignes.get(mois)
            if ligne is None or ligne['recettes_centiemes'] is None or ligne['depenses_centiemes'] is None or (not ligne['verifie']):
                manquants.append(mois)
        hors_periode = [mois for mois in lignes if mois < premier_mois or mois > fin.month]
        if hors_periode:
            return {'complete': False, 'message': 'Des mois saisis sont hors de la période de reprise. Vérifiez la période avant de continuer.', 'mois_manquants': manquants}
        return {'complete': not manquants, 'message': 'Tous les mois attendus sont renseignés et vérifiés.' if not manquants else 'La reprise reste à compléter.', 'mois_manquants': manquants}

    def enregistrer_ca_n1(self, annee, valeur):
        texte = str(valeur).strip()
        montant = self.convertir_en_centiemes(texte) if texte else None
        with self.session() as connexion:
            connexion.execute("""
            INSERT INTO fiscalite_annuelle (
                annee, ca_n1_centiemes
            )
            VALUES (?, ?)
            ON CONFLICT(annee) DO UPDATE SET
                ca_n1_centiemes = excluded.ca_n1_centiemes
            """, (annee, montant))

    def enregistrer_option_reel(self, annee, valeur):
        texte = self.verifier_date_fiscale(valeur, 'Date d’effet de l’option pour le réel')
        if texte:
            effet = date.fromisoformat(texte)
            if effet.year > annee:
                raise ValueError('Cette option prend effet après l’année affichée.')
        with self.session() as connexion:
            connexion.execute("""
            INSERT INTO fiscalite_annuelle (
                annee, date_effet_option_reel
            )
            VALUES (?, ?)
            ON CONFLICT(annee) DO UPDATE SET
                date_effet_option_reel =
                    excluded.date_effet_option_reel
            """, (annee, texte))

    def proposer_regime_tva(self, annee):
        entreprise = self.obtenir_entreprise() or {}
        fiscalite = self.obtenir_fiscalite_annuelle(annee) or {}
        debut_texte = entreprise.get('date_debut_activite', '')
        option_texte = fiscalite.get('date_effet_option_reel', '')
        ca_n1 = fiscalite.get('ca_n1_centiemes')
        date_reference = date.today() if annee == date.today().year else date(annee, 12, 31)
        depassement_texte = fiscalite.get('date_depassement', '')
        if depassement_texte:
            jour = date.fromisoformat(depassement_texte)
            debut_tva = date(jour.year + 1, 1, 1) if jour.month == 12 else date(jour.year, jour.month + 1, 1)
            effet_option = date.fromisoformat(option_texte) if option_texte else None
            if effet_option is None or effet_option > date_reference:
                if date_reference >= debut_tva:
                    return {'titre': 'Régime réel — dépassement renseigné', 'message': f'D’après le dépassement enregistré, la TVA est applicable depuis le {debut_tva:%d/%m/%Y}.'}
                return {'titre': 'Passage au réel à venir', 'message': f'D’après le dépassement enregistré, la TVA sera applicable à partir du {debut_tva:%d/%m/%Y}. Le régime antérieur reste à vérifier.'}
        if option_texte:
            effet = date.fromisoformat(option_texte)
            if effet <= date_reference:
                return {'titre': 'Régime réel — option renseignée', 'message': 'Une option déclarée comme en vigueur prend effet au plus tard à la date examinée.'}
            return {'titre': 'Option à venir', 'message': 'L’option renseignée n’a pas encore pris effet. Le régime applicable avant cette date reste à déterminer.'}
        if not debut_texte:
            return {'titre': 'Informations manquantes', 'message': 'Renseignez la date de début d’activité.'}
        debut = date.fromisoformat(debut_texte)
        if debut > date_reference:
            return {'titre': 'Activité non commencée', 'message': 'Le début d’activité est postérieur à la période examinée.'}
        if debut.year == annee:
            return {'titre': 'Première année d’activité', 'message': 'Le CA N−1 ne détermine pas le régime. Il faut contrôler le seuil de démarrage et le chiffre d’affaires de l’année en cours.'}
        if ca_n1 is None:
            return {'titre': 'CA précédent manquant', 'message': 'Renseignez le CA de l’année précédente. Un montant inconnu ne vaut pas zéro.'}
        seuil_centiemes = 10000000 * 100
        if ca_n1 > seuil_centiemes:
            return {'titre': 'Régime réel à prévoir', 'message': 'Le CA précédent dépasse 10 000 000 F CFP. Les éventuelles exonérations doivent être examinées séparément.'}
        if debut.year == annee - 1 and debut != date(annee - 1, 1, 1):
            return {'titre': 'Première année précédente incomplète', 'message': 'L’activité a commencé en cours d’année N−1. Le contrôle du prorata doit être ajouté avant de proposer la franchise.'}
        return {'titre': 'Franchise en base envisageable', 'message': 'Le CA précédent ne dépasse pas 10 000 000 F CFP. Il reste à vérifier l’historique du régime et tout dépassement pendant l’année en cours. Ce résultat ne valide pas une sortie du régime réel.'}

    def enregistrer_depassement(self, annee, valeur):
        texte = self.verifier_date_fiscale(valeur, 'Date de dépassement')
        if texte:
            jour = date.fromisoformat(texte)
            if jour.year != annee:
                raise ValueError('Le dépassement doit appartenir à l’année affichée.')
            if jour > date.today():
                raise ValueError('Le dépassement ne peut pas être futur.')
            entreprise = self.obtenir_entreprise() or {}
            debut = entreprise.get('date_debut_activite', '')
            if debut and jour < date.fromisoformat(debut):
                raise ValueError('Le dépassement ne peut pas précéder le début d’activité.')
        with self.session() as connexion:
            connexion.execute("""
            INSERT INTO fiscalite_annuelle (
                annee, date_depassement
            )
            VALUES (?, ?)
            ON CONFLICT(annee) DO UPDATE SET
                date_depassement = excluded.date_depassement
            """, (annee, texte))

    def obtenir_date_tva_depassement(self, annee):
        fiscalite = self.obtenir_fiscalite_annuelle(annee) or {}
        texte = fiscalite.get('date_depassement', '')
        if not texte:
            return ''
        jour = date.fromisoformat(texte)
        if jour.month == 12:
            debut_tva = date(jour.year + 1, 1, 1)
        else:
            debut_tva = date(jour.year, jour.month + 1, 1)
        return debut_tva.strftime('%d/%m/%Y')

    def ajouter_operation(self, date_operation, libelle, type_operation, montant):
        date_texte = self.verifier_date_fiscale(date_operation, 'Date de l’opération')
        if not date_texte:
            raise ValueError('La date est obligatoire.')
        jour = date.fromisoformat(date_texte)
        if jour > date.today():
            raise ValueError('Une opération réalisée ne peut pas être future.')
        libelle = libelle.strip()
        type_operation = type_operation.strip()
        if not libelle:
            raise ValueError('Le libellé est obligatoire.')
        if type_operation not in ('recette', 'depense'):
            raise ValueError('Le type d’opération est invalide.')
        montant_centiemes = self.convertir_en_centiemes(montant)
        if montant_centiemes == 0:
            raise ValueError('Le montant doit être supérieur à zéro.')
        entreprise = self.obtenir_entreprise() or {}
        debut = entreprise.get('date_debut_activite', '')
        if not debut:
            raise ValueError('Renseignez d’abord le début d’activité dans la fiche entreprise.')
        if jour < date.fromisoformat(debut):
            raise ValueError('L’opération ne peut pas précéder le début d’activité.')
        fiscalite = self.obtenir_fiscalite_annuelle(jour.year) or {}
        fin_reprise = fiscalite.get('date_fin_reprise', '')
        if fin_reprise and jour <= date.fromisoformat(fin_reprise):
            raise ValueError('Cette date appartient à la période reprise. Corrigez les montants dans la reprise mensuelle.')
        with self.session() as connexion:
            curseur = connexion.execute("""
            INSERT INTO operations (
                date_operation,
                libelle,
                type_operation,
                montant_centiemes
            )
            VALUES (?, ?, ?, ?)
            """, (date_texte, libelle, type_operation, montant_centiemes))
            return curseur.lastrowid

    def lister_operations(self, annee):
        from coffre import ACTIF
        if ACTIF is not None and ACTIF.compte.get('role') != 'admin':
            raise PermissionError('Action réservée à l’administrateur.')
        with self.session() as connexion:
            lignes = connexion.execute("""
            SELECT *
            FROM operations
            WHERE date_operation BETWEEN ? AND ?
            ORDER BY date_operation DESC, id DESC
            """, (f'{annee:04d}-01-01', f'{annee:04d}-12-31')).fetchall()
            return [dict(ligne) for ligne in lignes]

    def obtenir_operation(self, operation_id):
        from coffre import ACTIF
        if ACTIF is not None and ACTIF.compte.get('role') != 'admin':
            raise PermissionError('Action réservée à l’administrateur.')
        with self.session() as connexion:
            ligne = connexion.execute('SELECT * FROM operations WHERE id = ?', (operation_id,)).fetchone()
            return dict(ligne) if ligne else None

    def supprimer_operation(self, operation_id):
        from coffre import ACTIF
        if ACTIF is not None and ACTIF.compte.get('role') != 'admin':
            raise PermissionError('Action réservée à l’administrateur.')
        with self.session() as connexion:
            curseur = connexion.execute('DELETE FROM operations WHERE id = ?', (operation_id,))
            if curseur.rowcount == 0:
                raise ValueError('Opération introuvable.')

    def modifier_operation(self, operation_id, date_operation, libelle, type_operation, montant):
        from coffre import ACTIF
        if ACTIF is not None and ACTIF.compte.get('role') != 'admin':
            raise PermissionError('Action réservée à l’administrateur.')
        date_texte = self.verifier_date_fiscale(date_operation, 'Date de l’opération')
        if not date_texte:
            raise ValueError('La date est obligatoire.')
        jour = date.fromisoformat(date_texte)
        if jour > date.today():
            raise ValueError('Une opération réalisée ne peut pas être future.')
        libelle = libelle.strip()
        type_operation = type_operation.strip()
        if not libelle:
            raise ValueError('Le libellé est obligatoire.')
        if type_operation not in ('recette', 'depense'):
            raise ValueError('Le type d’opération est invalide.')
        montant_centiemes = self.convertir_en_centiemes(montant)
        if montant_centiemes == 0:
            raise ValueError('Le montant doit être supérieur à zéro.')
        entreprise = self.obtenir_entreprise() or {}
        debut = entreprise.get('date_debut_activite', '')
        if not debut:
            raise ValueError('Renseignez d’abord le début d’activité dans la fiche entreprise.')
        if jour < date.fromisoformat(debut):
            raise ValueError('L’opération ne peut pas précéder le début d’activité.')
        fiscalite = self.obtenir_fiscalite_annuelle(jour.year) or {}
        fin_reprise = fiscalite.get('date_fin_reprise', '')
        if fin_reprise and jour <= date.fromisoformat(fin_reprise):
            raise ValueError('Cette date appartient à la période reprise. Corrigez les montants dans la reprise mensuelle.')
        with self.session() as connexion:
            curseur = connexion.execute("""
            UPDATE operations
            SET date_operation = ?,
                libelle = ?,
                type_operation = ?,
                montant_centiemes = ?
            WHERE id = ?
            """, (date_texte, libelle, type_operation, montant_centiemes, operation_id))
            if curseur.rowcount == 0:
                raise ValueError('Opération introuvable.')

    def obtenir_resume_annuel(self, annee):
        from coffre import ACTIF
        if ACTIF is not None and ACTIF.compte.get('role') != 'admin':
            raise PermissionError('Action réservée à l’administrateur.')
        reprises = self.lister_reprise_mensuelle(annee)
        operations = self.lister_operations(annee)
        fiscalite = self.obtenir_fiscalite_annuelle(annee) or {}
        controle = self.verifier_reprise(annee)
        fin_texte = fiscalite.get('date_fin_reprise', '')
        fin = date.fromisoformat(fin_texte) if fin_texte else None
        entreprise = self.obtenir_entreprise() or {}
        debut_texte = entreprise.get('date_debut_activite', '')
        debut = date.fromisoformat(debut_texte) if debut_texte else None
        alertes = []
        if reprises and (not controle['complete']):
            alertes.append(controle['message'])
        if fin and (not controle['complete']) and (not reprises):
            alertes.append(controle['message'])
        if not debut:
            alertes.append('La date de début d’activité manque.')
        premier_mois = debut.month if debut and debut.year == annee else 1
        reprises_retenues = [ligne for ligne in reprises if fin and debut and (fin.year == annee) and (fin >= debut) and (premier_mois <= ligne['mois'] <= fin.month)]
        if reprises and (not fin):
            alertes.append('Les montants de reprise sont exclus du total : renseignez la date de fin de reprise.')
        operations_retenues = []
        chevauchements = 0
        for operation in operations:
            jour = date.fromisoformat(operation['date_operation'])
            if fin and jour <= fin:
                chevauchements += 1
            else:
                operations_retenues.append(operation)
        if chevauchements:
            alertes.append(f'{chevauchements} opération(s) du journal se trouvent dans la période reprise. Elles sont exclues du total pour éviter un double compte. Vérifiez ces lignes.')
        recettes = sum((ligne['recettes_centiemes'] for ligne in reprises_retenues if ligne['recettes_centiemes'] is not None))
        depenses = sum((ligne['depenses_centiemes'] for ligne in reprises_retenues if ligne['depenses_centiemes'] is not None))
        for operation in operations_retenues:
            if operation['type_operation'] == 'recette':
                recettes += operation['montant_centiemes']
            else:
                depenses += operation['montant_centiemes']
        return {'recettes': recettes, 'depenses': depenses, 'difference': recettes - depenses, 'alertes': alertes}

    def obtenir_resume_mensuel(self, annee):
        entreprise = self.obtenir_entreprise() or {}
        fiscalite = self.obtenir_fiscalite_annuelle(annee) or {}
        debut_texte = entreprise.get('date_debut_activite', '')
        fin_texte = fiscalite.get('date_fin_reprise', '')
        debut = date.fromisoformat(debut_texte) if debut_texte else None
        fin = date.fromisoformat(fin_texte) if fin_texte else None
        resume = {mois: {'mois': mois, 'recettes': 0, 'depenses': 0} for mois in range(1, 13)}
        premier_mois = debut.month if debut and debut.year == annee else 1
        if debut and fin and (fin.year == annee) and (fin >= debut):
            for ligne in self.lister_reprise_mensuelle(annee):
                mois = ligne['mois']
                if premier_mois <= mois <= fin.month:
                    if ligne['recettes_centiemes'] is not None:
                        resume[mois]['recettes'] += ligne['recettes_centiemes']
                    if ligne['depenses_centiemes'] is not None:
                        resume[mois]['depenses'] += ligne['depenses_centiemes']
        for operation in self.lister_operations(annee):
            jour = date.fromisoformat(operation['date_operation'])
            if fin and jour <= fin:
                continue
            champ = 'recettes' if operation['type_operation'] == 'recette' else 'depenses'
            resume[jour.month][champ] += operation['montant_centiemes']
        for ligne in resume.values():
            ligne['difference'] = ligne['recettes'] - ligne['depenses']
        return list(resume.values())

    def creer_devis(self, client_id, date_devis, objet=''):
        date_texte = self.verifier_date_fiscale(date_devis, 'Date du devis')
        if not date_texte:
            raise ValueError('La date du devis est obligatoire.')
        with self.session() as connexion:
            connexion.execute('PRAGMA foreign_keys = ON')
            client = connexion.execute('SELECT id FROM clients WHERE id = ?', (client_id,)).fetchone()
            if client is None:
                raise ValueError('Le client est introuvable.')
            curseur = connexion.execute("""
            INSERT INTO devis (
                client_id,
                date_devis,
                objet
            )
            VALUES (?, ?, ?)
            """, (client_id, date_texte, objet.strip()))
            return curseur.lastrowid

    def lister_devis(self):
        with self.session() as connexion:
            lignes = connexion.execute('\n            SELECT\n                devis.id,\n                devis.date_devis,\n                devis.objet,\n                devis.statut,\n                clients.nom AS nom_client\n            FROM devis\n            JOIN clients ON clients.id = devis.client_id\n            ORDER BY devis.date_devis DESC, devis.id DESC\n            ').fetchall()
            return [dict(ligne) for ligne in lignes]

    def obtenir_devis(self, devis_id):
        with self.session() as connexion:
            ligne = connexion.execute('\n            SELECT\n                devis.*,\n                clients.nom AS nom_client\n            FROM devis\n            JOIN clients ON clients.id = devis.client_id\n            WHERE devis.id = ?\n            ', (devis_id,)).fetchone()
            return dict(ligne) if ligne else None

    def lister_lignes_devis(self, devis_id):
        with self.session() as connexion:
            lignes = connexion.execute("""
            SELECT *
            FROM devis_lignes
            WHERE devis_id = ?
            ORDER BY id
            """, (devis_id,)).fetchall()
            return [dict(ligne) for ligne in lignes]

    def ajouter_ligne_devis(self, devis_id, designation, unite, quantite, prix_unitaire, taxe, reference='', enregistrer_catalogue=False, type_article='produit'):
        designation = designation.strip()
        unite = unite.strip()
        reference = reference.strip().upper()
        if not designation or not unite:
            raise ValueError('La désignation et l’unité sont obligatoires.')
        quantite_centiemes = self.convertir_en_centiemes(quantite)
        prix_centiemes = self.convertir_en_centiemes(prix_unitaire)
        taux_centiemes = self.convertir_en_centiemes(taxe)
        if quantite_centiemes == 0:
            raise ValueError('La quantité doit être supérieure à zéro.')
        if taux_centiemes > 10000:
            raise ValueError('La TVA doit être comprise entre 0 et 100 %.')
        if enregistrer_catalogue:
            if not reference:
                raise ValueError('Une référence est obligatoire pour le catalogue.')
            type_article = type_article.strip().lower()
            if type_article not in ('produit', 'service'):
                raise ValueError('Choisissez produit ou prestation.')
        with self.session() as connexion:
            try:
                connexion.execute('PRAGMA foreign_keys = ON')
                connexion.execute('BEGIN')
                devis = connexion.execute('SELECT statut FROM devis WHERE id = ?', (devis_id,)).fetchone()
                if devis is None:
                    raise ValueError('Devis introuvable.')
                if devis[0] != 'brouillon':
                    raise ValueError('Seul un devis en brouillon peut être modifié.')
                if enregistrer_catalogue:
                    connexion.execute("""
                INSERT INTO articles (
                    reference,
                    designation,
                    type_article,
                    unite,
                    prix_achat_centiemes,
                    prix_vente_centiemes,
                    taxe_centiemes
                )
                VALUES (?, ?, ?, ?, 0, ?, ?)
                """, (reference, designation, type_article, unite, prix_centiemes, taux_centiemes))
                curseur = connexion.execute("""
            INSERT INTO devis_lignes (
                devis_id,
                reference,
                designation,
                unite,
                quantite_centiemes,
                prix_unitaire_centiemes,
                taxe_centiemes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (devis_id, reference, designation, unite, quantite_centiemes, prix_centiemes, taux_centiemes))
                return curseur.lastrowid
            except sqlite3.IntegrityError as erreur:
                connexion.rollback()
                if 'UNIQUE constraint failed: articles.reference' in str(erreur):
                    raise ValueError('Cette référence existe déjà dans le catalogue. Choisissez une autre référence ou ajoutez l’article depuis le catalogue.') from None
                raise
            except Exception:
                connexion.rollback()
                raise

    def obtenir_ligne_devis(self, devis_id, ligne_id):
        with self.session() as connexion:
            ligne = connexion.execute("""
            SELECT *
            FROM devis_lignes
            WHERE id = ? AND devis_id = ?
            """, (ligne_id, devis_id)).fetchone()
            return dict(ligne) if ligne else None

    def modifier_ligne_devis(self, devis_id, ligne_id, designation, unite, quantite, prix_unitaire, taxe, reference=''):
        designation = designation.strip()
        unite = unite.strip()
        reference = reference.strip()
        if not designation or not unite:
            raise ValueError('La désignation et l’unité sont obligatoires.')
        quantite_centiemes = self.convertir_en_centiemes(quantite)
        prix_centiemes = self.convertir_en_centiemes(prix_unitaire)
        taux_centiemes = self.convertir_en_centiemes(taxe)
        if quantite_centiemes == 0:
            raise ValueError('La quantité doit être supérieure à zéro.')
        if taux_centiemes > 10000:
            raise ValueError('La TVA doit être comprise entre 0 et 100 %.')
        with self.session() as connexion:
            devis = connexion.execute('SELECT statut FROM devis WHERE id = ?', (devis_id,)).fetchone()
            if devis is None:
                raise ValueError('Devis introuvable.')
            if devis[0] != 'brouillon':
                raise ValueError('Seul un devis en brouillon peut être modifié.')
            curseur = connexion.execute("""
            UPDATE devis_lignes
            SET reference = ?,
                designation = ?,
                unite = ?,
                quantite_centiemes = ?,
                prix_unitaire_centiemes = ?,
                taxe_centiemes = ?
            WHERE id = ? AND devis_id = ?
            """, (reference, designation, unite, quantite_centiemes, prix_centiemes, taux_centiemes, ligne_id, devis_id))
            if curseur.rowcount == 0:
                raise ValueError('Ligne de devis introuvable.')

    def supprimer_ligne_devis(self, devis_id, ligne_id):
        with self.session() as connexion:
            devis = connexion.execute('SELECT statut FROM devis WHERE id = ?', (devis_id,)).fetchone()
            if devis is None:
                raise ValueError('Devis introuvable.')
            if devis[0] != 'brouillon':
                raise ValueError('Seul un devis en brouillon peut être modifié.')
            curseur = connexion.execute("""
            DELETE FROM devis_lignes
            WHERE id = ? AND devis_id = ?
            """, (ligne_id, devis_id))
            if curseur.rowcount == 0:
                raise ValueError('Ligne de devis introuvable.')

    def determiner_tva_devis(self, date_devis):
        jour = date.fromisoformat(date_devis)
        fiscalite = self.obtenir_fiscalite_annuelle(jour.year) or {}
        option = fiscalite.get('date_effet_option_reel', '')
        depassement = fiscalite.get('date_depassement', '')
        ca_n1 = fiscalite.get('ca_n1_centiemes')
        if option and date.fromisoformat(option) <= jour:
            return {'applicable': True, 'message': 'TVA applicable : option pour le réel renseignée.'}
        if depassement:
            date_depassement = date.fromisoformat(depassement)
            debut_tva = date(date_depassement.year + 1, 1, 1) if date_depassement.month == 12 else date(date_depassement.year, date_depassement.month + 1, 1)
            if jour >= debut_tva:
                return {'applicable': True, 'message': 'TVA applicable : dépassement renseigné.'}
        if ca_n1 is not None and ca_n1 > 10000000 * 100:
            return {'applicable': True, 'message': 'TVA applicable d’après le CA précédent, sous réserve des exonérations propres aux opérations.'}
        return {'applicable': None, 'message': 'Régime de TVA à vérifier pour la date du devis. Le CA seul ne confirme pas la franchise : l’historique fiscal et le contrôle du seuil restent nécessaires.'}

    def modifier_validite_devis(self, devis_id, validite_jours):
        try:
            jours = int(str(validite_jours).strip())
        except ValueError:
            raise ValueError('La validité doit être un nombre entier de jours.') from None
        if not 1 <= jours <= 365:
            raise ValueError('La validité doit être comprise entre 1 et 365 jours.')
        with self.session() as connexion:
            curseur = connexion.execute("""
            UPDATE devis
            SET validite_jours = ?
            WHERE id = ? AND statut = 'brouillon'
            """, (jours, devis_id))
            if curseur.rowcount == 0:
                raise ValueError('Devis introuvable ou déjà sorti du brouillon.')

base = BaseDonnees()

def __getattr__(nom):
    # Compatibilité des anciennes interfaces ; le code métier utilise les objets.
    return getattr(base, nom)

if __name__ == '__main__':
    base.initialiser_base()
    print(f'Base prête : {base.chemin}')
