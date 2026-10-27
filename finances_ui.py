# SPDX-License-Identifier: GPL-3.0-or-later
"""Écrans du module annuel ; toutes les actions sont contrôlées par le service."""
import json
from datetime import date
from pathlib import Path
from PySide6.QtCore import QDate, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QLabel,QPushButton,QHBoxLayout,QVBoxLayout,QFormLayout,QLineEdit,
 QComboBox,QDateEdit,QCheckBox,QDialog,QDialogButtonBox,QTableWidget,QTableWidgetItem,
 QFileDialog,QMessageBox,QInputDialog,QPlainTextEdit)
import database as db
import gestion as g
from finances_pro import FinancesPro
from licences_pro import LicencePro
from qt_app import Page, money_text, marquer_module

SOURCES={'tva1010':'https://www.service-public.pf/dicp/', 'it':'https://www.service-public.pf/dicp/',
 'tpe':'https://www.service-public.pf/dicp/', 'tva1040':'https://www.service-public.pf/dicp/',
 'cps_rns':'https://www.cps.pf/'}

def bouton(layout,texte,action):
    b=QPushButton(texte);b.clicked.connect(action);layout.addWidget(b);return b

def calendrier(jour=None):
    d=QDateEdit(QDate.fromString(jour,'yyyy-MM-dd') if jour else QDate.currentDate());d.setCalendarPopup(True);d.setDisplayFormat('dd/MM/yyyy');return d

def iso(widget):return widget.date().toString('yyyy-MM-dd')

def combo(paires):
    w=QComboBox()
    for texte,valeur in paires:w.addItem(texte,valeur)
    return w

def montant(texte):return db.base.convertir_montant(texte or '0')

class ProPage(Page):
    def __init__(self,titre,parent,module):
        super().__init__('Module annuel',titre,('Dépenses détaillées HT / TVA / TTC et calculs de TVA par taux.' if module=='finance_tva' else 'Dossiers administratifs préparatoires et rappels des échéances.')+' Licence annuelle requise pour débloquer les actions.',parent)
        self.service=FinancesPro();self.module=module;self.titre_module=titre;self.etat=QLabel();self.etat.setWordWrap(True);self.layout.addWidget(self.etat)
        h=QHBoxLayout();bouton(h,'Ouvrir Licence',lambda:self.navigate.emit('licence'));bouton(h,'Demander une licence annuelle',lambda:QDesktopServices.openUrl(QUrl('mailto:sav.centreprotech@proton.me?subject=Licence%20annuelle%20Patenteasy')));self.layout.addLayout(h)
        self.actions_pro=[]
    def executer(self,action):
        try:action()
        except Exception as e:QMessageBox.warning(self,'Patenteasy',str(e))
    def autorise(self):
        s=self.service.licence.etat();ok=marquer_module(self.etat,self.titre_module,self.module,s)
        if not ok:self.etat.setToolTip('Finances : calculs TVA et dépenses détaillées. Administratif : dossiers préparatoires et rappels. Une licence annuelle autorisant ce module est nécessaire.')
        for a in self.actions_pro:a.setEnabled(ok)
        return ok

