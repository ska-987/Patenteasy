# SPDX-License-Identifier: GPL-3.0-or-later
"""Petits outils communs de la bêta : relances, export et état des sauvegardes."""
import csv
import io
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode
import regional
import database as db
import gestion as g

ANCIENNES_NOUVEAUTES = ('Sélection lisible et désélection avec Échap.',
              'Formulaires et documents défilants.',
              'Conditions et mentions des devis repliables et facultatives.',
              'Choix de TVA sans dates ni attestation ; CA facultatif.',
              'Rappel de dépassement de 10 millions sans blocage.')

NOUVEAUTES = ('Pays, devise, précision et formats configurables.', 'Brouillons enregistrés automatiquement, même avec une date à compléter.', 'Aperçu PDF avant l’enregistrement du fichier.', 'Sauvegardes portables récupérables sur un nouveau PC.', 'Rappels fiscaux locaux informatifs.')

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
        montant=regional.montant(d['reste'],s['entreprise'])
        corps=f"Bonjour {s['client']['nom']},\n\nSauf erreur de notre part, il reste {montant} à régler pour la facture {d['numero']}, avec une échéance le {d['echeance']}.\n\nSi votre règlement a déjà été effectué, merci de nous en informer.\n\nMerci,\n{s['entreprise']['nom']}"
        return email,corps,'mailto:'+email+'?'+urlencode({'subject':'Rappel — facture '+d['numero'],'body':corps})
    def exporter_csv(self,annee,destination):
        self.comptes.exiger_admin();lignes=db.lister_operations(annee)
        flux=io.StringIO(newline='');w=csv.writer(flux,delimiter=';');w.writerow(['Date','Libellé','Type','Montant '+regional.configuration()['devise']])
        for r in lignes:w.writerow([r['date_operation'],cellule_csv(r['libelle']),r['type_operation'],regional.montant(r['montant_centiemes'],unite=False,saisie=True)])
        p=Path(destination);p.write_text(flux.getvalue(),encoding='utf-8-sig',newline='');self.comptes.tracer('Export CSV',str(annee));return p
