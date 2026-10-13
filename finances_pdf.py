# SPDX-License-Identifier: GPL-3.0-or-later
"""Export d'un dossier préparatoire, explicitement distinct d'une déclaration déposée."""
import json
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def exporter_preparation(service,ident,chemin):
    service.licence.exiger('administratif')
    a=next((r for r in service.declarations() if r['id']==ident),None)
    if a is None:raise ValueError('Préparation introuvable.')
    c=json.loads(a['contenu']);styles=getSampleStyleSheet();story=[]
    def p(texte,style='Normal'):story.append(Paragraph(escape(str(texte)),styles[style]));story.append(Spacer(1,8))
    precision=int(c['entreprise'].get('decimales',0))
    def m(v):return f'{v/(10**precision):,.{precision}f} XPF'
    p('Patenteasy • préparation administrative','Title');p('BROUILLON À VÉRIFIER • ne vaut pas déclaration déposée','Heading2')
    p(c['genre'].upper()+' • '+c['entreprise'].get('nom',''));p('Période : '+c['debut']+' au '+c['fin']);p('Échéance confirmée : '+c['echeance']);p('Source : '+c['source']);p('DN CPS : '+c['profil'].get('dn_cps','À compléter'))
    p('Données préremplies depuis la comptabilité','Heading2');p('Encaissements TTC : '+m(c['recettes_ttc']));p('Décaissements TTC : '+m(c['depenses_ttc']))
    s=c['tva'];p('TVA • régime : '+s['regime'],'Heading2')
    lignes=[['Taux %','Base exigible HT','TVA exigible','TVA déductible']]+[[str(x['taux']/100),m(x['base_exigible']),m(x['tva_exigible']),m(x['tva_deductible'])] for x in s['taux']]
    table=Table(lignes,repeatRows=1);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#164d56')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.5,colors.lightgrey),('FONTSIZE',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(table);story.append(Spacer(1,12))
    for label,k in [('TVA perçue','tva_percue'),('TVA exigible','tva_exigible'),('TVA déductible','tva_deductible'),('Crédit antérieur','credit_precedent'),('Régularisations','regularisations'),('À reverser','a_reverser'),('Crédit','credit')]:p(label+' : '+m(s[k]))
    p('Contrôles et informations à compléter','Heading2')
    for x in c['manquants']:p('• '+x)
    p('Les encaissements TTC ne sont pas automatiquement le chiffre d’affaires fiscal ou le revenu CPS. Rapprochez les pièces et complétez les revenus et charges non connus du logiciel avant de reporter les données dans le formulaire officiel.')
    SimpleDocTemplate(str(chemin),title='Patenteasy • préparation administrative',author='ska_987').build(story)
