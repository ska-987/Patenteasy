# SPDX-License-Identifier: GPL-3.0-or-later
"""Récupération explicite d'une sauvegarde sur un espace neuf."""
from localisation import tr
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QComboBox, QLabel, QFileDialog, QHBoxLayout
from qt_app import FormDialog, button, show_error
from sauvegarde_portable import preparer, verifier, MAGIC


class RecuperationDialog(FormDialog):
    def __init__(self, comptes, parent=None):
        super().__init__(tr('Retrouver votre activité'),parent)
        self.comptes=comptes;self.compte=None;self.preparation=None
        self.file=QLineEdit();self.file.setReadOnly(True)
        row=QHBoxLayout();row.addWidget(self.file);row.addWidget(button(tr('Choisir une sauvegarde'),self.choisir,secondary=True));self.form.addRow(tr('Sauvegarde Patenteasy'),row)
        self.old=QLineEdit();self.old.setReadOnly(True);self.old_button=button(tr('Choisir acces.json'),self.choisir_acces,secondary=True)
        self.old_label=QLabel(tr('Ancien format : fichier d’accès de l’ancien PC'))
        oldrow=QHBoxLayout();oldrow.addWidget(self.old);oldrow.addWidget(self.old_button);self.form.addRow(self.old_label,oldrow)
        self.mode=QComboBox();self.mode.addItem(tr('Mot de passe administrateur'),'mot_de_passe');self.mode.addItem(tr('Code de récupération'),'code');self.form.addRow(tr(tr('Accès à la sauvegarde')),self.mode)
        self.ident=QLineEdit();self.ident.setPlaceholderText(tr('Facultatif si un seul administrateur'));self.form.addRow(tr('Identifiant administrateur'),self.ident)
        self.secret=QLineEdit();self.secret.setEchoMode(QLineEdit.Password);self.form.addRow(tr('Mot de passe ou code'),self.secret)
        self.new=QLineEdit();self.new.setEchoMode(QLineEdit.Password);self.new.setPlaceholderText(tr('Au moins 12 caractères'));self.new_label=QLabel(tr(tr('Nouveau mot de passe')));self.form.addRow(self.new_label,self.new)
        self.confirm=QLineEdit();self.confirm.setEchoMode(QLineEdit.Password);self.confirm_label=QLabel(tr('Confirmer'));self.form.addRow(self.confirm_label,self.confirm)
        self.check=button(tr('Vérifier la sauvegarde'),self.verifier);self.form.addRow(self.check)
        self.review=QLabel();self.review.setWordWrap(True);self.form.addRow(self.review)
        self.buttons.accepted.disconnect();self.buttons.accepted.connect(self.restaurer)
        self.buttons.button(self.buttons.StandardButton.Ok).setText(tr('Restaurer sur ce PC'));self.buttons.button(self.buttons.StandardButton.Ok).setEnabled(False)
        self.mode.currentIndexChanged.connect(self.invalidate)
        for entry in (self.secret,self.ident,self.new,self.confirm):entry.textChanged.connect(self.invalidate)
        self.old_label.hide();self.old.hide();self.old_button.hide();self.invalidate()

    def invalidate(self,*_):
        self.preparation=None;self.review.clear();self.buttons.button(self.buttons.StandardButton.Ok).setEnabled(False)
        code=self.mode.currentData()=='code'
        for widget in (self.new,self.new_label,self.confirm,self.confirm_label):widget.setVisible(code)

    def choisir(self):
        name,_=QFileDialog.getOpenFileName(self,tr('Choisir une sauvegarde'),'','Patenteasy (*.pebackup)')
        if not name:return
        self.file.setText(name);self.old.clear();self.invalidate()
        with Path(name).open('rb') as f:portable=f.read(len(MAGIC))==MAGIC
        for w in (self.old_label,self.old,self.old_button):w.setVisible(not portable)

    def choisir_acces(self):
        name,_=QFileDialog.getOpenFileName(self,tr('Fichier d’accès de l’ancien PC'),'','JSON (*.json)')
        if name:self.old.setText(name);self.invalidate()

    def verifier(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.preparation=preparer(self.file.text(),self.secret.text(),self.mode.currentData(),self.ident.text(),self.old.text() or None)
            if self.mode.currentData()=='code':
                self.comptes.valider_mot_de_passe(self.new.text())
                if self.new.text()!=self.confirm.text():raise ValueError(tr('Les deux mots de passe sont différents.'))
            resume=verifier(self.preparation,self.comptes.base.chemin.parent)
            self.review.setText(f"Sauvegarde vérifiée : {resume['entreprise']}\n{resume['clients']} clients · {resume['devis']} devis · {resume['factures']} factures\nLes comptes et les réglages seront récupérés.")
            self.buttons.button(self.buttons.StandardButton.Ok).setEnabled(True)
        except Exception as exc:self.preparation=None;show_error(self,exc)
        finally:QApplication.restoreOverrideCursor()

    def restaurer(self):
        if self.preparation is None:return
        try:
            code=self.mode.currentData()=='code'
            self.compte=self.comptes.restaurer_nouveau_pc(self.preparation,self.new.text() if code else None,self.secret.text() if code else None)
            self.secret.clear();self.new.clear();self.confirm.clear();self.accept()
        except Exception as exc:show_error(self,exc)
