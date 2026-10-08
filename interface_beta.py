from localisation import tr
# SPDX-License-Identifier: GPL-3.0-or-later
"""Parcours de démarrage et annonces courts, sans création de données fictives."""
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QPushButton,QTextEdit,QHBoxLayout,QLineEdit
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from qt_app import Page,button,est_admin,selected_id,show_error
from beta_fonctions import NOUVEAUTES

class DemarragePage(Page):
    def __init__(self,parent=None):
        super().__init__(tr('Bienvenue'),tr('Bien démarrer'),tr('Quatre étapes, à votre rythme.'),parent)
        self.etat=QLabel();self.etat.setWordWrap(True);self.layout.addWidget(self.etat)
        for titre,key in [(tr('1 · Renseigner mon entreprise'),'entreprise'),(tr('2 · Choisir le dossier de sauvegarde'),'preferences'),(tr('3 · Ajouter mon premier client'),'clients'),(tr('4 · Préparer mon premier devis'),'devis')]:self.layout.addWidget(button(titre,lambda checked=False,k=key:self.navigate.emit(k)))
        self.layout.addWidget(button(tr('Passer et ouvrir le tableau de bord'),lambda:self.navigate.emit('dashboard'),secondary=True));self.layout.addStretch()
    def refresh(self):
        import database as db
        self.etat.setText('\n'.join((tr('✓ Entreprise renseignée') if (db.obtenir_entreprise() or {}).get('nom') else tr('○ Entreprise à renseigner'),tr('✓ Dossier de sauvegarde choisi') if self.window().sauvegardes.configuration().get('dossier') else tr('○ Sauvegarde à configurer'),tr('✓ Premier client ajouté') if db.lister_clients() else tr('○ Premier client à ajouter'),tr('✓ Premier devis préparé') if db.lister_devis() else tr('○ Premier devis à préparer'))))

def nouveautes(parent):
    d=QDialog(parent);d.setWindowTitle(tr('Patenteasy — nouveautés'));v=QVBoxLayout(d);label=QLabel('\n\n'.join('• '+x for x in NOUVEAUTES));label.setWordWrap(True);v.addWidget(label);v.addWidget(button(tr('Continuer'),d.accept));d.exec()

def relancer(parent,identifiant):
    try:
        email,corps,lien=parent.window().beta.relance(identifiant)
        d=QDialog(parent);d.setWindowTitle(tr('Préparer une relance'));d.resize(560,420);v=QVBoxLayout(d);v.addWidget(QLabel(tr('Adresse mail du client')));destination=QLineEdit(email);v.addWidget(destination);texte=QTextEdit();texte.setPlainText(corps);texte.setReadOnly(True);v.addWidget(texte)
        v.addWidget(QLabel(tr('Vérifiez ce texte. Votre messagerie s’ouvrira ; aucun mail ne sera envoyé automatiquement.')))
        def ouvrir():
            from urllib.parse import urlencode
            adresse=destination.text().strip()
            import re
            if not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',adresse):
                show_error(d,ValueError(tr('Saisissez une adresse mail valide.')));return
            QDesktopServices.openUrl(QUrl('mailto:'+adresse+'?'+urlencode({'subject':'Rappel de facture','body':corps})));d.accept()
        v.addWidget(button(tr('Ouvrir ma messagerie'),ouvrir));v.addWidget(button(tr('Annuler'),d.reject,secondary=True));d.exec()
    except Exception as e:show_error(parent,e)