class LicencePage(Page):
    def __init__(self,parent=None):
        super().__init__('Patenteasy','Licence annuelle','La TVA sur les factures reste disponible gratuitement. La licence débloque les calculs financiers et la préparation administrative.',parent)
        self.licence=LicencePro(db.base);self.info=QLabel();self.info.setWordWrap(True);self.layout.addWidget(self.info)
        bouton(self.layout,'Importer ma licence SKA',lambda:self.importer())
        bouton(self.layout,'Demander une licence annuelle',lambda:QDesktopServices.openUrl(QUrl('mailto:sav.centreprotech@proton.me?subject=Licence%20annuelle%20Patenteasy')))
        self.layout.addStretch()
    def refresh(self):
        s=self.licence.etat();self.info.setText(s['message']+'\n'+('Titulaire : '+s.get('titulaire','')+'\nExpiration : '+s.get('expiration','')+'\nModules : '+', '.join(s['modules']) if s['active'] else 'Les fonctions gratuites restent utilisables.'))
    def importer(self):
        chemin,_=QFileDialog.getOpenFileName(self,'Licence SKA','','Licences (*.skalic *.json);;Tous les fichiers (*)')
        if not chemin:return
        try:
            if Path(chemin).stat().st_size>65536:raise ValueError('Licence trop volumineuse.')
            self.licence.importer(Path(chemin).read_text(encoding='utf-8'));self.refresh()
            if hasattr(self.window(),'rafraichir_modules'):self.window().rafraichir_modules()
            QMessageBox.information(self,'Licence','Licence vérifiée et activée.')
        except Exception as e:QMessageBox.warning(self,'Licence',str(e))

class AchatDialog(QDialog):
    def __init__(self,parent=None,franchise=False):
        self.franchise=franchise
        super().__init__(parent);self.setWindowTitle('Dépense détaillée • HT / TVA / TTC');self.resize(1000,550)
        root=QVBoxLayout(self);f=QFormLayout();root.addLayout(f)
        self.fournisseur=QLineEdit();self.reference=QLineEdit();self.date=calendrier();self.livraison=calendrier();self.livre=QCheckBox('Biens livrés à cette date');self.justificatif=QCheckBox('Facture fournisseur conforme conservée');self.debits=QCheckBox('Débits : autorisation DICP / mention fournisseur confirmée')
        for label,w in [('Fournisseur',self.fournisseur),('Référence facture',self.reference),('Date facture',self.date),('Date livraison',self.livraison),('',self.livre),('',self.justificatif),('',self.debits)]:f.addRow(label,w)
        self.table=QTableWidget(0,8);self.table.setHorizontalHeaderLabels(['Libellé','HT','Taux %','TVA','TTC','Nature','Déductible %','Catégorie']);root.addWidget(self.table)
        bouton(root,'Ajouter une ligne' if self.franchise else 'Ajouter un taux / une ligne',self.ajouter)
        self.operation=combo([('Nouvelle dépense',None)]);
        with db.base.session() as c:
            for op in c.execute("SELECT * FROM operations o WHERE type_operation='depense' AND NOT EXISTS(SELECT 1 FROM paiements_achats_pro p WHERE p.operation_id=o.id) AND NOT EXISTS(SELECT 1 FROM remboursements r WHERE r.operation_id=o.id) ORDER BY date_operation DESC"):
                self.operation.addItem(op['date_operation']+' • '+op['libelle']+' • '+money_text(op['montant_centiemes']),op['id'])
        f.addRow('Rapprocher un règlement existant',self.operation)
        self.paye=QLineEdit('0');self.date_paiement=calendrier();f2=QFormLayout();f2.addRow('Déjà réglé TTC',self.paye);f2.addRow('Date règlement',self.date_paiement);root.addLayout(f2)
        self.mode_reglement=combo([('Virement','virement'),('Chèque','cheque'),('Carte','carte'),('Espèces','especes'),('Autre','autre')]);self.banque_reglement=combo([('Non renseignée','')]+[(n,n) for n in g.banques()])
        f2.addRow('Moyen de règlement',self.mode_reglement);f2.addRow('Banque (facultatif)',self.banque_reglement)
        def adapter_banque():
            cash=self.mode_reglement.currentData()=='especes';self.banque_reglement.setEnabled(not cash)
            if cash:self.banque_reglement.setCurrentIndex(0)
        self.mode_reglement.currentIndexChanged.connect(adapter_banque)
        info=QLabel('Une ligne par taux. Renseignez TVA et TTC d’après la facture fournisseur. En franchise, aucune TVA ne sera déduite.');info.setWordWrap(True);root.addWidget(info)
        b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);b.accepted.connect(self.accept);b.rejected.connect(self.reject);root.addWidget(b);self.ajouter()
        if self.franchise:
            self.setWindowTitle('Dépense TTC · Franchise en base')
            for col in (1,2,3,5,6):self.table.setColumnHidden(col,True)
            for w in (self.livraison,self.livre,self.debits):f.setRowVisible(w,False)
            info.setText('Franchise en base : saisissez le montant TTC payé au fournisseur, TVA comprise et non déductible.')
    def ajouter(self):
        r=self.table.rowCount();self.table.insertRow(r)
        for c,v in enumerate(['Dépense','0','16','0','0']):self.table.setItem(r,c,QTableWidgetItem(v))
        self.table.setCellWidget(r,5,combo([('Service','service'),('Bien','bien'),('Débits autorisés','debits')]))
        self.table.setItem(r,6,QTableWidgetItem('100'))
        self.table.setCellWidget(r,7,combo([('Autres charges','autres'),('Achats','achats'),('Immobilisation','immobilisation'),('Personnel','personnel'),('Cotisations RNS','cotisations_rns')]))
    def donnees(self):
        from decimal import Decimal
        lignes=[]
        for r in range(self.table.rowCount()):
            def t(c):return self.table.item(r,c).text().strip()
            if self.franchise:
                ttc=montant(t(4));lignes.append({'libelle':t(0),'ht':ttc,'tva':0,'ttc':ttc,'taux':0,'nature':'service','deduction':0,'categorie':self.table.cellWidget(r,7).currentData()});continue
            nature=self.table.cellWidget(r,5).currentData()
            if nature=='debits' and not self.debits.isChecked():raise ValueError('Confirmez l’autorisation pour les débits.')
            if nature=='bien' and not self.livre.isChecked():raise ValueError('Confirmez la livraison réelle des biens.')
            lignes.append({'libelle':t(0),'ht':montant(t(1)),'taux':int(Decimal(t(2).replace(',','.'))*100),'tva':montant(t(3)),'ttc':montant(t(4)),'nature':nature,'deduction':int(Decimal(t(6).replace(',','.'))*100),'categorie':self.table.cellWidget(r,7).currentData()})
        return {'fournisseur':self.fournisseur.text(),'reference':self.reference.text(),'date':iso(self.date),'livraison':iso(self.livraison) if self.livre.isChecked() else '', 'justificatif':self.justificatif.isChecked(),'lignes':lignes,'autorisation_debits':self.debits.isChecked(),'mode_reglement':self.mode_reglement.currentData(),'banque_reglement':self.banque_reglement.currentData()},montant(self.paye.text()),iso(self.date_paiement)

