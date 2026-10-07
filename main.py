# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
import uvicorn
from pathlib import Path
from fastapi.responses import FileResponse, RedirectResponse
from database import initialiser_base, lister_clients, ajouter_client, obtenir_client, modifier_client, lister_articles, ajouter_article, obtenir_article, modifier_article, supprimer_article, obtenir_entreprise, modifier_entreprise, enregistrer_reprise_mensuelle, lister_reprise_mensuelle, obtenir_fiscalite_annuelle, verifier_date_fiscale, enregistrer_fin_reprise, verifier_reprise, enregistrer_debut_activite, enregistrer_ca_n1, enregistrer_option_reel, proposer_regime_tva, enregistrer_depassement, obtenir_date_tva_depassement, ajouter_operation, lister_operations, obtenir_operation, supprimer_operation, modifier_operation, obtenir_resume_annuel, obtenir_resume_mensuel, creer_devis, lister_devis, obtenir_devis, lister_lignes_devis, ajouter_ligne_devis, obtenir_ligne_devis, modifier_ligne_devis, supprimer_ligne_devis, determiner_tva_devis, modifier_validite_devis
from datetime import date, timedelta
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title='PatenteEasy')
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))
MOIS = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
import web_final
import sys

class InterfaceWeb:
    """Contrôleur des formulaires et listes historiques."""

    def __init__(self, app, templates):
        self.app = app
        self.templates = templates
        self.app.get('/')(self.accueil)
        self.app.get('/api/clients')(self.clients_api)
        self.app.get('/clients')(self.page_clients)
        self.app.post('/clients')(self.creer_client)
        self.app.get('/clients/{client_id}/modifier')(self.page_modifier_client)
        self.app.post('/clients/{client_id}/modifier')(self.enregistrer_modification)
        self.app.get('/articles')(self.page_articles)
        self.app.post('/articles')(self.creer_article)
        self.app.get('/articles/{article_id}/modifier')(self.formulaire_modifier_article)
        self.app.post('/articles/{article_id}/modifier')(self.enregistrer_modification_article)
        self.app.get('/articles/{article_id}/supprimer')(self.confirmer_suppression_article)
        self.app.post('/articles/{article_id}/supprimer')(self.enregistrer_suppression_article)
        self.app.get('/entreprise')(self.page_entreprise)
        self.app.post('/entreprise')(self.enregistrer_entreprise)
        self.app.get('/reprise')(self.page_reprise)
        self.app.post('/reprise')(self.sauvegarder_reprise)
        self.app.post('/reprise/periode')(self.sauvegarder_periode_reprise)
        self.app.post('/entreprise/debut-activite')(self.sauvegarder_debut_activite)
        self.app.post('/reprise/ca-n1')(self.sauvegarder_ca_n1)
        self.app.post('/reprise/option-reel')(self.sauvegarder_option_reel)
        self.app.post('/reprise/depassement')(self.sauvegarder_depassement)
        self.app.get('/journal')(self.page_journal)
        self.app.post('/journal')(self.enregistrer_operation)
        self.app.get('/journal/{operation_id}/supprimer')(self.confirmer_suppression_operation)
        self.app.post('/journal/{operation_id}/supprimer')(self.valider_suppression_operation)
        self.app.get('/journal/{operation_id}/modifier')(self.formulaire_modifier_operation)
        self.app.post('/journal/{operation_id}/modifier')(self.enregistrer_modification_operation)
        self.app.get('/devis')(self.page_devis)
        self.app.post('/devis')(self.enregistrer_brouillon_devis)
        self.app.get('/devis/{devis_id}')(self.page_detail_devis)
        self.app.post('/devis/{devis_id}/catalogue')(self.ajouter_catalogue_au_devis)
        self.app.post('/devis/{devis_id}/ligne-libre')(self.ajouter_ligne_libre_au_devis)
        self.app.get('/devis/{devis_id}/lignes/{ligne_id}/modifier')(self.formulaire_modifier_ligne_devis)
        self.app.post('/devis/{devis_id}/lignes/{ligne_id}/modifier')(self.sauvegarder_ligne_devis)
        self.app.get('/devis/{devis_id}/lignes/{ligne_id}/supprimer')(self.confirmer_suppression_ligne_devis)
        self.app.post('/devis/{devis_id}/lignes/{ligne_id}/supprimer')(self.valider_suppression_ligne_devis)
        self.app.post('/devis/{devis_id}/validite')(self.sauvegarder_validite_devis)

    def afficher_centiemes(self, valeur):
        valeur = int(valeur)
        signe = '-' if valeur < 0 else ''
        unites, fraction = divmod(abs(valeur), 100)
        texte = f'{unites:,}'.replace(',', ' ')
        if fraction:
            texte += f',{fraction:02d}'
        return signe + texte

    def accueil(self):
        return FileResponse(BASE_DIR / 'templates' / 'index.html', media_type='text/html')

    def clients_api(self):
        return lister_clients()

    def page_clients(self, request: Request):
        return templates.TemplateResponse(request=request, name='clients.html', context={'clients': lister_clients(), 'saisie': {}})

    def creer_client(self, request: Request, nom: str=Form(''), telephone: str=Form(''), email: str=Form(''), adresse: str=Form('')):
        saisie = {'nom': nom, 'telephone': telephone, 'email': email, 'adresse': adresse}
        try:
            ajouter_client(nom, telephone, email, adresse)
        except ValueError as erreur:
            return templates.TemplateResponse(request=request, name='clients.html', context={'clients': lister_clients(), 'saisie': saisie, 'erreur': str(erreur)}, status_code=400)
        return RedirectResponse(url='/clients', status_code=303)

    def page_modifier_client(self, request: Request, client_id: int):
        client = obtenir_client(client_id)
        if client is None:
            raise HTTPException(status_code=404, detail='Client introuvable.')
        return templates.TemplateResponse(request=request, name='client_modifier.html', context={'client': client})

    def enregistrer_modification(self, request: Request, client_id: int, nom: str=Form(''), telephone: str=Form(''), email: str=Form(''), adresse: str=Form('')):
        if obtenir_client(client_id) is None:
            raise HTTPException(status_code=404, detail='Client introuvable.')
        try:
            modifier_client(client_id, nom, telephone, email, adresse)
        except ValueError as erreur:
            return templates.TemplateResponse(request=request, name='client_modifier.html', context={'client': {'id': client_id, 'nom': nom, 'telephone': telephone, 'email': email, 'adresse': adresse}, 'erreur': str(erreur)}, status_code=400)
        return RedirectResponse(url='/clients', status_code=303)

    def page_articles(self, request: Request):
        return templates.TemplateResponse(request=request, name='articles.html', context={'articles': lister_articles(), 'saisie': {}})

    def creer_article(self, request: Request, reference: str=Form(''), designation: str=Form(''), type_article: str=Form('produit'), unite: str=Form('pièce'), prix_achat: str=Form('0'), prix_vente: str=Form('0'), taxe: str=Form('0')):
        saisie = {'reference': reference, 'designation': designation, 'type_article': type_article, 'unite': unite, 'prix_achat': prix_achat, 'prix_vente': prix_vente, 'taxe': taxe}
        try:
            ajouter_article(reference=reference, designation=designation, type_article=type_article, unite=unite, prix_achat=prix_achat, prix_vente=prix_vente, taxe=taxe)
        except ValueError as erreur:
            return templates.TemplateResponse(request=request, name='articles.html', context={'articles': lister_articles(), 'saisie': saisie, 'erreur': str(erreur)}, status_code=400)
        return RedirectResponse(url='/articles', status_code=303)

    def formulaire_modifier_article(self, request: Request, article_id: int):
        article = obtenir_article(article_id)
        if article is None:
            raise HTTPException(status_code=404, detail='Article introuvable.')
        saisie = {'reference': article['reference'], 'designation': article['designation'], 'type_article': article['type_article'], 'unite': article['unite'], 'prix_achat': self.afficher_centiemes(article['prix_achat_centiemes']).replace(' ', ''), 'prix_vente': self.afficher_centiemes(article['prix_vente_centiemes']).replace(' ', ''), 'taxe': self.afficher_centiemes(article['taxe_centiemes']).replace(' ', '')}
        return templates.TemplateResponse(request=request, name='article_modifier.html', context={'article_id': article_id, 'saisie': saisie})

    def enregistrer_modification_article(self, request: Request, article_id: int, reference: str=Form(''), designation: str=Form(''), type_article: str=Form('produit'), unite: str=Form(''), prix_achat: str=Form(''), prix_vente: str=Form(''), taxe: str=Form('')):
        if obtenir_article(article_id) is None:
            raise HTTPException(status_code=404, detail='Article introuvable.')
        saisie = {'reference': reference, 'designation': designation, 'type_article': type_article, 'unite': unite, 'prix_achat': prix_achat, 'prix_vente': prix_vente, 'taxe': taxe}
        try:
            modifier_article(article_id=article_id, reference=reference, designation=designation, type_article=type_article, unite=unite, prix_achat=prix_achat, prix_vente=prix_vente, taxe=taxe)
        except ValueError as erreur:
            return templates.TemplateResponse(request=request, name='article_modifier.html', context={'article_id': article_id, 'saisie': saisie, 'erreur': str(erreur)}, status_code=400)
        return RedirectResponse(url='/articles', status_code=303)

    def confirmer_suppression_article(self, request: Request, article_id: int):
        article = obtenir_article(article_id)
        if article is None:
            raise HTTPException(status_code=404, detail='Article introuvable.')
        return templates.TemplateResponse(request=request, name='article_supprimer.html', context={'article': article})

    def enregistrer_suppression_article(self, article_id: int):
        try:
            supprimer_article(article_id)
        except ValueError as erreur:
            raise HTTPException(status_code=404, detail=str(erreur)) from None
        return RedirectResponse(url='/articles', status_code=303)

    def page_entreprise(self, request: Request):
        entreprise = obtenir_entreprise()
        if entreprise is None:
            raise HTTPException(status_code=404, detail='La fiche entreprise est introuvable.')
        return templates.TemplateResponse(request=request, name='entreprise.html', context={'saisie': entreprise})

    def enregistrer_entreprise(self, request: Request, nom: str=Form(''), responsable: str=Form(''), telephone: str=Form(''), email: str=Form(''), adresse: str=Form(''), numero_tahiti: str=Form(''), numero_rcs: str=Form('')):
        saisie = {'nom': nom, 'responsable': responsable, 'telephone': telephone, 'email': email, 'adresse': adresse, 'numero_tahiti': numero_tahiti, 'numero_rcs': numero_rcs}
        try:
            modifier_entreprise(nom=nom, responsable=responsable, telephone=telephone, email=email, adresse=adresse, numero_tahiti=numero_tahiti, numero_rcs=numero_rcs)
        except ValueError as erreur:
            return templates.TemplateResponse(request=request, name='entreprise.html', context={'saisie': saisie, 'erreur': str(erreur)}, status_code=400)
        return RedirectResponse(url='/entreprise', status_code=303)

    def afficher_page_reprise(self, request, annee, saisie=None, erreur=None):
        lignes = lister_reprise_mensuelle(annee)
        total_recettes = sum((ligne['recettes_centiemes'] for ligne in lignes if ligne['recettes_centiemes'] is not None))
        total_depenses = sum((ligne['depenses_centiemes'] for ligne in lignes if ligne['depenses_centiemes'] is not None))
        fiscalite = obtenir_fiscalite_annuelle(annee) or {}
        montant_n1 = fiscalite.get('ca_n1_centiemes')
        ca_n1 = self.afficher_centiemes(montant_n1).replace(' ', '') if montant_n1 is not None else ''
        if saisie is not None and 'ca_n1' in saisie:
            ca_n1 = saisie['ca_n1']
        option_reel = fiscalite.get('date_effet_option_reel', '')
        if saisie is not None and 'option_reel' in saisie:
            option_reel = saisie['option_reel']
        par_mois = {ligne['mois']: ligne for ligne in lignes}
        depassement = fiscalite.get('date_depassement', '')
        if saisie is not None and 'depassement' in saisie:
            depassement = saisie['depassement']
        mois_affiches = [{'numero': numero, 'nom': nom, 'donnees': par_mois.get(numero), 'date_fin_reprise': fiscalite.get('date_fin_reprise', ''), 'controle_reprise': verifier_reprise(annee)} for numero, nom in enumerate(MOIS, start=1)]
        return templates.TemplateResponse(request=request, name='reprise.html', context={'annee': annee, 'ca_n1': ca_n1, 'option_reel': option_reel, 'depassement': depassement, 'date_debut_tva': obtenir_date_tva_depassement(annee), 'mois_affiches': mois_affiches, 'saisie': saisie or {}, 'erreur': erreur, 'date_fin_reprise': fiscalite.get('date_fin_reprise', ''), 'controle_reprise': verifier_reprise(annee), 'proposition_tva': proposer_regime_tva(annee), 'total_recettes': total_recettes, 'total_depenses': total_depenses}, status_code=400 if erreur else 200)

    def page_reprise(self, request: Request, annee: int=date.today().year):
        if not 1900 <= annee <= date.today().year:
            raise HTTPException(status_code=400, detail='Année invalide.')
        return self.afficher_page_reprise(request, annee)

    def sauvegarder_reprise(self, request: Request, annee: int=Form(...), mois: int=Form(...), recettes: str=Form(''), depenses: str=Form(''), verifie: bool=Form(False)):
        if not 1900 <= annee <= date.today().year:
            raise HTTPException(status_code=400, detail='Année invalide.')
        saisie = {'mois': mois, 'recettes': recettes, 'depenses': depenses, 'verifie': verifie}
        try:
            if date(annee, mois, 1) > date.today():
                raise ValueError('Vous ne pouvez pas reprendre un mois futur.')
            enregistrer_reprise_mensuelle(annee=annee, mois=mois, recettes=recettes, depenses=depenses, verifie=verifie)
        except ValueError as erreur:
            return self.afficher_page_reprise(request, annee, saisie, str(erreur))
        return RedirectResponse(url=f'/reprise?annee={annee}', status_code=303)

    def sauvegarder_periode_reprise(self, request: Request, annee: int=Form(...), date_fin_reprise: str=Form('')):
        if not 1900 <= annee <= date.today().year:
            raise HTTPException(status_code=400, detail='Année invalide.')
        try:
            enregistrer_fin_reprise(annee, date_fin_reprise)
        except ValueError as erreur:
            return self.afficher_page_reprise(request, annee, erreur=str(erreur))
        return RedirectResponse(url=f'/reprise?annee={annee}', status_code=303)

    def sauvegarder_debut_activite(self, request: Request, date_debut_activite: str=Form('')):
        try:
            enregistrer_debut_activite(date_debut_activite)
        except ValueError as erreur:
            saisie = obtenir_entreprise() or {}
            saisie['date_debut_activite'] = date_debut_activite
            return templates.TemplateResponse(request=request, name='entreprise.html', context={'saisie': saisie, 'erreur': str(erreur)}, status_code=400)
        return RedirectResponse(url='/entreprise', status_code=303)

    def sauvegarder_ca_n1(self, request: Request, annee: int=Form(...), ca_n1: str=Form('')):
        if not 1900 <= annee <= date.today().year:
            raise HTTPException(status_code=400, detail='Année invalide.')
        try:
            enregistrer_ca_n1(annee, ca_n1)
        except ValueError as erreur:
            return self.afficher_page_reprise(request, annee, saisie={'ca_n1': ca_n1}, erreur=str(erreur))
        return RedirectResponse(url=f'/reprise?annee={annee}', status_code=303)

    def sauvegarder_option_reel(self, request: Request, annee: int=Form(...), option_reel: str=Form('')):
        if not 1900 <= annee <= date.today().year:
            raise HTTPException(status_code=400, detail='Année invalide.')
        try:
            enregistrer_option_reel(annee, option_reel)
        except ValueError as erreur:
            return self.afficher_page_reprise(request, annee, saisie={'option_reel': option_reel}, erreur=str(erreur))
        return RedirectResponse(url=f'/reprise?annee={annee}', status_code=303)

    def sauvegarder_depassement(self, request: Request, annee: int=Form(...), depassement: str=Form('')):
        if not 1900 <= annee <= date.today().year:
            raise HTTPException(status_code=400, detail='Année invalide.')
        try:
            enregistrer_depassement(annee, depassement)
        except ValueError as erreur:
            return self.afficher_page_reprise(request, annee, saisie={'depassement': depassement}, erreur=str(erreur))
        return RedirectResponse(url=f'/reprise?annee={annee}', status_code=303)

    def afficher_journal(self, request, annee, saisie=None, erreur=None):
        mensuel = obtenir_resume_mensuel(annee)
        precedent = obtenir_resume_mensuel(annee - 1)
        reprises_precedentes = {ligne['mois']: ligne for ligne in lister_reprise_mensuelle(annee - 1)}
        fiscalite_precedente = obtenir_fiscalite_annuelle(annee - 1) or {}
        fin_texte = fiscalite_precedente.get('date_fin_reprise', '')
        fin_precedente = date.fromisoformat(fin_texte) if fin_texte else None
        entreprise = obtenir_entreprise() or {}
        debut_texte = entreprise.get('date_debut_activite', '')
        debut = date.fromisoformat(debut_texte) if debut_texte else None
        for ligne, ancienne in zip(mensuel, precedent):
            mois = ligne['mois']
            reprise = reprises_precedentes.get(mois)
            debut_mois = date(annee - 1, mois, 1)
            if mois == 12:
                mois_suivant = date(annee, 1, 1)
            else:
                mois_suivant = date(annee - 1, mois + 1, 1)
            fin_mois = date.fromordinal(mois_suivant.toordinal() - 1)
            disponible = bool(debut and debut <= debut_mois and fin_precedente and (fin_precedente >= fin_mois) and reprise and reprise['verifie'] and (reprise['recettes_centiemes'] is not None) and (reprise['depenses_centiemes'] is not None))
            ligne['nom_mois'] = MOIS[mois - 1]
            ligne['precedent_disponible'] = disponible
            ligne['recettes_precedentes'] = ancienne['recettes']
            ligne['depenses_precedentes'] = ancienne['depenses']
            ligne['ecart_recettes'] = ligne['recettes'] - ancienne['recettes']
        return templates.TemplateResponse(request=request, name='journal.html', context={'annee': annee, 'operations': lister_operations(annee), 'resume': obtenir_resume_annuel(annee), 'mensuel': mensuel, 'saisie': saisie or {}, 'erreur': erreur}, status_code=400 if erreur else 200)

    def page_journal(self, request: Request, annee: int | None=None):
        if annee is None:
            annee = date.today().year
        if not 1900 <= annee <= date.today().year:
            raise HTTPException(status_code=400, detail='Année invalide.')
        return self.afficher_journal(request, annee)

    def enregistrer_operation(self, request: Request, annee: int=Form(...), date_operation: str=Form(''), libelle: str=Form(''), type_operation: str=Form('recette'), montant: str=Form('')):
        if not 1900 <= annee <= date.today().year:
            raise HTTPException(status_code=400, detail='Année invalide.')
        saisie = {'date_operation': date_operation, 'libelle': libelle, 'type_operation': type_operation, 'montant': montant}
        try:
            date_texte = verifier_date_fiscale(date_operation, 'Date de l’opération')
            if not date_texte:
                raise ValueError('La date est obligatoire.')
            if date.fromisoformat(date_texte).year != annee:
                raise ValueError('La date doit appartenir à l’année affichée.')
            ajouter_operation(date_operation=date_texte, libelle=libelle, type_operation=type_operation, montant=montant)
        except ValueError as erreur:
            return self.afficher_journal(request, annee, saisie, str(erreur))
        return RedirectResponse(url=f'/journal?annee={annee}', status_code=303)

    def confirmer_suppression_operation(self, request: Request, operation_id: int):
        operation = obtenir_operation(operation_id)
        if operation is None:
            raise HTTPException(status_code=404, detail='Opération introuvable.')
        return templates.TemplateResponse(request=request, name='operation_supprimer.html', context={'operation': operation})

    def valider_suppression_operation(self, operation_id: int):
        operation = obtenir_operation(operation_id)
        if operation is None:
            raise HTTPException(status_code=404, detail='Opération introuvable.')
        annee = date.fromisoformat(operation['date_operation']).year
        try:
            supprimer_operation(operation_id)
        except ValueError as erreur:
            raise HTTPException(status_code=400, detail=str(erreur)) from None
        return RedirectResponse(url=f'/journal?annee={annee}', status_code=303)

    def formulaire_modifier_operation(self, request: Request, operation_id: int):
        operation = obtenir_operation(operation_id)
        if operation is None:
            raise HTTPException(status_code=404, detail='Opération introuvable.')
        saisie = {'date_operation': operation['date_operation'], 'libelle': operation['libelle'], 'type_operation': operation['type_operation'], 'montant': self.afficher_centiemes(operation['montant_centiemes']).replace(' ', '')}
        return templates.TemplateResponse(request=request, name='operation_modifier.html', context={'operation_id': operation_id, 'annee_retour': operation['date_operation'][:4], 'saisie': saisie})

    def enregistrer_modification_operation(self, request: Request, operation_id: int, date_operation: str=Form(''), libelle: str=Form(''), type_operation: str=Form('recette'), montant: str=Form('')):
        operation = obtenir_operation(operation_id)
        if operation is None:
            raise HTTPException(status_code=404, detail='Opération introuvable.')
        saisie = {'date_operation': date_operation, 'libelle': libelle, 'type_operation': type_operation, 'montant': montant}
        try:
            modifier_operation(operation_id=operation_id, date_operation=date_operation, libelle=libelle, type_operation=type_operation, montant=montant)
        except ValueError as erreur:
            return templates.TemplateResponse(request=request, name='operation_modifier.html', context={'operation_id': operation_id, 'annee_retour': operation['date_operation'][:4], 'saisie': saisie, 'erreur': str(erreur)}, status_code=400)
        annee = date.fromisoformat(date_operation.strip()).year
        return RedirectResponse(url=f'/journal?annee={annee}', status_code=303)

    def afficher_page_devis(self, request, saisie=None, erreur=None):
        return templates.TemplateResponse(request=request, name='devis.html', context={'clients': lister_clients(), 'devis': lister_devis(), 'saisie': saisie or {}, 'date_du_jour': date.today().isoformat(), 'erreur': erreur}, status_code=400 if erreur else 200)

    def page_devis(self, request: Request):
        return self.afficher_page_devis(request)

    def enregistrer_brouillon_devis(self, request: Request, client_id: str=Form(''), date_devis: str=Form(''), objet: str=Form('')):
        saisie = {'client_id': client_id, 'date_devis': date_devis, 'objet': objet}
        try:
            try:
                identifiant_client = int(client_id)
            except ValueError:
                raise ValueError('Choisissez un client.') from None
            creer_devis(client_id=identifiant_client, date_devis=date_devis, objet=objet)
        except ValueError as erreur:
            return self.afficher_page_devis(request, saisie, str(erreur))
        return RedirectResponse(url='/devis', status_code=303)

    def afficher_detail_devis(self, request, devis_id, saisie=None, erreur=None):
        devis = obtenir_devis(devis_id)
        if devis is None:
            raise HTTPException(status_code=404, detail='Devis introuvable.')
        date_fin_validite = (date.fromisoformat(devis['date_devis']) + timedelta(days=devis['validite_jours'])).strftime('%d/%m/%Y')
        validite_saisie = str(devis['validite_jours'])
        if saisie is not None and 'validite_jours' in saisie:
            validite_saisie = saisie['validite_jours']
        fiscalite = determiner_tva_devis(devis['date_devis'])
        lignes = lister_lignes_devis(devis_id)
        for ligne in lignes:
            produit = ligne['quantite_centiemes'] * ligne['prix_unitaire_centiemes']
            montant_ht = (produit + 50) // 100
            ligne['montant_ht_centiemes'] = montant_ht
            if fiscalite['applicable'] is True:
                ligne['montant_tva_centiemes'] = (montant_ht * ligne['taxe_centiemes'] + 5000) // 10000
            else:
                ligne['montant_tva_centiemes'] = None
        total_ht = sum((ligne['montant_ht_centiemes'] for ligne in lignes))
        total_tva = None
        total_ttc = None
        if fiscalite['applicable'] is True:
            total_tva = sum((ligne['montant_tva_centiemes'] for ligne in lignes))
            total_ttc = total_ht + total_tva
        return templates.TemplateResponse(request=request, name='devis_detail.html', context={'devis': devis, 'lignes': lignes, 'articles': lister_articles(), 'saisie': saisie or {}, 'erreur': erreur, 'total_ht': total_ht, 'total_tva': total_tva, 'total_ttc': total_ttc, 'fiscalite': fiscalite, 'date_fin_validite': date_fin_validite, 'validite_saisie': validite_saisie}, status_code=400 if erreur else 200)

    def page_detail_devis(self, request: Request, devis_id: int):
        return self.afficher_detail_devis(request, devis_id)

    def ajouter_catalogue_au_devis(self, request: Request, devis_id: int, article_id: str=Form(''), quantite: str=Form('1')):
        if obtenir_devis(devis_id) is None:
            raise HTTPException(status_code=404, detail='Devis introuvable.')
        saisie = {'article_id': article_id, 'quantite_catalogue': quantite}
        try:
            try:
                identifiant = int(article_id)
            except ValueError:
                raise ValueError('Choisissez un article.') from None
            article = obtenir_article(identifiant)
            if article is None:
                raise ValueError('Article introuvable.')
            ajouter_ligne_devis(devis_id=devis_id, reference=article['reference'], designation=article['designation'], unite=article['unite'], quantite=quantite, prix_unitaire=self.afficher_centiemes(article['prix_vente_centiemes']).replace(' ', ''), taxe=self.afficher_centiemes(article['taxe_centiemes']).replace(' ', ''))
        except ValueError as erreur:
            return self.afficher_detail_devis(request, devis_id, saisie, str(erreur))
        return RedirectResponse(url=f'/devis/{devis_id}', status_code=303)

    def ajouter_ligne_libre_au_devis(self, request: Request, devis_id: int, designation: str=Form(''), unite: str=Form('pièce'), quantite: str=Form('1'), prix_unitaire: str=Form(''), taxe: str=Form('0'), reference: str=Form(''), type_article: str=Form('produit'), enregistrer_catalogue: bool=Form(False)):
        if obtenir_devis(devis_id) is None:
            raise HTTPException(status_code=404, detail='Devis introuvable.')
        saisie = {'designation': designation, 'unite': unite, 'quantite_libre': quantite, 'prix_unitaire': prix_unitaire, 'taxe': taxe, 'reference': reference, 'type_article': type_article, 'enregistrer_catalogue': enregistrer_catalogue}
        try:
            ajouter_ligne_devis(devis_id=devis_id, designation=designation, unite=unite, quantite=quantite, prix_unitaire=prix_unitaire, taxe=taxe, reference=reference, type_article=type_article, enregistrer_catalogue=enregistrer_catalogue)
        except ValueError as erreur:
            return self.afficher_detail_devis(request, devis_id, saisie, str(erreur))
        return RedirectResponse(url=f'/devis/{devis_id}', status_code=303)

    def formulaire_modifier_ligne_devis(self, request: Request, devis_id: int, ligne_id: int):
        devis = obtenir_devis(devis_id)
        ligne = obtenir_ligne_devis(devis_id, ligne_id)
        if devis is None or ligne is None:
            raise HTTPException(status_code=404, detail='Devis ou ligne introuvable.')
        if devis['statut'] != 'brouillon':
            raise HTTPException(status_code=400, detail='Seul un brouillon peut être modifié.')
        saisie = {'reference': ligne['reference'], 'designation': ligne['designation'], 'unite': ligne['unite'], 'quantite': self.afficher_centiemes(ligne['quantite_centiemes']).replace(' ', ''), 'prix_unitaire': self.afficher_centiemes(ligne['prix_unitaire_centiemes']).replace(' ', ''), 'taxe': self.afficher_centiemes(ligne['taxe_centiemes']).replace(' ', '')}
        return templates.TemplateResponse(request=request, name='devis_ligne_modifier.html', context={'devis_id': devis_id, 'ligne_id': ligne_id, 'saisie': saisie})

    def sauvegarder_ligne_devis(self, request: Request, devis_id: int, ligne_id: int, reference: str=Form(''), designation: str=Form(''), unite: str=Form(''), quantite: str=Form(''), prix_unitaire: str=Form(''), taxe: str=Form('')):
        if obtenir_ligne_devis(devis_id, ligne_id) is None:
            raise HTTPException(status_code=404, detail='Ligne introuvable.')
        saisie = {'reference': reference, 'designation': designation, 'unite': unite, 'quantite': quantite, 'prix_unitaire': prix_unitaire, 'taxe': taxe}
        try:
            modifier_ligne_devis(devis_id=devis_id, ligne_id=ligne_id, reference=reference, designation=designation, unite=unite, quantite=quantite, prix_unitaire=prix_unitaire, taxe=taxe)
        except ValueError as erreur:
            return templates.TemplateResponse(request=request, name='devis_ligne_modifier.html', context={'devis_id': devis_id, 'ligne_id': ligne_id, 'saisie': saisie, 'erreur': str(erreur)}, status_code=400)
        return RedirectResponse(url=f'/devis/{devis_id}', status_code=303)

    def confirmer_suppression_ligne_devis(self, request: Request, devis_id: int, ligne_id: int):
        devis = obtenir_devis(devis_id)
        ligne = obtenir_ligne_devis(devis_id, ligne_id)
        if devis is None or ligne is None:
            raise HTTPException(status_code=404, detail='Devis ou ligne introuvable.')
        if devis['statut'] != 'brouillon':
            raise HTTPException(status_code=400, detail='Seul un brouillon peut être modifié.')
        return templates.TemplateResponse(request=request, name='devis_ligne_supprimer.html', context={'devis_id': devis_id, 'ligne': ligne})

    def valider_suppression_ligne_devis(self, request: Request, devis_id: int, ligne_id: int):
        if obtenir_ligne_devis(devis_id, ligne_id) is None:
            raise HTTPException(status_code=404, detail='Ligne introuvable.')
        try:
            supprimer_ligne_devis(devis_id, ligne_id)
        except ValueError as erreur:
            return self.afficher_detail_devis(request, devis_id, erreur=str(erreur))
        return RedirectResponse(url=f'/devis/{devis_id}', status_code=303)

    def sauvegarder_validite_devis(self, request: Request, devis_id: int, validite_jours: str=Form('')):
        if obtenir_devis(devis_id) is None:
            raise HTTPException(status_code=404, detail='Devis introuvable.')
        try:
            modifier_validite_devis(devis_id, validite_jours)
        except ValueError as erreur:
            return self.afficher_detail_devis(request, devis_id, saisie={'validite_jours': validite_jours}, erreur=str(erreur))
        return RedirectResponse(url=f'/devis/{devis_id}', status_code=303)

interface = InterfaceWeb(app, templates)
templates.env.filters['centiemes'] = interface.afficher_centiemes
def __getattr__(nom):
    return getattr(interface, nom)

web_final.installer(app, templates, sys.modules[__name__])

if __name__ == '__main__':
    web_final.initialiser()
    uvicorn.run(app, host='127.0.0.1', port=8000)
