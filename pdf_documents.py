# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
import regional
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable, KeepTogether


class ConditionsBasDePage(Flowable):
    """Aligne les conditions au bas de la dernière page, sans réduire le texte.

    Un bloc court passe entièrement à la page suivante si nécessaire. Un texte
    plus long qu'une page est réparti en paragraphes sur les pages suivantes.
    """
    def __init__(self, paragraphes, hauteur_page):
        super().__init__()
        self.paragraphes = paragraphes
        self.hauteur_page = hauteur_page

    def wrap(self, largeur, hauteur):
        self.largeur = largeur
        self.mesures = [(p, p.wrap(largeur, self.hauteur_page)[1]) for p in self.paragraphes]
        self.hauteur_texte = 10 + sum(h + 4 for _, h in self.mesures)
        # KeepTogether mesure ses enfants avec une hauteur artificiellement
        # grande : lui donner la hauteur réelle du texte, sans l'espace libre.
        return largeur, self.hauteur_texte if hauteur > self.hauteur_page else max(self.hauteur_texte, hauteur)

    def split(self, largeur, hauteur):
        if self.hauteur_texte <= self.hauteur_page:
            return []
        places, suite = [], []
        disponible = hauteur - 10
        for i, (paragraphe, h) in enumerate(self.mesures):
            if h + 4 <= disponible:
                places.append(paragraphe)
                disponible -= h + 4
                continue
            morceaux = paragraphe.split(largeur, max(0, disponible - 4))
            if morceaux:
                places.append(morceaux[0])
                suite.extend(morceaux[1:])
            else:
                suite.append(paragraphe)
            suite.extend(self.paragraphes[i + 1:])
            break
        if not places:
            return []
        return [ConditionsBasDePage(places, self.hauteur_page),
                ConditionsBasDePage(suite, self.hauteur_page)] if suite else [ConditionsBasDePage(places, self.hauteur_page)]

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(colors.HexColor('#cbd4df'))
        self.canv.setLineWidth(.4)
        self.canv.line(0, self.hauteur_texte - 1, self.largeur, self.hauteur_texte - 1)
        y = self.hauteur_texte - 10
        for paragraphe, hauteur in self.mesures:
            y -= hauteur
            paragraphe.drawOn(self.canv, 0, y)
            y -= 4
        self.canv.restoreState()


def monnaie(n):
    entier, fraction = divmod(abs(n),100)
    return ('-' if n<0 else '')+f'{entier:,}'.replace(',',' ')+(f',{fraction:02d}' if fraction else '')


