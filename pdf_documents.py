# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
from io import BytesIO
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = Path(__file__).resolve().parent / "static" / "fonts"
pdfmetrics.registerFont(TTFont("Patenteasy", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("Patenteasy-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("Patenteasy", normal="Patenteasy", bold="Patenteasy-Bold", italic="Patenteasy", boldItalic="Patenteasy-Bold")
from html import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def monnaie(n):
    entier, fraction = divmod(abs(n),100)
    return ('-' if n<0 else '')+f'{entier:,}'.replace(',',' ')+(f',{fraction:02d}' if fraction else '')


def generer(s, brouillon=False):
    sortie=BytesIO()
    doc=SimpleDocTemplate(sortie,pagesize=(210*mm,297*mm),rightMargin=16*mm,leftMargin=16*mm,topMargin=16*mm,bottomMargin=18*mm,
        title=s.get('numero','Devis brouillon'),author=s['entreprise']['nom'])
    styles=getSampleStyleSheet()
    for style in styles.byName.values():
        if hasattr(style, 'fontName'):
            style.fontName='Patenteasy-Bold' if 'Bold' in style.fontName else 'Patenteasy'
    styles.add(ParagraphStyle(name='Petit',fontName='Patenteasy',fontSize=8,leading=11))
    styles['Normal'].fontSize=9; styles['Normal'].leading=13
    def p(t,style='Normal'): return Paragraph(escape(str(t)).replace('\n','<br/>'),styles[style])
    e=s['entreprise']; client=s['client']; typ=s.get('type','devis')
    titre={'devis':'DEVIS','facture':'FACTURE','avoir':'AVOIR'}[typ]
    elements=[p(titre+(' — BROUILLON' if brouillon else ''),'Title'),p(s.get('numero','Sans numéro'),'Heading2')]
    identite=e['nom']+'\n'+e['adresse']+'\nN° TAHITI : '+e['numero_tahiti']
    if e.get('numero_rcs'): identite+='\nRCS : '+e['numero_rcs']
    identite+='\n'+e['telephone']+' '+e['email']
    adresse_client=client['nom']+('\n'+client['adresse'] if client['adresse'] else '')
    entete=Table([[p(identite),p('CLIENT\n'+adresse_client)]],colWidths=[89*mm,89*mm])
    entete.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f0f3f7')),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12)]))
    elements += [entete,Spacer(1,8*mm)]
    elements.append(p('Date : '+s.get('date_document',s['devis']['date_devis'])))
    if typ=='devis': elements.append(p('Valable jusqu’au : '+s['validite']))
    if typ=='facture': elements.append(p('Échéance de règlement : '+s['echeance']))
    if s.get('numero_devis'): elements.append(p('Devis de référence : '+s['numero_devis']))
    if s.get('origine_numero'): elements.append(p('Facture corrigée : '+s['origine_numero']+' — '+s['motif']))
    if s['devis']['objet']: elements.append(p(s['devis']['objet'],'Heading2'))
    elements.append(Spacer(1,6*mm))
    rows=[[p(v,'Petit') for v in ['Désignation','Qté / unité','PU HT','TVA %','Total HT']]]
    for l in s['lignes']:
        rows.append([p((l['reference']+' — ' if l['reference'] else '')+l['designation'],'Petit'),p(monnaie(l['quantite_centiemes'])+' '+l['unite'],'Petit'),p(monnaie(l['prix_unitaire_centiemes']),'Petit'),p(monnaie(l['taxe_centiemes']) if s['regime']=='reel' else '—','Petit'),p(monnaie(l['ht']),'Petit')])
    table=Table(rows,colWidths=[78*mm,28*mm,25*mm,19*mm,28*mm],repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8edf4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#cbd4df')),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    elements += [table,Spacer(1,6*mm),p('Total HT : '+monnaie(s['ht'])+' F CFP','Heading3')]
    if s['regime']=='reel':
        for g in s['groupes']:
            elements.append(p('TVA '+monnaie(g['taux'])+' % — base '+monnaie(g['base'])+' : '+monnaie(g['tva'])+' F CFP'))
    if s['mention_tva']: elements.append(p(s['mention_tva']))
    elements.append(p(('Montant de l’avoir' if typ=='avoir' else 'Total à payer')+' : '+monnaie(s['ttc'])+' F CFP','Heading2'))
    if not s['regime']: elements.append(p('Régime fiscal à confirmer : total définitif non établi.'))
    for titre,champ in [('Conditions de vente','conditions_vente'),('Conditions de règlement','conditions_reglement'),('Mentions complémentaires','mention_complementaire')]:
        if s.get(champ): elements.extend([p(titre,'Heading3'),p(s[champ])])
    if typ=='devis': elements.extend([Spacer(1,6*mm),p('Acceptation : nom, date et accord écrit du client. Conservez la preuve d’acceptation avec ce devis.')])
    def pied(canvas,document):
        canvas.saveState(); canvas.setFont('Patenteasy',8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(16*mm,10*mm,e['nom']+' — F CFP (XPF)')
        canvas.drawRightString(194*mm,10*mm,'Page '+str(document.page)); canvas.restoreState()
    doc.build(elements,onFirstPage=pied,onLaterPages=pied)
    return sortie.getvalue()
