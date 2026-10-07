# SPDX-License-Identifier: GPL-3.0-or-later
"""Petits outils communs de la bêta : relances, export et état des sauvegardes."""
import csv
import io
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode
import database as db
import gestion as g

NOUVEAUTES = ('Un démarrage guidé en quatre étapes.', 'Recherche dans les clients, devis et factures selon vos droits.',
              'Relances de factures préparées par mail.', 'Alerte visible si la sauvegarde manque ou a échoué.',
              'Export CSV des recettes et dépenses pour l’administrateur.', 'Résumé des nouveautés après une mise à jour.')

def cellule_csv(valeur):
    s=str(valeur if valeur is not None else '')
    return "'"+s if s.lstrip().startswith(('=','+','-','@','\t','\r','\n')) else s

class ServicesBeta:
    def __init__(self, comptes, sauvegardes):self.comptes=comptes;self.sauvegardes=sauvegardes
    def etat_sauvegarde(self):
        c=self.sauvegardes.configuration()
        if not c.get('dossier'):return 'Choisissez le dossier de sauvegarde.'
        if c.get('erreur'):return 'La sauvegarde a échoué. Vérifiez le dossier choisi.'
        if not Path(c['dossier']).is_dir():return 'Le dossier de sauvegarde est inaccessible.'
        try:date=datetime.fromisoformat(c.get('derniere',''))
        except (ValueError,TypeError):return 'Aucune sauvegarde récente n’a été vérifiée.'
        if datetime.now()-date>timedelta(days=2):return 'La dernière sauvegarde date de plus de deux jours.'
        return ''
    def relance(self,identifiant):
        self.comptes.exiger_admin();d=g.document(identifiant)
        if d['type']!='facture' or d['reste']<=0:raise ValueError('Cette facture n’a aucun montant à relancer.')
        s=d['contenu'];email=s['client'].get('email','').strip()
        if not email and d.get('devis_id'):
            devis=db.obtenir_devis(d['devis_id'])
            client=db.obtenir_client(devis['client_id']) if devis else None
            email=(client or {}).get('email','').strip()
        if email and (any(c in email for c in '\r\n<>') or email.count('@')!=1):email=''
        montant=f"{Decimal(d['reste'])/100:,.2f}".replace(',',' ').replace('.',',')
        corps=f"Bonjour {s['client']['nom']},\n\nSauf erreur de notre part, il reste {montant} F CFP à régler pour la facture {d['numero']}, avec une échéance le {d['echeance']}.\n\nSi votre règlement a déjà été effectué, merci de nous en informer.\n\nMerci,\n{s['entreprise']['nom']}"
        return email,corps,'mailto:'+email+'?'+urlencode({'subject':'Rappel — facture '+d['numero'],'body':corps})
    def exporter_csv(self,annee,destination):
        self.comptes.exiger_admin();lignes=db.lister_operations(annee)
        flux=io.StringIO(newline='');w=csv.writer(flux,delimiter=';');w.writerow(['Date','Libellé','Type','Montant F CFP'])
        for r in lignes:w.writerow([r['date_operation'],cellule_csv(r['libelle']),r['type_operation'],format(Decimal(r['montant_centiemes'])/100,'.2f').replace('.',',')])
        p=Path(destination);p.write_text(flux.getvalue(),encoding='utf-8-sig',newline='');self.comptes.tracer('Export CSV',str(annee));return p
