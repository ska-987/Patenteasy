# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
"""Liens publics de publication : aucun identifiant de compte n'est conservé."""
import json
from pathlib import Path
from urllib.parse import urlsplit, urlencode


class ConfigurationEditeur:
    def __init__(self, chemin=None, local=None):
        self.local = Path(local) if local else None
        self.chemin = Path(chemin) if chemin else Path(__file__).with_name('configuration_editeur.json')

    def officiels(self):
        """Configuration livrée par l’éditeur, indépendante des anciens réglages locaux."""
        return json.loads(self.chemin.read_text(encoding="utf-8"))

    @staticmethod
    def demande_informations(email):
        import re
        email = str(email).strip()
        if len(email) > 254 or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", email):
            raise ValueError("Saisissez une adresse mail valide.")
        return "mailto:sav.centreprotech@proton.me?" + urlencode({
            "subject": "ska_987 — nouveautés et logiciels",
            "body": "Bonjour ska_987,\n\nJe souhaite être informé des nouveautés, des produits et des logiciels de ska_987.\n\nMon adresse mail : " + email + "\n\nMerci !\n"})

    def lire(self):
        donnees = json.loads(self.chemin.read_text(encoding='utf-8'))
        import database as db
        local = self.local or db.BASE_DIR / 'publication.json'
        if local.exists():
            donnees.update(json.loads(local.read_text(encoding='utf-8')))
        return donnees

    @staticmethod
    def lien(valeur, paypal=False):
        valeur = str(valeur).strip()
        if not valeur:
            return ''
        u = urlsplit(valeur)
        domaines = ('paypal.me', 'www.paypal.me', 'paypal.com', 'www.paypal.com') if paypal else ('drive.proton.me',)
        if u.scheme != 'https' or u.hostname not in domaines or u.username or u.password or u.port not in (None, 443):
            raise ValueError('Utilisez un lien public HTTPS de PayPal.' if paypal else 'Utilisez le lien public https://drive.proton.me/… de votre dossier Proton Drive.')
        return valeur

    def enregistrer(self, drive, paypal):
        donnees = self.lire()
        donnees.update(telechargements_url=self.lien(drive), paypal_url=self.lien(paypal, True))
        import database as db
        chemin = self.local or db.BASE_DIR / 'publication.json'
        temporaire = chemin.with_suffix('.tmp')
        temporaire.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporaire.replace(chemin)
        return donnees

    @staticmethod
    def demande_hebergement():
        corps = ('Bonjour ska_987,\n\nJe souhaite un devis pour un hébergement Patenteasy '
                 'permettant de relier téléphone et ordinateur, avec assistance personnalisée.\n\n'
                 'Entreprise :\nNombre de postes :\nNombre d’utilisateurs :\nTéléphone de contact :\n')
        return 'mailto:sav.centreprotech@proton.me?' + urlencode({'subject': 'Patenteasy — demande d’hébergement et assistance', 'body': corps})


editeur = ConfigurationEditeur()
