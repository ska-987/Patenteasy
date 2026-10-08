# SPDX-License-Identifier: GPL-3.0-or-later
"""Réglages de l'entreprise et nombres exacts, indépendants du métier."""
from decimal import Decimal, InvalidOperation
from datetime import date

DEFAULTS = {'pays': '', 'devise': 'EUR', 'decimales': 2, 'format_date': 'dd/MM/yy',
            'langue': 'fr', 'nom_taxe': 'Taxe', 'mention_sans_taxe': '', 'libelle_identifiant': 'Identifiant professionnel'}
FORMATS = {'dd/MM/yy': 'JJ/MM/AA', 'MM/dd/yy': 'MM/JJ/AA', 'yyyy-MM-dd': 'AAAA-MM-JJ'}


def configuration(entreprise=None):
    if entreprise is None:
        try:
            import database as db
            entreprise = db.obtenir_entreprise() or {}
        except Exception:
            entreprise = DEFAULTS
    if 'devise' not in entreprise:
        return {**DEFAULTS, 'devise': entreprise.get('monnaie', 'XPF'), 'pays': 'PF', 'nom_taxe': 'TVA'}
    return {**DEFAULTS, **{k: entreprise.get(k, v) for k, v in DEFAULTS.items()}}


def convertir_montant(valeur, entreprise=None, signe=False):
    cfg = configuration(entreprise)
    try:
        nombre = Decimal(str(valeur).strip().replace(' ', '').replace('\u00a0', '').replace(',', '.'))
    except InvalidOperation:
        raise ValueError('Saisissez un montant numérique.') from None
    if not nombre.is_finite() or abs(nombre) > Decimal('999999999999.9999'):
        raise ValueError('Montant invalide.')
    if nombre < 0 and not signe:
        raise ValueError('Le montant ne peut pas être négatif.')
    facteur = 10 ** int(cfg['decimales'])
    if nombre * facteur != (nombre * facteur).to_integral_value():
        raise ValueError(f"La devise choisie utilise {cfg['decimales']} décimale(s).")
    return int(nombre * facteur)


def nombre(n, decimales=2, langue='fr', groupe=True):
    facteur = 10 ** decimales
    entier, fraction = divmod(abs(int(n)), facteur)
    txt = f'{entier:,}' if groupe else str(entier)
    sep = ',' if langue == 'fr' else '.'
    txt = txt.replace(',', ' ' if langue == 'fr' else ',')
    if fraction:
        txt += sep + f'{fraction:0{decimales}d}'
    return ('-' if n < 0 else '') + txt


def montant(n, entreprise=None, unite=True, saisie=False):
    if n is None:
        return '—' if not saisie else ''
    cfg = configuration(entreprise)
    txt = nombre(n, int(cfg['decimales']), cfg['langue'], not saisie)
    return txt + (' ' + cfg['devise'] if unite else '')


def afficher_date(texte, entreprise=None):
    if not texte:
        return ''
    try:
        jour = date.fromisoformat(texte)
    except (ValueError, TypeError):
        return str(texte)
    fmt = configuration(entreprise)['format_date']
    return jour.strftime({'dd/MM/yy':'%d/%m/%y', 'MM/dd/yy':'%m/%d/%y', 'yyyy-MM-dd':'%Y-%m-%d'}[fmt])
