# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
import csv
import io
import json
import secrets
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs
from fastapi import Request, Form
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware
import database as db
import gestion as g
from pdf_documents import generer, monnaie

ROOT=Path(__file__).resolve().parent
CSRF=secrets.token_urlsafe(32)


def initialiser():
    g.migrer()


def installer(app, templates, main):
    from urllib.parse import urlsplit
    try:
        from editeur import editeur
        configuration = editeur.lire()
        paypal = str(configuration.get('paypal_url','')).strip()
        lien = urlsplit(paypal)
        if lien.scheme != 'https' or lien.hostname not in ('paypal.me','www.paypal.me','paypal.com','www.paypal.com') or lien.username or lien.password or lien.port not in (None,443):
            paypal = ''
    except (OSError, ValueError):
        paypal = ''
    templates.env.globals.update(csrf_token=CSRF, app_name='Patenteasy', developer='ska_987', paypal_url=paypal, telephone_actif=False)
    from editeur import editeur
    templates.env.globals['hebergement_url'] = editeur.demande_hebergement()
    templates.env.filters['centiemes']=monnaie
    app.title='Patenteasy'
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])
    # Remplacer les pages concernées, conserver les CRUD existants.
    remplaces={'/','/devis/{devis_id}','/devis','/entreprise/validite-devis'}
    app.router.routes[:]=[r for r in app.router.routes if getattr(r,'path',None) not in remplaces]
    main.creer_devis=g.creer_devis
    main.determiner_tva_devis=lambda jour: {'applicable':{'reel':True,'franchise':False}.get(g.regime_a_la_date(jour)), 'message':'Régime à vérifier'}
    # Les paiements liés aux factures ne doivent pas être modifiés via le journal.
    ancien_modifier=db.modifier_operation; ancien_supprimer=db.supprimer_operation
    def protege(identifiant):
        if g.liste('SELECT id FROM paiements WHERE operation_id=?',(identifiant,)) or g.liste('SELECT id FROM remboursements WHERE operation_id=?',(identifiant,)):
            raise ValueError('Cette opération est un paiement de facture. Elle ne peut pas être modifiée ou supprimée dans le journal.')
    def modifier(operation_id,*args,**kwargs):
        protege(operation_id); return ancien_modifier(operation_id,*args,**kwargs)
    def supprimer(operation_id):
        protege(operation_id); return ancien_supprimer(operation_id)
    main.modifier_operation=modifier; main.supprimer_operation=supprimer

    def vue(request, name, **context):
        context.update(entreprise_actuelle=db.obtenir_entreprise() or {}, aujourd_hui=g.aujourd_hui().isoformat())
        return templates.TemplateResponse(request=request,name=name,context=context)
    def retour(url): return RedirectResponse(url,303)

    @app.middleware('http')
    async def protection(request, call_next):
        if request.method in ('POST','PUT','DELETE','PATCH'):
            body=await request.body()
            token=parse_qs(body.decode('utf-8',errors='replace')).get('csrf_token',[''])[0]
            if not secrets.compare_digest(token,CSRF):
                return Response('Formulaire expiré. Actualisez la page et réessayez.',status_code=403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Cache-Control']='no-store'
        return response

    @app.exception_handler(ValueError)
    async def valeur_invalide(request, exc):
        r=vue(request,'erreur.html',message=str(exc)); r.status_code=400; return r
    @app.exception_handler(sqlite3.IntegrityError)
    async def integrite(request, exc):
        r=vue(request,'erreur.html',message='Cette action est incompatible avec les données existantes. Une référence existe déjà ou cet élément est utilisé.'); r.status_code=400; return r

    @app.get('/static/style.css')
    def style(): return Response((ROOT/'static/style.css').read_text(),media_type='text/css')

    @app.get('/')
    def tableau(request:Request):
        entreprise = db.obtenir_entreprise()
        if not entreprise['nom'].strip():
            return retour('/entreprise?premiere=1')
        docs=g.documents(); impayes=[]; restant=0
        for d in docs:
            if d['type']!='facture': continue
            d['reste']=max(0,d['total_centiemes']-d['paye']-d['credite'])
            d['client']=json.loads(d['instantane'])['client']['nom']
            d['retard']=d['echeance']<g.aujourd_hui().isoformat()
            if d['reste']: impayes.append(d); restant+=d['reste']
        e=db.obtenir_entreprise(); resume=db.obtenir_resume_annuel(g.aujourd_hui().year)
        tresorerie=None
        if e['date_solde_depart']:
            ops=g.liste('SELECT * FROM operations WHERE date_operation>=? AND date_operation<=?',(e['date_solde_depart'],g.aujourd_hui().isoformat()))
            tresorerie=e['solde_depart_centiemes']+sum(o['montant_centiemes']*(1 if o['type_operation']=='recette' else -1) for o in ops)
        rappels=g.liste('SELECT * FROM rappels WHERE fait=0 ORDER BY echeance')
        return vue(request,'dashboard.html',resume=resume,impayes=impayes,restant=restant,tresorerie=tresorerie,rappels=rappels,
                   devis=db.lister_devis(),configuration_ok=bool(e['nom'] and e['date_debut_activite']))

    @app.get('/devis')
    def devis_liste(request:Request): return main.afficher_page_devis(request)

    @app.post('/devis')
    def nouveau_devis(request:Request,client_id:str=Form(''),date_devis:str=Form(''),objet:str=Form('')):
        try: identifiant=int(client_id)
        except ValueError: raise ValueError('Choisissez un client.') from None
        return retour('/devis/'+str(g.creer_devis(identifiant,date_devis,objet)))

    @app.get('/devis/{devis_id}')
    def detail(request:Request,devis_id:int):
        s=g.calculer(devis_id); d=db.obtenir_devis(devis_id)
        return vue(request,'document_devis.html',s=s,devis=d,articles=db.lister_articles(),clients=db.lister_clients(),saisie={},erreur=None)

    # Les validations des anciennes routes réaffichent désormais la nouvelle page.
    def afficher_detail(request,devis_id,saisie=None,erreur=None):
        s=dict(g.calculer(devis_id));s.update(g.conditions_documents())
        r=vue(request,'document_devis.html',s=s,devis=db.obtenir_devis(devis_id),articles=db.lister_articles(),clients=db.lister_clients(),saisie=saisie or {},erreur=erreur)
        if erreur: r.status_code=400
        return r
    main.afficher_detail_devis=afficher_detail
    main.interface.afficher_detail_devis=afficher_detail

    @app.post('/devis/{devis_id}/entete')
    def entete(devis_id:int,client_id:int=Form(...),date_devis:str=Form(...),objet:str=Form(''),validite:str=Form('30')):
        g.modifier_devis(devis_id,client_id,date_devis,objet,validite); return retour(f'/devis/{devis_id}')

    @app.post('/devis/{devis_id}/emettre')
    def emettre(devis_id:int): g.emettre_devis(devis_id); return retour(f'/devis/{devis_id}')

    @app.post('/devis/{devis_id}/decision')
    def decision(devis_id:int,statut:str=Form(...)): g.decision_devis(devis_id,statut); return retour(f'/devis/{devis_id}')

    @app.post('/devis/{devis_id}/dupliquer')
    def copie(devis_id:int): return retour('/devis/'+str(g.dupliquer_devis(devis_id)))

    @app.get('/devis/{devis_id}/pdf')
    def pdf_devis(devis_id:int):
        s=g.calculer(devis_id); brouillon=not db.obtenir_devis(devis_id)['instantane']
        return Response(generer(s,brouillon),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="{s.get("numero","brouillon-"+str(devis_id))}.pdf"'})

    @app.post('/devis/{devis_id}/facturer')
    def facturer(devis_id:int,date_facture:str=Form(...),echeance:str=Form(...)):
        return retour('/factures/'+str(g.creer_facture(devis_id,date_facture,echeance)))

    @app.get('/factures')
    def factures(request:Request):
        docs=g.documents()
        for d in docs:
            d['client']=json.loads(d['instantane'])['client']['nom']; d['reste']=max(0,d['total_centiemes']-d['paye']-d['credite'])
        return vue(request,'factures.html',documents=docs)

    @app.get('/factures/{identifiant}')
    def facture(request:Request,identifiant:int):
        document = g.document(identifiant)
        document['contenu'].update(g.conditions_documents())
        return vue(request,'facture.html',document=document)

    @app.get('/factures/{identifiant}/pdf')
    def pdf_facture(identifiant:int):
        d=g.document(identifiant)
        return Response(generer(d['contenu']),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="{d["numero"]}.pdf"'})

    @app.post('/factures/{identifiant}/paiement')
    def paiement(identifiant:int,date_paiement:str=Form(...),montant:str=Form(...),mode:str=Form(...),reference:str=Form('')):
        g.payer(identifiant,date_paiement,montant,mode,reference); return retour(f'/factures/{identifiant}')

    @app.post('/factures/{identifiant}/avoir')
    async def avoir(request:Request,identifiant:int):
        form=await request.form()
        quantites={k[2:]:str(v) for k,v in form.items() if k.startswith('q_')}
        return retour('/factures/'+str(g.creer_avoir(identifiant,str(form.get('motif','')),quantites or None)))

    @app.post('/factures/{identifiant}/rembourser')
    def remboursement(identifiant:int,jour:str=Form(...),montant:str=Form(...),mode:str=Form(...)):
        g.rembourser(identifiant,jour,montant,mode);return retour(f'/factures/{identifiant}')

    @app.get('/reglages')
    def reglages(request:Request): return vue(request,'reglages.html',e=db.obtenir_entreprise())

    @app.post('/reglages')
    def sauver_reglages(validite:str=Form('30'),vente:str=Form(''),reglement:str=Form(''),mention:str=Form(''),periodicite:str=Form(''),solde:str=Form('0'),date_solde:str=Form('')):
        g.regler_entreprise(validite,vente,reglement,mention,periodicite,solde,date_solde); return retour('/reglages')

    @app.post('/entreprise/validite-devis')
    def validite_defaut(validite_devis_jours:str=Form('30')):
        e=db.obtenir_entreprise(); g.regler_entreprise(validite_devis_jours,e['conditions_vente'],e['conditions_reglement'],e['mention_complementaire'],e['periodicite_tva'],str(e['solde_depart_centiemes']/100),e['date_solde_depart']); return retour('/entreprise')

    @app.get('/fiscalite')
    def fiscalite(request:Request,annee:int|None=None):
        annee=annee or g.aujourd_hui().year
        if not 1900<=annee<=g.aujourd_hui().year: raise ValueError('Année invalide.')
        f=db.obtenir_fiscalite_annuelle(annee) or {}
        return vue(request,'fiscalite.html',annee=annee,f=f,proposition=db.proposer_regime_tva(annee))

    @app.post('/fiscalite')
    def sauver_fiscalite(annee:int=Form(...),regime:str=Form(''),date_confirmation:str=Form(''),ca:str=Form(''),date_ca:str=Form('')):
        if not 1900<=annee<=g.aujourd_hui().year: raise ValueError('Année invalide.')
        g.confirmer_fiscalite(annee,regime,date_confirmation,ca,date_ca); return retour(f'/fiscalite?annee={annee}')

    @app.get('/echeances')
    def echeances(request:Request): return vue(request,'echeances.html',rappels=g.liste('SELECT * FROM rappels ORDER BY fait,echeance'))

    @app.post('/echeances')
    def rappel(titre:str=Form(...),echeance:str=Form(...),source:str=Form('')):
        if not titre.strip(): raise ValueError('Titre obligatoire.')
        if source and not source.startswith(('https://','http://')): raise ValueError('Utilisez un lien http ou https.')
        with g.connexion() as c: c.execute('INSERT OR IGNORE INTO rappels(titre,echeance,source) VALUES(?,?,?)',(titre.strip(),g.date_valide(echeance),source))
        return retour('/echeances')

    @app.post('/echeances/{identifiant}/fait')
    def rappel_fait(identifiant:int):
        with g.connexion() as c: c.execute('UPDATE rappels SET fait=1-fait WHERE id=?',(identifiant,))
        return retour('/echeances')

    @app.post('/echeances/calendrier-2026')
    def calendrier():
        e=db.obtenir_entreprise(); periode=e['periodicite_tva']
        if not periode: raise ValueError('Choisissez votre périodicité TVA dans les réglages.')
        dates=['01-15','02-16','03-16','04-15','05-15','06-15','07-15','08-17','09-15','10-15','11-16','12-15']
        with g.connexion() as c:
            for i,j in enumerate(dates,1):
                if periode=='trimestrielle' and i not in (1,4,7,10): continue
                c.execute('INSERT OR IGNORE INTO rappels(titre,echeance,source) VALUES(?,?,?)',('TVA '+periode+' — échéance 2026','2026-'+j,'https://www.service-public.pf/dicp/calendrier-fiscal-polynesie-2026/'))
        return retour('/echeances')

    @app.get('/stock')
    def stock(request:Request): return vue(request,'stock.html',articles=g.stock(),mouvements=g.liste('SELECT s.*,a.designation FROM stock_mouvements s JOIN articles a ON a.id=s.article_id ORDER BY date_mouvement DESC,s.id DESC'))

    @app.post('/stock')
    def stock_mouvement(article_id:int=Form(...),jour:str=Form(...),quantite:str=Form(...),sens:str=Form(...),motif:str=Form(...)):
        g.bouger_stock(article_id,jour,quantite,sens,motif); return retour('/stock')

    @app.get('/aide')
    def aide(request:Request): return vue(request,'aide.html')

    @app.get('/sauvegarde')
    def sauvegarde():
        source=sqlite3.connect(db.DB_PATH); copie=sqlite3.connect(':memory:')
        try:
            source.backup(copie)
            # backup vers un fichier temporaire pour la compatibilité Python 3.10
            import tempfile
            with tempfile.TemporaryDirectory() as dossier:
                chemin=Path(dossier)/'patenteasy.db'; cible=sqlite3.connect(chemin)
                try: copie.backup(cible)
                finally: cible.close()
                donnees=chemin.read_bytes()
        finally: source.close(); copie.close()
        return Response(donnees,media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="patenteasy-{g.aujourd_hui()}.db"'})

    @app.get('/export/journal')
    def exporter():
        sortie=io.StringIO(); writer=csv.writer(sortie,delimiter=';')
        writer.writerow(['Date','Libellé','Type','Montant F CFP'])
        for o in g.liste('SELECT * FROM operations ORDER BY date_operation,id'):
            libelle=o['libelle']
            if libelle.startswith(('=','+','-','@','\t','\r')): libelle="'"+libelle
            writer.writerow([o['date_operation'],libelle,o['type_operation'],monnaie(o['montant_centiemes'])])
        return Response('\ufeff'+sortie.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="journal-patenteasy.csv"'})

    @app.on_event('startup')
    def demarrage(): initialiser()

    import mises_a_jour
    mises_a_jour.installer(app, templates)