def generer(s, brouillon=False, *, conditions=None):
    # Les montants et identités restent ceux de l'instantané. Les conditions
    # sont lues à chaque export : même les anciens documents suivent les Réglages.
    if conditions is None:
        import gestion
        conditions = gestion.conditions_documents()
    sortie=BytesIO()
    doc=SimpleDocTemplate(sortie,pagesize=(210*mm,297*mm),rightMargin=16*mm,leftMargin=16*mm,topMargin=16*mm,bottomMargin=18*mm,
        title=s.get('numero','Devis brouillon'),author=s['entreprise']['nom'])
    styles=getSampleStyleSheet()
    for style in styles.byName.values():
        if hasattr(style, 'fontName'):
            style.fontName='Patenteasy-Bold' if 'Bold' in style.fontName else 'Patenteasy'
    styles.add(ParagraphStyle(name='Petit',fontName='Patenteasy',fontSize=8,leading=11))
    styles['Normal'].fontSize=9; styles['Normal'].leading=13
    def p(t,style='Normal'):
        return Paragraph(escape(str(t)).replace('\n','<br/>'),styles[style])
    e=s['entreprise']; client=s['client']; typ=s.get('type','devis')
    cfg=regional.configuration(e)
    M=lambda valeur:regional.montant(valeur,e,unite=False)
    D=lambda valeur:regional.afficher_date(valeur,e)
    taxe=cfg['nom_taxe']
    anglais=cfg['langue']=='en'
    labels={'devis':'QUOTE','facture':'INVOICE','avoir':'CREDIT NOTE'} if anglais else {'devis':'DEVIS','facture':'FACTURE','avoir':'AVOIR'}
    titre=labels[typ]
    from localisation import traduire
    P=lambda txt:traduire(txt, cfg['langue'])
    elements=[p(titre+((' — DRAFT' if anglais else ' — BROUILLON') if brouillon else ''),'Title'),p(s.get('numero',P('Sans numéro')),'Heading2')]
    identite=e['nom']+('\n'+e['adresse'] if e['adresse'] else '')
    if e.get('numero_tahiti'):identite+='\n'+cfg['libelle_identifiant']+' : '+e['numero_tahiti']
    if e.get('numero_rcs'): identite+='\nRegistre : '+e['numero_rcs']
    identite+='\n'+e['telephone']+' '+e['email']
    adresse_client=client['nom']+('\n'+client['adresse'] if client['adresse'] else '')
    entete=Table([[p(identite),p(('CUSTOMER\n' if anglais else 'CLIENT\n')+adresse_client)]],colWidths=[89*mm,89*mm])
    entete.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f0f3f7')),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12)]))
    elements += [entete,Spacer(1,8*mm)]
    elements.append(p(P('Date : ')+D(s.get('date_document',s['devis']['date_devis']))))
    if typ=='devis': elements.append(p(P('Valable jusqu’au : ')+D(s['validite'])))
    if typ=='facture': elements.append(p(P('Échéance de règlement : ')+D(s['echeance'])))
    if s.get('numero_devis'): elements.append(p(P('Devis de référence : ')+s['numero_devis']))
    if s.get('origine_numero'): elements.append(p(P('Facture corrigée : ')+s['origine_numero']+' — '+s['motif']))
    if s['devis']['objet']: elements.append(p(s['devis']['objet'],'Heading2'))
    elements.append(Spacer(1,6*mm))
    rows=[[p(v,'Petit') for v in [P('Référence'),P('Désignation'),P('Qté / unité'),P('PU HT'),taxe+' %',P('Total HT')]]]
    for l in s['lignes']:
        rows.append([p(l.get('reference', ''),'Petit'),p(l['designation'],'Petit'),p(monnaie(l['quantite_centiemes'])+' '+l['unite'],'Petit'),p(M(l['prix_unitaire_centiemes']),'Petit'),p(monnaie(l['taxe_centiemes']) if s['regime']=='reel' else '—','Petit'),p(M(l['ht']),'Petit')])
    table=Table(rows,colWidths=[25*mm,55*mm,25*mm,26*mm,19*mm,28*mm],repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8edf4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#cbd4df')),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    elements += [table,Spacer(1,6*mm)]
    fin = [p(P('Total HT : ')+M(s['ht'])+' '+cfg['devise'],'Heading3')]
    if s['regime']=='reel':
        for g in s['groupes']:
            fin.append(p(taxe+' '+monnaie(g['taux'])+' % — base '+M(g['base'])+' : '+M(g['tva'])+' '+cfg['devise']))
    if s['mention_tva']: fin.append(p(s['mention_tva']))
    fin.append(p((P('Montant de l’avoir') if typ=='avoir' else P('Total à payer'))+' : '+M(s['ttc'])+' '+cfg['devise'],'Heading2'))
    if not s['regime']: fin.append(p(P('Sans taxe calculée — choix non renseigné.')))
    if typ=='devis': fin.extend([Spacer(1,6*mm),p(P('Acceptation : nom, date et accord écrit du client. Conservez la preuve d’acceptation avec ce devis.'))])
    paragraphes = []
    for titre, champ in [('Conditions de vente', 'conditions_vente'), ('Conditions de règlement', 'conditions_reglement'), ('Mentions complémentaires', 'mention_complementaire')]:
        texte = conditions.get(champ, '').strip()
        if texte:
            paragraphes.append(Paragraph('<b>' + escape(P(titre)) + '</b><br/>' + escape(texte).replace('\n', '<br/>'), styles['Petit']))
    if paragraphes:
        bloc = ConditionsBasDePage(paragraphes, doc.height - 12)
        hauteur = bloc.wrap(doc.width - 12, 10**6)[1]
        if hauteur <= (doc.height - 12) / 2:
            elements.append(KeepTogether(fin + [bloc]))
        else:
            elements.extend(fin + [bloc])
    else:
        elements.extend(fin)
    def pied(canvas,document):
        canvas.saveState(); canvas.setFont('Patenteasy',8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(16*mm,10*mm,e['nom']+' — '+cfg['devise'])
        canvas.drawRightString(194*mm,10*mm,P('Page ')+str(document.page)); canvas.restoreState()
    doc.build(elements,onFirstPage=pied,onLaterPages=pied)
    return sortie.getvalue()
