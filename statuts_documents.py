# SPDX-License-Identifier: GPL-3.0-or-later
"""Repères d'affichage calculés, sans modifier les documents ni leur statut métier."""
import json
from datetime import date,timedelta


def etat(code,libelle,detail='',limite=''):
    return dict(code=code,libelle=libelle,detail=detail or libelle,limite=limite)


def statut_devis(devis,aujourdhui=None):
    aujourd=aujourdhui or date.today()
    statut=devis.get('statut','')
    if statut=='brouillon':return etat('neutre','Brouillon','Devis non émis : aucun délai en cours.')
    try:
        contenu=devis.get('instantane') or {}
        if isinstance(contenu,str):contenu=json.loads(contenu)
        limite=date.fromisoformat(contenu['validite']) if contenu.get('validite') else date.fromisoformat(devis['date_devis'])+timedelta(days=int(devis['validite_jours']))
        expiration=limite.isoformat()
    except (ValueError,KeyError,TypeError,OverflowError):
        expiration=''
    terminaux={'accepte':('vert','Accepté'),'refuse':('neutre','Refusé'),'facture':('violet','Facturé')}
    if statut in terminaux:
        code,libelle=terminaux[statut]
        return etat(code,libelle,'Décision déjà enregistrée : le délai du devis ne change pas ce statut.',expiration)
    if statut!='envoye' or not expiration:return etat('neutre','À vérifier','Statut ou date de validité à vérifier.',expiration)
    if date.fromisoformat(expiration)<aujourd:
        return etat('rouge','Hors délai','Validité du devis dépassée ; aucune décision enregistrée.',expiration)
    return etat('bleu','En cours','Devis émis, dans sa période de validité, en attente de décision.',expiration)


def statut_facture(document,aujourdhui=None,etat_avoir=None):
    if document.get('type')=='avoir':
        return etat('violet',(etat_avoir or {}).get('statut','Avoir'),'Avoir : son solde ne constitue pas une facture client en retard.')
    total=document['total_centiemes'];paye=document.get('paye',0);credite=document.get('credite',0)
    reste=max(0,total-paye-credite)
    if reste==0:
        if credite or document.get('impute',0):
            return etat('vert','Soldée avec avoir','Le solde est nul grâce à un avoir, éventuellement complété par un paiement.')
        return etat('vert','Réglée','Aucun montant ne reste à encaisser.')
    try:limite=date.fromisoformat(document['echeance'])
    except (ValueError,TypeError,KeyError):return etat('neutre','À vérifier','Échéance absente ou invalide ; un solde reste à encaisser.')
    if limite<(aujourdhui or date.today()):
        return etat('rouge','En retard','Échéance dépassée et solde restant dû, même en cas de règlement partiel.',limite.isoformat())
    return etat('orange','Règlement partiel' if paye else 'À régler','Un solde reste à encaisser ; l’échéance n’est pas dépassée.',limite.isoformat())
