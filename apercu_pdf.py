# SPDX-License-Identifier: GPL-3.0-or-later
"""Lecture native d'un document PDF, sans navigateur ni serveur."""
from pathlib import Path
import tempfile
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog


def ouvrir(parent, contenu, nom):
    from localisation import tr
    with tempfile.TemporaryDirectory(prefix='patenteasy-pdf-') as folder:
        path=Path(folder)/'apercu.pdf';path.write_bytes(contenu)
        dialog=QDialog(parent);dialog.setWindowTitle(tr('Aperçu du document'));dialog.resize(900,700)
        layout=QVBoxLayout(dialog);document=QPdfDocument(dialog)
        if document.load(str(path)) != QPdfDocument.Error.None_:raise ValueError('Le document PDF ne peut pas être ouvert.')
        view=QPdfView(dialog);view.setDocument(document);view.setPageMode(QPdfView.PageMode.MultiPage);view.setZoomMode(QPdfView.ZoomMode.FitToWidth);layout.addWidget(view)
        actions=QHBoxLayout();save=QPushButton(tr('Enregistrer le PDF'));close=QPushButton(tr('Fermer'));actions.addWidget(save);actions.addStretch();actions.addWidget(close);layout.addLayout(actions)
        def enregistrer():
            destination,_=QFileDialog.getSaveFileName(dialog,tr('Enregistrer le PDF'),nom,'PDF (*.pdf)')
            if destination:Path(destination).write_bytes(contenu)
        save.clicked.connect(enregistrer);close.clicked.connect(dialog.accept)
        try:dialog.exec()
        finally:document.close();dialog.deleteLater()
