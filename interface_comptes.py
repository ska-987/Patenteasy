# SPDX-License-Identifier: GPL-3.0-or-later
"""Écrans courts pour comptes, apparence et sauvegardes."""
from localisation import tr
from pathlib import Path
from urllib.parse import urlencode
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (QApplication,QDialog,QDialogButtonBox,QFormLayout,QVBoxLayout,QHBoxLayout,
 QLabel,QLineEdit,QComboBox,QSpinBox,QPushButton,QFileDialog,QColorDialog,QMessageBox,QCheckBox,QTableWidget)
from qt_app import QComboBox,Page,button,configure_table,fill_table,selected_id,show_error,est_admin,exiger_admin

class SecretDialog(QDialog):
    def __init__(self,titre,parent=None,ancien=False):
        super().__init__(parent);self.setWindowTitle(titre);self.setMinimumWidth(450)
        v=QVBoxLayout(self);f=QFormLayout();self.identifiant=QLineEdit();self.secret=QLineEdit();self.confirmation=QLineEdit()
        self.secret.setEchoMode(QLineEdit.Password);self.confirmation.setEchoMode(QLineEdit.Password)
        f.addRow(tr('Mot de passe actuel') if ancien else tr('Identifiant'),self.identifiant)
        if ancien:self.identifiant.setEchoMode(QLineEdit.Password)
        f.addRow(tr('Nouveau mot de passe (12 caractères minimum)'),self.secret);f.addRow(tr('Confirmer'),self.confirmation);v.addLayout(f)
        b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);b.accepted.connect(self.valider);b.rejected.connect(self.reject);v.addWidget(b)
    def valider(self):
        if self.secret.text()!=self.confirmation.text():QMessageBox.warning(self,tr('Mot de passe'),tr('Les mots de passe sont différents.'));return
        if not 12<=len(self.secret.text())<=256:QMessageBox.warning(self,tr('Mot de passe'),tr('Utilisez au moins 12 caractères.'));return
        self.accept()

class ComptesPage(Page):
    def __init__(self,parent=None):
        super().__init__(tr('Administration'),tr('Comptes'),tr('Créez les accès locaux de votre équipe.'),parent)
        self.layout.addWidget(button(tr('Créer un utilisateur'),self.creer));self.layout.addWidget(button(tr('Activer / désactiver'),self.basculer,secondary=True))
        self.table=QTableWidget();configure_table(self.table,[tr('Identifiant'),tr('Rôle'),tr('Accès')]);self.layout.addWidget(self.table)
    def refresh(self):
        if not exiger_admin(self):return
        comptes=self.window().gestion_comptes.lister();fill_table(self.table,[[c['identifiant'],c['role'],tr('Actif') if c['actif'] else tr('Désactivé')] for c in comptes],[c['id'] for c in comptes])
    def creer(self):
        if not exiger_admin(self):return
        d=SecretDialog(tr('Créer un utilisateur'),self)
        if d.exec():
            try:self.window().gestion_comptes.creer_utilisateur(d.identifiant.text(),d.secret.text());self.refresh()
            except Exception as e:show_error(self,e)
    def basculer(self):
        if not exiger_admin(self):return
        ident=selected_id(self.table)
        if ident is None:return
        try:self.window().gestion_comptes.basculer_actif(ident);self.refresh()
        except Exception as e:show_error(self,e)