class FinancesPage(ProPage):
    def __init__(self,parent=None):
        super().__init__('Finances et TVA',parent,'finance_tva')
        h=QHBoxLayout();self.debut=calendrier(date.today().replace(day=1).isoformat());self.fin=calendrier();self.regime=combo([('Confirmer le régime',''),('Franchise en base','franchise'),('Assujetti TVA','reel')]);self.credit=QLineEdit('0')
        for texte,w in [('Du',self.debut),('Au',self.fin),('Régime de la période',self.regime),('Crédit antérieur',self.credit)]:h.addWidget(QLabel(texte));h.addWidget(w)
        self.credit_label=h.itemAt(h.count()-2).widget()
        self.layout.addLayout(h);self.actions_pro.append(bouton(self.layout,'Calculer la période',lambda:self.executer(self.calculer)))
        self.resume=QLabel();self.resume.setWordWrap(True);self.layout.addWidget(self.resume)
        self.taux=QTableWidget(0,7);self.taux.setHorizontalHeaderLabels(['Taux %','Base exigible HT','TVA exigible','TVA perçue','Achats HT','TVA achats','TVA déductible']);self.layout.addWidget(self.taux)
        self.alertes=QLabel();self.alertes.setWordWrap(True);self.layout.addWidget(self.alertes)
        h=QHBoxLayout()
        for label,fn in [('Ajouter une dépense détaillée',self.ajouter),('Régler le fournisseur',self.payer),('Qualifier une facture',self.qualifier),('Régularisation TVA / avoir',self.ajuster)]:self.actions_pro.append(bouton(h,label,lambda checked=False,fn=fn:self.executer(fn)))
        self.layout.addLayout(h);self.achats=QTableWidget(0,6);self.achats.setHorizontalHeaderLabels(['ID','Fournisseur','Référence','HT','TVA','Reste TTC']);self.layout.addWidget(self.achats)
        self.regime.setCurrentIndex(max(0,self.regime.findData(g.regime_a_la_date(iso(self.fin)))))
        self.regime.currentIndexChanged.connect(self.adapter_regime);self.adapter_regime()
    def refresh(self):
        if not self.autorise():
            self.resume.clear();self.alertes.clear();self.taux.setRowCount(0);self.achats.setRowCount(0);return
        self.regime.setCurrentIndex(max(0,self.regime.findData(g.regime_a_la_date(iso(self.fin)))))
        self.executer(self.lister)
    def adapter_regime(self):
        franchise=self.regime.currentData()=='franchise'
        self.findChild(QLabel,'title').setText('Finances · TTC' if franchise else 'Finances et TVA')
        self.findChild(QLabel,'lead').setText('Recettes et dépenses TTC. Franchise en base : TVA non collectée et non déductible.' if franchise else 'Dépenses HT / TVA / TTC et calculs de TVA par taux.')
        self.credit.setVisible(not franchise);self.credit_label.setVisible(not franchise);self.taux.setVisible(not franchise)
        for b in self.actions_pro:
            if b.text() in ('Ajouter une dépense détaillée','Ajouter une dépense TTC'):b.setText('Ajouter une dépense TTC' if franchise else 'Ajouter une dépense détaillée')
            if b.text() in ('Qualifier une facture','Régularisation TVA / avoir'):b.setVisible(not franchise)
        self.achats.setColumnHidden(4,franchise)
        self.achats.setHorizontalHeaderItem(3,QTableWidgetItem('Total TTC' if franchise else 'HT'))
        self.resume.clear();self.alertes.clear()
        if self.autorise(): self.lister()

    def lister(self):
        achats=self.service.achats();self.achats.setRowCount(len(achats))
        for r,a in enumerate(achats):
            valeurs=[a['id'],a['fournisseur'],a['reference'],money_text(sum(l['ttc' if self.regime.currentData()=='franchise' else 'ht'] for l in a['lignes'])),money_text(sum(l['tva'] for l in a['lignes'])),money_text(a['reste'])]
            for c,v in enumerate(valeurs):self.achats.setItem(r,c,QTableWidgetItem(str(v)))
    def calculer(self):
        s=self.service.calculer(iso(self.debut),iso(self.fin),self.regime.currentData(),0 if self.regime.currentData()=='franchise' else montant(self.credit.text()))
        self.resume.setText('TVA perçue : '+money_text(s['tva_percue'])+' • TVA exigible : '+money_text(s['tva_exigible'])+' • TVA déductible : '+money_text(s['tva_deductible'])+'\nÀ reverser : '+money_text(s['a_reverser'])+' • Crédit : '+money_text(s['credit']))
        if s['regime']=='franchise':self.resume.setText('Franchise en base · Montants TTC\nRecettes : '+money_text(s['recettes_ttc'])+' · Dépenses : '+money_text(s['depenses_ttc'])+' · Différence : '+money_text(s['solde_periode'])+'\nTVA non collectée et non déductible.')
        self.taux.setRowCount(len(s['taux']))
        for r,l in enumerate(s['taux']):
            for c,k in enumerate(['taux','base_exigible','tva_exigible','tva_percue','base_achats','tva_achats','tva_deductible']):self.taux.setItem(r,c,QTableWidgetItem(str(l[k]/100) if c==0 else money_text(l[k])))
        self.alertes.setText('\n'.join(s['alertes']) or ('Suivi TTC de la période.' if s['regime']=='franchise' else 'Calcul prêt à vérifier avant déclaration.'));self.lister()
    def ajouter(self):
        d=AchatDialog(self,franchise=self.regime.currentData()=="franchise")
        while d.exec()==QDialog.Accepted:
            try:a,m,j=d.donnees();self.service.ajouter_achat(a,m,j,operation_existante=d.operation.currentData());self.lister();break
            except Exception as e:QMessageBox.warning(d,'Dépense',str(e))
    def payer(self):
        r=self.achats.currentRow()
        if r<0:raise ValueError('Sélectionnez un fournisseur.')
        from qt_app import PaymentDialog
        ident=int(self.achats.item(r,0).text());d=PaymentDialog(parent=self);d.setWindowTitle('Règlement fournisseur')
        if d.exec()==QDialog.Accepted:
            j,m,mode,ref=d.values();self.service.payer_achat(ident,j,montant(m),mode,d.banque.currentData(),ref);self.lister()
    def qualifier(self):
        import gestion as g
        factures=[a for a in self.service.factures() if a['type']=='facture']
        choix={a['numero']:a for a in factures};nom,ok=QInputDialog.getItem(self,'TVA','Facture',list(choix),0,False)
        if not ok:return
        a=choix[nom];s=g.document(a['id'])['contenu'];d=QDialog(self);d.setWindowTitle('Exigibilité TVA • '+nom);f=QFormLayout(d);natures=[]
        for l in s['lignes']:
            w=combo([('Service • encaissements','service'),('Bien • livraison et acomptes','bien'),('Débits autorisés DICP','debits')]);f.addRow(l.get('designation','Ligne'),w);natures.append(w)
        livraison=calendrier();f.addRow('Livraison des biens',livraison);autorisation=QCheckBox('Je dispose de l’autorisation DICP pour les débits');f.addRow(autorisation);b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);f.addRow(b);b.accepted.connect(d.accept);b.rejected.connect(d.reject)
        if d.exec()==QDialog.Accepted:self.service.qualifier(a['id'],[w.currentData() for w in natures],iso(livraison) if any(w.currentData()=='bien' for w in natures) else '',autorisation.isChecked())
    def ajuster(self):
        d=QDialog(self);d.setWindowTitle('Régularisation TVA');f=QFormLayout(d);j=calendrier();m=QLineEdit('0');motif=QLineEdit();avoir=QLineEdit();f.addRow('Date',j);f.addRow('TVA signée (+ / −)',m);f.addRow('Motif / référence pièce',motif);f.addRow('ID avoir lié (facultatif)',avoir);b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);f.addRow(b);b.accepted.connect(d.accept);b.rejected.connect(d.reject)
        if d.exec()==QDialog.Accepted:
            from decimal import Decimal
            signe=-1 if Decimal(m.text().replace(',','.'))<0 else 1;val=montant(str(abs(Decimal(m.text().replace(',','.')))))
            self.service.ajuster(iso(j),signe*val,motif.text(),int(avoir.text()) if avoir.text().strip() else None)

