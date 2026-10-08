# SPDX-License-Identifier: GPL-3.0-or-later
"""Lecture native en mémoire : aucun PDF temporaire à supprimer sous Windows."""
from PySide6.QtCore import QBuffer, QIODevice, QCoreApplication, QEvent
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton


def ouvrir(parent, contenu, nom):
    from localisation import tr
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr('Aperçu du document')); dialog.resize(900, 700)
    layout = QVBoxLayout(dialog)
    buffer = QBuffer(dialog); buffer.setData(contenu); buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    document = QPdfDocument(dialog)
    view = None
    try:
        document.load(buffer)
        if document.status() != QPdfDocument.Status.Ready:
            raise ValueError('Le document PDF ne peut pas être ouvert.')
        view = QPdfView(dialog)
        view.setDocument(document)
        view.setPageMode(QPdfView.PageMode.MultiPage)
        view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        layout.addWidget(view)
        actions = QHBoxLayout()
        save = QPushButton(tr('Enregistrer le PDF')); close = QPushButton(tr('Fermer'))
        actions.addWidget(save); actions.addStretch(); actions.addWidget(close)
        layout.addLayout(actions)
        def enregistrer():
            from exports_pdf import enregistrer as exporter
            from qt_app import show_error, show_info
            try:
                destination = exporter(dialog, contenu, nom)
                if destination: show_info(dialog, f"PDF enregistré :\n{destination}")
            except Exception as exc:
                show_error(dialog, exc)
        save.clicked.connect(enregistrer); close.clicked.connect(dialog.accept)
        dialog.exec()
    finally:
        if view is not None:
            view.deleteLater()
            QCoreApplication.sendPostedEvents(view, QEvent.Type.DeferredDelete)
        document.close()
        buffer.close()
        dialog.deleteLater()