class PreferencesPage(Page):
    def __init__(self,parent=None):
        super().__init__(tr('Personnel'),tr('Mes préférences'),tr('Ces réglages concernent votre compte.'),parent)
        self.gestion=parent.gestion_comptes;p=self.gestion.preferences();f=QFormLayout()
        self.theme=QComboBox();self.theme.addItems(['Clair','Sombre','Personnalisé']);self.theme.setCurrentText(p.get('theme','Clair'))
        self.couleur=p.get('accent','#2563eb');self.accent=button(tr('Choisir une couleur'),self.choisir,secondary=True)
        self.delai=QSpinBox();self.delai.setRange(1,120);self.delai.setSuffix(' minutes');self.delai.setValue(p.get('verrouillage',15))
        f.addRow(tr('Apparence'),self.theme);f.addRow(tr('Couleur d’accent'),self.accent);f.addRow(tr('Verrouiller après inactivité'),self.delai);self.layout.addLayout(f)
        self.layout.addWidget(button(tr('Appliquer'),self.appliquer));self.layout.addWidget(button(tr('Changer mon mot de passe'),self.secret,secondary=True))
        self.layout.addWidget(button(tr('Verrouiller / se déconnecter'),parent.verrouiller,secondary=True))
        self.layout.addWidget(button(tr('Sauvegarder maintenant'),self.sauvegarder,secondary=True));self.etat=QLabel();self.etat.setWordWrap(True);self.layout.addWidget(self.etat)
        if est_admin(self):
            self.layout.addWidget(button(tr('Choisir le dossier des sauvegardes'),self.dossier,secondary=True))
            self.jours=QSpinBox();self.jours.setRange(1,90);self.semaines=QSpinBox();self.semaines.setRange(0,52)
            c=parent.sauvegardes.configuration();self.jours.setValue(c['jours']);self.semaines.setValue(c['semaines']);r=QFormLayout();r.addRow(tr('Jours conservés'),self.jours);r.addRow(tr('Semaines conservées'),self.semaines);self.layout.addLayout(r)
            self.layout.addWidget(button(tr('Enregistrer la conservation'),self.retenir,secondary=True))
            self.layout.addWidget(button(tr('Restaurer une sauvegarde'),self.restaurer,danger=True))
            self.layout.addWidget(button(tr('Journal des actions'),self.audit,secondary=True))
        self.layout.addStretch()
    def choisir(self):
        c=QColorDialog.getColor(QColor(self.couleur),self)
        if c.isValid():self.couleur=c.name()
    def appliquer(self):
        p=self.gestion.preferences();p.update(theme=self.theme.currentText(),accent=self.couleur,verrouillage=self.delai.value());self.gestion.enregistrer_preferences(p);self.window().appliquer_theme()
    def secret(self):
        d=SecretDialog(tr('Changer mon mot de passe'),self,ancien=True)
        if d.exec():
            try:self.gestion.changer_mot_de_passe(d.identifiant.text(),d.secret.text());QMessageBox.information(self,tr('Mot de passe'),tr('Mot de passe modifié.'))
            except Exception as e:show_error(self,e)
    def sauvegarder(self):
        try:p=self.window().sauvegardes.creer();self.window().rafraichir_sauvegarde();QMessageBox.information(self,tr('Sauvegarde'),tr('Sauvegarde chiffrée créée.'));self.refresh()
        except Exception as e:self.window().rafraichir_sauvegarde();show_error(self,e)
    def dossier(self):
        if not exiger_admin(self):return
        p=QFileDialog.getExistingDirectory(self,tr('Dossier de sauvegardes'))
        if p:
            try:self.window().sauvegardes.configurer(p,self.jours.value(),self.semaines.value());self.refresh()
            except Exception as e:show_error(self,e)
    def retenir(self):
        if not exiger_admin(self):return
        try:self.window().sauvegardes.configurer(self.window().sauvegardes.configuration()['dossier'],self.jours.value(),self.semaines.value());self.refresh()
        except Exception as e:show_error(self,e)
    def refresh(self):
        c=self.window().sauvegardes.configuration();texte='Dernière sauvegarde : '+c.get('derniere','aucune')
        if est_admin(self):texte+='\nDossier : '+(c['dossier'] or 'à choisir')
        self.etat.setText(texte)
    def audit(self):
        if not exiger_admin(self):return
        from datetime import datetime
        c=self.gestion.coffre.ouvrir()
        try:rows=c.execute('SELECT * FROM audit_local ORDER BY date DESC LIMIT 500').fetchall()
        finally:c.close()
        d=QDialog(self);d.setWindowTitle(tr('Journal local des actions'));d.resize(850,500);v=QVBoxLayout(d);t=QTableWidget();configure_table(t,[tr('Date'),tr('Compte'),tr('Action'),tr('Détail')])
        fill_table(t,[[datetime.fromtimestamp(x['date']).strftime('%d/%m/%Y %H:%M'),x['utilisateur'],x['action'],x['detail']] for x in rows]);v.addWidget(t)
        v.addWidget(button(tr('Fermer'),d.accept,secondary=True));d.exec()

    def restaurer(self):
        if not exiger_admin(self):return
        p,_=QFileDialog.getOpenFileName(self,tr('Restaurer une sauvegarde'),'','Patenteasy (*.pebackup)')
        if not p:return
        texte='Les données et comptes seront remis à la date de cette sauvegarde. Les anciens mots de passe et le code de récupération s’appliqueront. Une sauvegarde de l’état actuel sera créée. Patenteasy se fermera. Continuer ?'
        if QMessageBox.question(self,tr('Restaurer'),texte,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        try:self.window().sauvegardes.restaurer(p);QApplication.instance().quit()
        except Exception as e:show_error(self,e)

class ParticipationDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle('Aidez à améliorer Patenteasy');self.setMinimumWidth(480)
        v=QVBoxLayout(self);l=QLabel('Facultatif. Aucune donnée comptable ni client ne sera transmise. Le message sera ouvert dans votre messagerie pour que vous le vérifiiez et l’envoyiez.');l.setWordWrap(True);v.addWidget(l)
        f=QFormLayout();self.activite=QLineEdit();self.commune=QLineEdit();self.email=QLineEdit();self.besoin=QLineEdit();self.usage=QComboBox();self.usage.addItems([tr('Ordinateur'),tr('Téléphone'),tr('Les deux')]);self.equipe=QComboBox();self.equipe.addItems([tr('Seul'),tr('En équipe')])
        for titre,w in [(tr('Activité'),self.activite),(tr('Ville / région'),self.commune),(tr('Mail (facultatif)'),self.email),(tr('Usage'),self.usage),(tr('Organisation'),self.equipe),(tr('Fonction souhaitée'),self.besoin)]:f.addRow(titre,w)
        v.addLayout(f);self.stats=QCheckBox('J’accepte l’utilisation de ces réponses pour améliorer Patenteasy et établir des statistiques.');v.addWidget(self.stats)
        self.news=QCheckBox('Je souhaite recevoir les nouveautés des produits ska_987.');v.addWidget(self.news)
        notice=QLabel('Destinataire : ska_987, sav.centreprotech@proton.me. Réponses conservées 12 mois, puis statistiques regroupées. Vous pouvez demander leur suppression et retirer votre accord à cette adresse.');notice.setWordWrap(True);v.addWidget(notice)
        b=QDialogButtonBox();env=b.addButton(tr('Préparer le message'),QDialogButtonBox.AcceptRole);pas=b.addButton(tr('Passer'),QDialogButtonBox.RejectRole);env.clicked.connect(self.envoyer);pas.clicked.connect(self.reject);v.addWidget(b)
    def envoyer(self):
        if not self.stats.isChecked() and not self.news.isChecked():QMessageBox.information(self,tr('Votre choix'),'Choisissez un accord ou cliquez sur Passer.');return
        lignes=['Participation volontaire à Patenteasy 0.3.7']
        if self.stats.isChecked():
            lignes += ['Accord statistiques : oui','Activité : '+self.activite.text(),'Commune : '+self.commune.text(),'Usage : '+self.usage.currentText(),'Organisation : '+self.equipe.currentText(),'Souhait : '+self.besoin.text()]
        if self.news.isChecked():lignes+=['Accord nouveautés ska_987 : oui']
        lignes+=['Mail de contact : '+self.email.text()]
        url='mailto:sav.centreprotech@proton.me?'+urlencode({'subject':'Participation Patenteasy bêta 1','body':'\n'.join(lignes)})
        if QDesktopServices.openUrl(QUrl(url)):self.accept()
        else:QMessageBox.warning(self,'Messagerie','Aucune messagerie disponible. Vous pouvez contacter le support depuis Aide.')