class AdministratifPage(ProPage):
    def __init__(self,parent=None):
        super().__init__('Préparation administrative',parent,'administratif')
        f=QFormLayout();self.fiscal=combo([('À confirmer',''),('TPE','tpe'),('Impôt sur les transactions','it'),('Impôt sur les sociétés','is')]);self.dn=QLineEdit();f.addRow('Régime fiscal',self.fiscal);f.addRow('DN CPS',self.dn);self.layout.addLayout(f)
        self.actions_pro.append(bouton(self.layout,'Enregistrer le profil',lambda:self.executer(lambda:self.service.enregistrer_profil({'fiscal':self.fiscal.currentData(),'dn_cps':self.dn.text()}))))
        f=QFormLayout();self.genre=combo([('TVA • préparation 1010','tva1010'),('CPS • revenus RNS','cps_rns'),('Recettes / CA HT • IT','it'),('Démarche TPE','tpe'),('TVA • préparation 1040','tva1040')]);self.debut=calendrier(date.today().replace(month=1,day=1).isoformat());self.fin=calendrier();self.echeance=calendrier();self.source=QLineEdit(SOURCES['tva1010']);self.confirme=QCheckBox('J’ai vérifié cette échéance auprès de la DICP / CPS');self.regime=combo([('À confirmer',''),('Franchise en base','franchise'),('Assujetti TVA','reel')]);self.credit=QLineEdit('0')
        self.genre.currentIndexChanged.connect(lambda:self.source.setText(SOURCES[self.genre.currentData()]))
        for label,w in [('Document',self.genre),('Du',self.debut),('Au',self.fin),('Échéance officielle',self.echeance),('Source de l’échéance',self.source),('',self.confirme),('Régime TVA',self.regime),('Crédit TVA antérieur',self.credit)]:f.addRow(label,w)
        self.layout.addLayout(f);h=QHBoxLayout();self.actions_pro.append(bouton(h,'Préparer le dossier',lambda:self.executer(self.preparer)));self.actions_pro.append(bouton(h,'Exporter la préparation PDF',lambda:self.executer(self.exporter)));self.actions_pro.append(bouton(h,'Noter le dépôt / paiement',lambda:self.executer(self.suivre)));self.layout.addLayout(h)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['ID','Document','Période','Échéance','État']);self.layout.addWidget(self.table);self.rappels=QLabel();self.rappels.setWordWrap(True);self.layout.addWidget(self.rappels)
    def refresh(self):
        if not self.autorise():self.table.setRowCount(0);self.rappels.clear();return
        self.executer(self.lister)
    def lister(self):
        profil=self.service.profil();self.fiscal.setCurrentIndex(max(0,self.fiscal.findData(profil.get('fiscal',''))));self.dn.setText(profil.get('dn_cps',''))
        rows=self.service.declarations();self.table.setRowCount(len(rows))
        for r,a in enumerate(rows):
            for c,v in enumerate([a['id'],a['genre'],a['debut']+' → '+a['fin'],a['echeance'],a['statut']]):self.table.setItem(r,c,QTableWidgetItem(str(v)))
        self.rappels.setText('\n'.join(a['genre']+' • '+a['echeance']+' • '+('EN RETARD' if a['jours']<0 else str(a['jours'])+' jour(s)') for a in self.service.rappels()))
    def preparer(self):
        if not self.confirme.isChecked():raise ValueError('Confirmez la date officielle ; le logiciel ne présume pas votre périodicité.')
        self.service.preparer(self.genre.currentData(),iso(self.debut),iso(self.fin),iso(self.echeance),self.source.text(),self.regime.currentData(),montant(self.credit.text()));self.lister()
    def selection(self):
        r=self.table.currentRow()
        if r<0:raise ValueError('Sélectionnez un dossier.')
        ident=int(self.table.item(r,0).text());return next(a for a in self.service.declarations() if a['id']==ident)
    def exporter(self):
        from finances_pdf import exporter_preparation
        a=self.selection();p,_=QFileDialog.getSaveFileName(self,'Préparation administrative','Preparation-'+a['genre']+'.pdf','PDF (*.pdf)')
        if p:exporter_preparation(self.service,a['id'],p);QDesktopServices.openUrl(QUrl.fromLocalFile(p))
    def suivre(self):
        a=self.selection();statut,ok=QInputDialog.getItem(self,'Dossier','État',['depose','paye','a_verifier'],0,False)
        if not ok:return
        preuve,ok=QInputDialog.getText(self,'Dossier','Référence de preuve')
        if ok:self.service.suivre(a['id'],statut,preuve);self.lister()
