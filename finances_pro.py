# SPDX-License-Identifier: GPL-3.0-or-later
"""Achats et préparations fiscales dans la base chiffrée existante."""
import json
from datetime import date
from calendar import monthrange
import database as db
import gestion as g
from licences_pro import LicencePro
from finances_calculs import lignes_valides, jour, entier, synthese

def migrer(base):
    with base.session() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS licence_pro(id INTEGER PRIMARY KEY CHECK(id=1),contenu TEXT NOT NULL,dernier TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS achats_pro(id INTEGER PRIMARY KEY,contenu TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS paiements_achats_pro(id INTEGER PRIMARY KEY,achat_id INTEGER NOT NULL REFERENCES achats_pro(id),operation_id INTEGER UNIQUE REFERENCES operations(id),jour TEXT NOT NULL,montant INTEGER NOT NULL CHECK(montant>0));
        CREATE TABLE IF NOT EXISTS documents_pro(id INTEGER PRIMARY KEY REFERENCES documents(id),contenu TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS profil_pro(id INTEGER PRIMARY KEY CHECK(id=1),contenu TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ajustements_pro(id INTEGER PRIMARY KEY,jour TEXT NOT NULL,montant INTEGER NOT NULL,motif TEXT NOT NULL,document_id INTEGER REFERENCES documents(id));
        CREATE TABLE IF NOT EXISTS declarations_pro(id INTEGER PRIMARY KEY,genre TEXT NOT NULL,debut TEXT NOT NULL,fin TEXT NOT NULL,echeance TEXT NOT NULL,source TEXT NOT NULL,contenu TEXT NOT NULL,statut TEXT NOT NULL DEFAULT 'a_verifier',preuve TEXT NOT NULL DEFAULT '');
        ''')

class FinancesPro:
    def __init__(self, base=None, licence=None):
        self.base=base or db.base
        self.licence=licence or LicencePro(self.base)

    def profil(self):
        self.licence.exiger('administratif')
        with self.base.session() as c:r=c.execute('SELECT contenu FROM profil_pro WHERE id=1').fetchone()
        return json.loads(r[0]) if r else {}

    def enregistrer_profil(self,profil):
        self.licence.exiger('administratif')
        if profil.get('fiscal','') not in ('','tpe','it','is'):raise ValueError('Régime administratif invalide.')
        with self.base.session() as c:c.execute('INSERT OR REPLACE INTO profil_pro VALUES(1,?)',(json.dumps(profil,ensure_ascii=False),))

    def achats(self):
        self.licence.exiger('finance_tva')
        with self.base.session() as c:
            rows=c.execute('SELECT * FROM achats_pro ORDER BY id DESC').fetchall()
            resultat=[]
            for r in rows:
                a=json.loads(r['contenu']);a['id']=r['id']
                a['paiements']=[{'date':p['jour'],'montant':p['montant']} for p in c.execute('SELECT * FROM paiements_achats_pro WHERE achat_id=? ORDER BY jour,id',(r['id'],))]
                a['ttc']=sum(l['ttc'] for l in a['lignes']);a['regle']=sum(p['montant'] for p in a['paiements']);a['reste']=a['ttc']-a['regle']
                resultat.append(a)
        return resultat

    def ajouter_achat(self,a,montant_regle=0,date_reglement='',operation_existante=None):
        self.licence.exiger('finance_tva')
        a=dict(a);a['date']=jour(a['date']);a['livraison']=jour(a['livraison']) if a.get('livraison') else ''
        if a['date']>date.today().isoformat() or (a['livraison'] and a['livraison']>date.today().isoformat()):raise ValueError('Vérifiez les dates de facture et livraison.')
        if not a.get('fournisseur','').strip() or not a.get('reference','').strip():raise ValueError('Fournisseur et référence obligatoires.')
        a['lignes']=lignes_valides(a['lignes']);
        if any(l['nature']=='debits' for l in a['lignes']) and a.get('autorisation_debits') is not True:raise ValueError('Confirmez l’autorisation pour les débits.')
        if any(l['nature']=='bien' for l in a['lignes']) and not a['livraison']:raise ValueError('Livraison réelle des biens requise.')
        total=sum(l['ttc'] for l in a['lignes']);entier(montant_regle)
        if montant_regle>total:raise ValueError('Le règlement dépasse le TTC.')
        if montant_regle:jour(date_reglement)
        with self.base.session() as c:
            ancien=None
            if operation_existante is not None:
                if montant_regle:raise ValueError('Ne ressaisissez pas le paiement d’une dépense existante.')
                ancien=c.execute('SELECT * FROM operations WHERE id=?',(operation_existante,)).fetchone()
                if not ancien or ancien['type_operation']!='depense' or ancien['date_operation']<a['date'] or ancien['montant_centiemes']>total:raise ValueError('Dépense incompatible avec cette facture fournisseur.')
                if c.execute('SELECT 1 FROM paiements_achats_pro WHERE operation_id=?',(operation_existante,)).fetchone() or c.execute('SELECT 1 FROM remboursements WHERE operation_id=?',(operation_existante,)).fetchone():raise ValueError('Cette dépense est déjà liée à un règlement ou remboursement.')
            ident=c.execute('INSERT INTO achats_pro(contenu) VALUES(?)',(json.dumps(a,ensure_ascii=False),)).lastrowid
            if ancien:c.execute('INSERT INTO paiements_achats_pro(achat_id,operation_id,jour,montant) VALUES(?,?,?,?)',(ident,operation_existante,ancien['date_operation'],ancien['montant_centiemes']))
            if montant_regle:self._payer(c,ident,a,date_reglement,montant_regle,a.get("mode_reglement","autre"),a.get("banque_reglement",""))
        return ident

    def _payer(self,c,ident,a,d,m,mode="autre",banque="",reference=""):
        if d<a['date'] or d>date.today().isoformat():raise ValueError('Date de règlement invalide.')
        if mode not in ('virement','cheque','carte','especes','autre'): raise ValueError('Moyen de paiement invalide.')
        banque=g.GestionDocuments(self.base).verifier_banque(banque,mode)
        libelle='Règlement fournisseur '+a['fournisseur']+' · '+a['reference']+' · '+mode+(' · '+banque if banque else '')+(' · '+reference if reference else '')
        op=c.execute("INSERT INTO operations(date_operation,libelle,type_operation,montant_centiemes,banque) VALUES(?,?,'depense',?,?)",(d,libelle,m,banque)).lastrowid
        c.execute('INSERT INTO paiements_achats_pro(achat_id,operation_id,jour,montant) VALUES(?,?,?,?)',(ident,op,d,m))

    def payer_achat(self,ident,d,m,mode="autre",banque="",reference=""):
        self.licence.exiger('finance_tva');jour(d);entier(m,1)
        with self.base.session() as c:
            r=c.execute('SELECT contenu FROM achats_pro WHERE id=?',(ident,)).fetchone()
            if not r:raise ValueError('Achat absent.')
            a=json.loads(r[0]);paye=c.execute('SELECT COALESCE(SUM(montant),0) FROM paiements_achats_pro WHERE achat_id=?',(ident,)).fetchone()[0]
            if paye+m>sum(l['ttc'] for l in a['lignes']):raise ValueError('Le paiement dépasse le reste fournisseur.')
            self._payer(c,ident,a,d,m,mode,banque,reference)

    def factures(self):
        self.licence.exiger('finance_tva')
        return g.GestionDocuments(self.base).documents()

    def qualifier(self,ident,natures,livraison='',autorisation_debits=False):
        self.licence.exiger('finance_tva')
        s=g.GestionDocuments(self.base).document(ident)['contenu']
        if len(natures)!=len(s['lignes']) or any(n not in ('bien','service','debits') for n in natures):raise ValueError('Qualifiez chaque ligne de la facture.')
        if 'debits' in natures and autorisation_debits is not True:raise ValueError('Confirmez votre autorisation DICP pour les débits.')
        if livraison:jour(livraison)
        if 'bien' in natures and not livraison:raise ValueError('Renseignez la date réelle de livraison des biens.')
        with self.base.session() as c:c.execute('INSERT OR REPLACE INTO documents_pro VALUES(?,?)',(ident,json.dumps({'natures':natures,'livraison':livraison,'autorisation_debits':autorisation_debits}),))

    def ajuster(self,d,m,motif,document_id=None):
        self.licence.exiger('finance_tva');jour(d)
        if type(m) is not int or not motif.strip():raise ValueError('Montant signé et motif obligatoires.')
        with self.base.session() as c:c.execute('INSERT INTO ajustements_pro(jour,montant,motif,document_id) VALUES(?,?,?,?)',(d,m,motif,document_id))

    def calculer(self,debut,fin,regime,credit=0):
        self.licence.exiger('finance_tva');entier(credit)
        documents=[];avertissements=[]
        with self.base.session() as c:
            corrections=[{'date':r['jour'],'montant':r['montant'],'motif':r['motif']} for r in c.execute('SELECT * FROM ajustements_pro')]
            for d in g.GestionDocuments(self.base).documents():
                if d['date_document']>fin:continue
                s=json.loads(d['instantane'])
                if d['type']=='avoir':
                    if debut<=d['date_document']<=fin and not c.execute('SELECT 1 FROM ajustements_pro WHERE document_id=?',(d['id'],)).fetchone():
                        avertissements.append('Avoir '+d['numero']+' : vérifier et enregistrer sa régularisation de TVA.')
                    continue
                r=c.execute('SELECT contenu FROM documents_pro WHERE id=?',(d['id'],)).fetchone();q=json.loads(r[0]) if r else {}
                lignes=[{'ht':l['ht'],'tva':l['tva'],'taux':l['taxe_centiemes'],'nature':q.get('natures',['inconnue']*len(s['lignes']))[i]} for i,l in enumerate(s['lignes'])]
                paiements=[{'date':r['date_paiement'],'montant':r['montant_centiemes']} for r in c.execute('SELECT * FROM paiements WHERE document_id=? ORDER BY date_paiement,id',(d['id'],))]
                # Un document historique sans qualification ne sera pas déclaré silencieusement.
                incomplet='' if q else 'Facture '+d['numero']+' : nature et date de livraison à confirmer.'
                documents.append({'date':d['date_document'],'ttc':s['ttc'],'lignes':lignes,'paiements':paiements,'livraison':q.get('livraison',''),'incomplet':incomplet})
            anciens=c.execute("SELECT COUNT(*) FROM operations o WHERE o.type_operation='depense' AND o.date_operation BETWEEN ? AND ? AND NOT EXISTS(SELECT 1 FROM paiements_achats_pro p WHERE p.operation_id=o.id) AND NOT EXISTS(SELECT 1 FROM remboursements r WHERE r.operation_id=o.id)",(debut,fin)).fetchone()[0]
            recettes_non_detaillees=c.execute("SELECT COUNT(*) FROM operations o WHERE o.type_operation='recette' AND o.date_operation BETWEEN ? AND ? AND NOT EXISTS(SELECT 1 FROM paiements p WHERE p.operation_id=o.id)",(debut,fin)).fetchone()[0]
        achats=self.achats()
        for a in achats:
            if any(l['tva'] and l['deduction'] for l in a['lignes']) and not a.get('justificatif'):
                a['incomplet']='Achat '+a['reference']+' : TVA exclue de la déduction, justificatif manquant.'
        result=synthese(debut,fin,documents,achats,regime,credit,corrections)
        if recettes_non_detaillees:avertissements.append(str(recettes_non_detaillees)+' recette(s) hors encaissement de facture : TVA à vérifier et régulariser si nécessaire.')
        if anciens:avertissements.append(str(anciens)+' ancienne(s) dépense(s) sans détail HT/TVA : à rapprocher avant déclaration.')
        totaux={'recette':0,'depense':0};alertes_tresorerie=[]
        entreprise=self.base.obtenir_entreprise() or {};debut_activite=entreprise.get('date_debut_activite','')
        for annee in range(int(debut[:4]),int(fin[:4])+1):
            fiscal=self.base.obtenir_fiscalite_annuelle(annee) or {};fin_reprise=fiscal.get('date_fin_reprise','')
            for op in self.base.lister_operations(annee):
                if debut<=op['date_operation']<=fin:
                    if fin_reprise and op['date_operation']<=fin_reprise:
                        alertes_tresorerie.append('Des opérations du journal incluses dans la reprise sont exclues pour éviter un double compte.');continue
                    totaux[op['type_operation']]+=op['montant_centiemes']
            reprises=self.base.lister_reprise_mensuelle(annee)
            if reprises and (not fin_reprise or not debut_activite):
                alertes_tresorerie.append('Reprise exclue : renseignez le début d’activité et la date de fin de reprise.');continue
            for ligne in reprises:
                premier=f"{annee:04d}-{ligne['mois']:02d}-01"
                dernier=f"{annee:04d}-{ligne['mois']:02d}-{monthrange(annee,ligne['mois'])[1]:02d}"
                premier=max(premier,debut_activite);dernier=min(dernier,fin_reprise)
                if dernier<premier or dernier<debut or premier>fin:continue
                if debut>premier or fin<dernier:
                    alertes_tresorerie.append('Une reprise mensuelle recoupe partiellement la période : son montant est exclu, sans répartition journalière inventée.');continue
                for type_op,col in (('recette','recettes_centiemes'),('depense','depenses_centiemes')):
                    if ligne[col] is None:alertes_tresorerie.append('Reprise incomplète : les totaux de la période restent partiels.')
                    else:totaux[type_op]+=ligne[col]
        result['recettes_ttc']=totaux['recette'];result['depenses_ttc']=totaux['depense']
        result['solde_periode']=result['recettes_ttc']-result['depenses_ttc']
        if regime=='franchise':
            result['taux']=[]
            avertissements=[]
            if any(l['tva'] for d in documents if debut<=d['date']<=fin for l in d['lignes']):
                avertissements.append('Des factures de cette période comportent de la TVA : vérifiez le régime sélectionné.')
            rappel=g.GestionDocuments(self.base).rappel_seuil_ca(int(fin[:4]))
            if rappel: avertissements.append(rappel)
            result['alertes']=avertissements
        else: result['alertes']=list(dict.fromkeys(result['alertes']+avertissements))
        result['alertes']=list(dict.fromkeys(result['alertes']+alertes_tresorerie))
        result['depenses_non_detaillees']=anciens
        return result

    def preparer(self,genre,debut,fin,echeance,source,regime,credit=0):
        self.licence.exiger('administratif')
        if genre not in ('tva1010','cps_rns','it','tpe','tva1040'):raise ValueError('Document non pris en charge.')
        e=self.base.obtenir_entreprise() or {}
        if e.get('pays')!='PF' or e.get('devise')!='XPF':raise ValueError('Les formulaires DICP/CPS nécessitent un profil Polynésie/XPF.')
        jour(echeance)
        if not source.startswith(('https://www.service-public.pf/','https://www.cps.pf/','https://wwwapi.cps.pf/')):raise ValueError('Indiquez la source officielle de l’échéance.')
        profil=self.profil()
        if genre=='it' and profil.get('fiscal')=='tpe':raise ValueError('Le régime TPE dispense de la déclaration IT annuelle ; utilisez la démarche TPE si nécessaire.')
        if genre in ('tva1010','tva1040') and regime!='reel':raise ValueError('Pas de déduction ni déclaration TVA pour la franchise en base dans ce module.')
        s=self.calculer(debut,fin,regime,credit)
        with self.base.session() as c:
            recettes=c.execute("SELECT COALESCE(SUM(montant_centiemes),0) FROM operations WHERE type_operation='recette' AND date_operation BETWEEN ? AND ?",(debut,fin)).fetchone()[0]
            depenses=c.execute("SELECT COALESCE(SUM(montant_centiemes),0) FROM operations WHERE type_operation='depense' AND date_operation BETWEEN ? AND ?",(debut,fin)).fetchone()[0]
            contenu={'entreprise':e,'profil':profil,'tva':s,'recettes_ttc':recettes,'depenses_ttc':depenses,'genre':genre,'debut':debut,'fin':fin,'echeance':echeance,'source':source,'statut':'a_verifier','manquants':list(s['alertes'])}
            if genre=='cps_rns':contenu['manquants']+=['Confirmer les autres revenus et annexes CPS.','Vérifier les charges déductibles, cotisations RNS et l’option forfaitaire.']
            if genre in ('it','tpe'):contenu['manquants']+=['Confirmer les recettes brutes HT et leur ventilation ventes/prestations ; les recettes du journal ne sont pas automatiquement le chiffre d’affaires fiscal.']
            ident=c.execute('INSERT INTO declarations_pro(genre,debut,fin,echeance,source,contenu) VALUES(?,?,?,?,?,?)',(genre,debut,fin,echeance,source,json.dumps(contenu,ensure_ascii=False))).lastrowid
        return ident,contenu

    def declarations(self):
        self.licence.exiger('administratif')
        with self.base.session() as c:return [dict(r) for r in c.execute('SELECT * FROM declarations_pro ORDER BY echeance,id')]

    def suivre(self,ident,statut,preuve=''):
        self.licence.exiger('administratif')
        if statut not in ('a_verifier','depose','paye'):raise ValueError('État invalide.')
        if statut!='a_verifier' and not preuve.strip():raise ValueError('Indiquez la référence de preuve du dépôt ou paiement.')
        with self.base.session() as c:c.execute('UPDATE declarations_pro SET statut=?,preuve=? WHERE id=?',(statut,preuve,ident))

    def rappels(self):
        self.licence.exiger('administratif');aujourdhui=date.today()
        return [{**r,'jours':(date.fromisoformat(r['echeance'])-aujourdhui).days} for r in self.declarations() if r['statut']=='a_verifier' and (date.fromisoformat(r['echeance'])-aujourdhui).days<=30]
