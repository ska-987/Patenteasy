# SPDX-License-Identifier: GPL-3.0-or-later
"""Calculs entiers et événements de TVA, indépendants des interfaces."""
from datetime import date

def entier(n, minimum=0):
    if type(n) is not int or n < minimum or n > 9_000_000_000_000: raise ValueError('Montant entier invalide.')
    return n

def jour(s):
    d = date.fromisoformat(s)
    if d.isoformat() != s: raise ValueError('Date invalide.')
    return s

def lignes_valides(lignes):
    if not lignes or len(lignes)>100: raise ValueError('Ajoutez entre 1 et 100 lignes.')
    resultat=[]
    for l in lignes:
        ht,taux=entier(l['ht']),entier(l['taux'])
        if taux>10000: raise ValueError('Taux supérieur à 100 %.')
        attendu=(ht*taux+5000)//10000
        tva=entier(l.get('tva',attendu));ttc=entier(l.get('ttc',ht+tva))
        if abs(tva-attendu)>1 or ttc!=ht+tva: raise ValueError('Vérifiez HT, taux, TVA et TTC ; tolérance d’arrondi : une unité monétaire minimale.')
        if l.get('nature') not in ('bien','service','debits'): raise ValueError('Choisissez biens, services ou débits autorisés.')
        deduction=entier(l.get('deduction',10000))
        if deduction>10000: raise ValueError('Part déductible invalide.')
        categorie=l.get('categorie','autres')
        if categorie not in ('achats','personnel','autres','immobilisation','cotisations_rns'): raise ValueError('Catégorie invalide.')
        resultat.append({**l,'ht':ht,'tva':tva,'ttc':ttc,'taux':taux,'deduction':deduction,'categorie':categorie})
    if sum(l['ttc'] for l in resultat)<=0: raise ValueError('Le total TTC doit être positif.')
    return resultat

def fraction(valeur, paye, total):
    return (valeur*min(paye,total)+total//2)//total if total else 0

def evenements(lignes,total,paiements,date_facture,date_livraison):
    """Biens : acomptes puis solde à la livraison. Services : encaissements.

    Les débits ne sont sélectionnés que si l'autorisation est confirmée par
    l'utilisateur. L'allocation des paiements suit le prorata TTC de la facture.
    """
    etapes={}
    for p in paiements:
        etapes[p['date']]=etapes.get(p['date'],0)+entier(p['montant'])
    if date_livraison: etapes.setdefault(date_livraison,0)
    etapes.setdefault(date_facture,0)
    deja=[(0,0,0) for l in lignes];paye=0;sortie=[]
    for d,montant in sorted(etapes.items()):
        paye+=montant
        for i,l in enumerate(lignes):
            nature=l.get('nature','inconnue')
            complet = (nature=='bien' and date_livraison and d>=date_livraison) or (nature=='debits' and d>=date_facture)
            ht=l['ht'] if complet else fraction(l['ht'],paye,total)
            tva=l['tva'] if complet else fraction(l['tva'],paye,total)
            ded=(tva*(l.get('deduction') or 0)+5000)//10000
            dh,dv=ht-deja[i][0],tva-deja[i][1]
            if dh or dv: sortie.append({'date':d,'ht':dh,'tva':dv,'ligne':i,'deduction_delta':ded-deja[i][2],**{k:l.get(k) for k in ('taux','nature','categorie','deduction')}})
            deja[i]=(ht,tva,ded)
    return sortie

def synthese(debut,fin,documents,achats,regime,credit=0,corrections=()):
    jour(debut);jour(fin);entier(credit)
    if fin<debut: raise ValueError('Période inversée.')
    groupes={};alertes=[];exigible=deductible=percue=0;deduction_immobilisation=0
    def ligne(taux):
        return groupes.setdefault(taux,{'taux':taux,'base_exigible':0,'tva_exigible':0,'tva_percue':0,'base_achats':0,'tva_achats':0,'tva_deductible':0})
    for doc in documents:
        if doc.get('incomplet'):alertes.append(doc['incomplet'])
        even=evenements(doc['lignes'],doc['ttc'],doc['paiements'],doc['date'],doc.get('livraison',''))
        enc=evenements([{**l,'nature':'service'} for l in doc['lignes']],doc['ttc'],doc['paiements'],doc['date'],'')
        for e in even:
            if debut<=e['date']<=fin:
                gr=ligne(e['taux']);gr['base_exigible']+=e['ht']
                if regime=='reel':gr['tva_exigible']+=e['tva'];exigible+=e['tva']
        for e in enc:
            if debut<=e['date']<=fin and regime=='reel':ligne(e['taux'])['tva_percue']+=e['tva'];percue+=e['tva']
    for achat in achats:
        if achat.get('incomplet'):alertes.append(achat['incomplet'])
        for e in evenements(achat['lignes'],achat['ttc'],achat['paiements'],achat['date'],achat.get('livraison','')):
            if not debut<=e['date']<=fin:continue
            gr=ligne(e['taux']);gr['base_achats']+=e['ht'];gr['tva_achats']+=e['tva']
            deduction=e['deduction_delta'] if regime=='reel' and achat.get('justificatif') else 0
            deductible+=deduction;gr['tva_deductible']+=deduction
            if e.get('categorie')=='immobilisation':deduction_immobilisation+=deduction
    if regime not in ('franchise','reel'):alertes.append('Régime TVA de la période à confirmer.')
    ajustements=sum(x['montant'] for x in corrections if debut<=x['date']<=fin)
    net=exigible-deductible-credit+ajustements if regime=='reel' else 0
    return {'debut':debut,'fin':fin,'regime':regime,'tva_percue':percue,'tva_exigible':exigible,'tva_deductible':deductible,'deduction_immobilisation':deduction_immobilisation,'credit_precedent':credit if regime=='reel' else 0,'regularisations':ajustements if regime=='reel' else 0,'a_reverser':max(0,net),'credit':max(0,-net),'taux':sorted(groupes.values(),key=lambda x:x['taux']),'alertes':list(dict.fromkeys(alertes))}
