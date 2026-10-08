# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ska_987
"""Interface de bureau Qt native de Patenteasy.

Aucun navigateur embarqué, WebView ou serveur HTTP n'est utilisé. Les widgets
PySide6 appellent directement la couche métier SQLite existante.
"""
from __future__ import annotations
from localisation import tr

import os
import subprocess
import csv
import io
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from threading import Thread

from PySide6.QtCore import QDate, Qt, QUrl, Signal, QSettings, QTimer, QObject, QEvent, QLocale
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QCalendarWidget,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import regional
import database as db
import gestion as g
from editeur import editeur
from mises_a_jour import telecharger as telecharger_mise_a_jour
from mises_a_jour import verifier as verifier_mise_a_jour
from pdf_documents import generer, monnaie
from version import VERSION
from comptes import GestionComptes

# La valeur métier des listes reste stable quelle que soit la langue affichée.
_BaseComboBox=QComboBox
class QComboBox(_BaseComboBox):
    def addItem(self,text,userData=None):
        super().addItem(text if isinstance(userData,int) else tr(text),userData)
    def addItems(self,texts):
        for text in texts:self.addItem(text)
    def currentText(self):
        from localisation import original
        return original(super().currentText())
    def setCurrentText(self,text):super().setCurrentText(tr(text))

ROOT = Path(__file__).resolve().parent
MOIS = [
    tr("Janvier"), tr("Février"), tr("Mars"), tr("Avril"), tr("Mai"), tr("Juin"),
    tr("Juillet"), tr("Août"), tr("Septembre"), tr("Octobre"), tr("Novembre"), tr("Décembre"),
]

APP_QSS = r"""
QWidget {
    background: #f4f6f9;
    color: #182336;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}
QMainWindow { background: #f4f6f9; }
QFrame#sidebar {
    background: #172536;
    border: none;
}
QLabel#brand {
    background: transparent;
    color: white;
    font-size: 21pt;
    font-weight: 700;
}
QLabel#tagline, QLabel#sidebarFoot {
    background: transparent;
    color: #9aabbe;
}
QListWidget#navigation {
    background: transparent;
    border: none;
    outline: none;
    color: #c8d2df;
}
QListWidget#navigation::item {
    padding: 9px 11px;
    border-radius: 7px;
    margin: 1px 0px;
}
QListWidget#navigation::item:selected,
QListWidget#navigation::item:hover {
    background: #2b4059;
    color: white;
}
QFrame#topbar {
    background: white;
    border: none;
    border-bottom: 1px solid #dce3ed;
}
QLabel#topbarText { background: transparent; color: #65748a; }
QScrollArea { border: none; background: #f4f6f9; }
QScrollArea > QWidget > QWidget { background: #f4f6f9; }
QLabel#eyebrow { color: #65748a; font-size: 8.5pt; font-weight: 650; }
QLabel#title { font-size: 23pt; font-weight: 700; }
QLabel#lead { color: #65748a; font-size: 11pt; }
QLabel#muted { color: #65748a; }
QFrame#card, QGroupBox {
    background: white;
    border: 1px solid #dce3ed;
    border-radius: 10px;
}
QGroupBox {
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
    font-weight: 650;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
    background: #f4f6f9;
}
QLabel[class="metricValue"] { font-size: 18pt; font-weight: 700; }
QLabel[class="metricCaption"] { color: #65748a; font-size: 9pt; }
QPushButton {
    background: #285b9b;
    color: white;
    border: none;
    border-radius: 7px;
    padding: 8px 14px;
    min-height: 20px;
}
QPushButton:hover { background: #1c477e; }
QPushButton[secondary="true"] { background: #eaf0f7; color: #254568; }
QPushButton[secondary="true"]:hover { background: #dce7f2; }
QPushButton[danger="true"] { background: #a43d3d; color: white; }
QPushButton[danger="true"]:hover { background: #863232; }
QPushButton:disabled { background: #cbd5e1; color: #6b7280; }
QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox {
    background: white;
    border: 1px solid #bbc7d6;
    border-radius: 6px;
    padding: 7px 9px;
    selection-background-color: #9cbcdf;
    selection-color: #182336;
}
QTextEdit { min-height: 72px; }
QTableWidget {
    background: white;
    alternate-background-color: #fafbfd;
    border: 1px solid #dce3ed;
    border-radius: 8px;
    gridline-color: #dce3ed;
    selection-background-color: #dce8f5;
    selection-color: #182336;
}
QTableWidget::item:selected {
    background: #dce8f5;
    color: #182336;
}
QHeaderView::section {
    background: #edf2f7;
    color: #4c5d73;
    border: none;
    border-right: 1px solid #dce3ed;
    border-bottom: 1px solid #dce3ed;
    padding: 8px;
    font-size: 9pt;
    font-weight: 650;
}
QTabWidget::pane { border: 1px solid #dce3ed; background: white; border-radius: 8px; }
QTabBar::tab { background: #eaf0f7; color: #254568; padding: 8px 13px; margin-right: 2px; }
QTabBar::tab:selected { background: #285b9b; color: white; }
QMessageBox { background: #f4f6f9; }
"""


def fcfp(centimes: int | None) -> str:
    return regional.montant(centimes)


def decimal_text(centimes: int | None) -> str:
    if centimes is None:
        return ""
    return regional.nombre(int(centimes), langue=regional.configuration()["langue"], groupe=False)


def money_text(value):
    return regional.montant(value, unite=False, saisie=True)


def qdate_from_iso(value: str | None, fallback_today: bool = True) -> QDate:
    if value:
        parsed = QDate.fromString(value, Qt.DateFormat.ISODate)
        if parsed.isValid():
            return parsed
    return QDate.currentDate() if fallback_today else QDate(2000, 1, 1)


class DateInput(QWidget):
    """Six chiffres, séparateurs automatiques et calendrier facultatif."""
    def __init__(self, value=None, *, optional=False):
        super().__init__()
        self.optional = optional
        self._original = QDate()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.entry = QLineEdit()
        self.format = regional.configuration()['format_date']
        self.entry.setInputMask("0000-00-00;_" if self.format == 'yyyy-MM-dd' else "00/00/00;_")
        self.entry.setToolTip(regional.FORMATS[self.format])
        self.setFocusProxy(self.entry)
        self.calendar_button = QPushButton(tr("Calendrier"))
        self.calendar_button.setToolTip(tr("Choisir une date dans le calendrier"))
        self.calendar_button.clicked.connect(self.open_calendar)
        layout.addWidget(self.entry, 1)
        layout.addWidget(self.calendar_button)
        if value or not optional:
            self.setDate(qdate_from_iso(value))

    def setDate(self, value):
        if not value.isValid():
            raise ValueError(tr("Date invalide."))
        self._original = value
        self.entry.setText(value.toString(self.format))

    def clear(self):
        self._original = QDate()
        self.entry.clear()

    def date(self):
        digits = ''.join(c for c in self.entry.text() if c.isdigit())
        if not digits and self.optional:
            return QDate()
        attendu = 8 if self.format == 'yyyy-MM-dd' else 6
        if len(digits) != attendu:
            raise ValueError("Complétez la date au format " + regional.FORMATS[self.format] + ".")
        if self._original.isValid() and self.entry.text() == self._original.toString(self.format):
            return self._original
        if self.format == 'yyyy-MM-dd':
            result = QDate(int(digits[:4]), int(digits[4:6]), int(digits[6:]))
        elif self.format == 'MM/dd/yy':
            result = QDate(2000 + int(digits[4:]), int(digits[:2]), int(digits[2:4]))
        else:
            result = QDate(2000 + int(digits[4:]), int(digits[2:4]), int(digits[:2]))
        if not result.isValid():
            raise ValueError("Cette date n’existe pas. Utilisez " + regional.FORMATS[self.format] + ".")
        return result

    def open_calendar(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Choisir une date"))
        layout = QVBoxLayout(dialog)
        calendar = QCalendarWidget()
        calendar.setGridVisible(True)
        try:
            selected = self.date()
        except ValueError:
            selected = QDate.currentDate()
        calendar.setSelectedDate(selected if selected.isValid() else QDate.currentDate())
        layout.addWidget(calendar)
        controls = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        controls.accepted.connect(dialog.accept)
        controls.rejected.connect(dialog.reject)
        calendar.activated.connect(lambda _: dialog.accept())
        layout.addWidget(controls)
        if dialog.exec() == QDialog.Accepted:
            self.setDate(calendar.selectedDate())


def make_date(value: str | None = None) -> DateInput:
    return DateInput(value)


def iso_date(widget: DateInput) -> str:
    return widget.date().toString(Qt.DateFormat.ISODate)


def button(text: str, slot=None, *, secondary=False, danger=False) -> QPushButton:
    b = QPushButton(tr(text))
    if secondary:
        b.setProperty("secondary", True)
    if danger:
        b.setProperty("danger", True)
    if slot:
        b.clicked.connect(slot)
    return b


class DateTableItem(QTableWidgetItem):
    def __lt__(self, other):
        a, b = self.data(Qt.UserRole + 1), other.data(Qt.UserRole + 1)
        return a < b if a and b else super().__lt__(other)


class TableInteraction(QObject):
    """Désélection sans laisser de ligne courante utilisable par les actions."""
    def eventFilter(self, obj, event):
        if event.type() not in (QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress, QEvent.Type.Wheel):
            return False
        table = self.parent()
        if event.type() == QEvent.Type.Wheel:
            if event.modifiers() != Qt.NoModifier:
                return False
            delta = event.pixelDelta().y() or event.angleDelta().y()
            bar = table.verticalScrollBar()
            at_edge = (delta > 0 and bar.value() == bar.minimum()) or (delta < 0 and bar.value() == bar.maximum())
            if not at_edge:
                return False
            ancestor = table.parentWidget()
            while ancestor is not None:
                if isinstance(ancestor, QScrollArea):
                    outer = ancestor.verticalScrollBar()
                    movement = event.pixelDelta().y() or round(event.angleDelta().y() / 120 * QApplication.wheelScrollLines() * outer.singleStep())
                    previous = outer.value()
                    outer.setValue(previous - movement)
                    if outer.value() != previous:
                        event.accept()
                        return True
                ancestor = ancestor.parentWidget()
            return False
        clear = (event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape)
        if obj is table.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            clear = not table.indexAt(event.position().toPoint()).isValid()
        if clear:
            table.clearSelection()
            table.setCurrentCell(-1, -1)
            return True
        return False


def configure_table(table: QTableWidget, headers: list[str], stretch_last=True):
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels([tr(h) for h in headers])
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setMinimumHeight(180)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table._interaction = TableInteraction(table)
    table.installEventFilter(table._interaction)
    table.viewport().installEventFilter(table._interaction)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if stretch_last and headers:
        table.horizontalHeader().setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeMode.Stretch)


def fill_table(table: QTableWidget, rows: list[list[object]], ids: list[int] | None = None):
    table.setSortingEnabled(False)
    table.setRowCount(len(rows))
    for r, values in enumerate(rows):
        for c, value in enumerate(values):
            texte = "" if value is None else str(value)
            import re
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', texte):
                item = DateTableItem(regional.afficher_date(texte))
                item.setData(Qt.UserRole + 1, texte)
            else: item = QTableWidgetItem(texte)
            if c == 0 and ids is not None:
                item.setData(Qt.ItemDataRole.UserRole, ids[r])
            table.setItem(r, c, item)
    table.setSortingEnabled(True)


def selected_id(table: QTableWidget) -> int | None:
    if not table.selectionModel().hasSelection():
        return None
    row = table.currentRow()
    if row < 0:
        return None
    item = table.item(row, 0)
    return item.data(Qt.ItemDataRole.UserRole) if item and item.data(Qt.ItemDataRole.UserRole) is not None else None


def show_error(parent, exc: BaseException):
    QMessageBox.critical(parent, "Patenteasy", tr(str(exc)))


def show_info(parent, text: str):
    QMessageBox.information(parent, "Patenteasy", tr(text))


def confirm(parent, text: str) -> bool:
    return QMessageBox.question(parent, "Patenteasy", text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes


def save_pdf(parent, contents: bytes, suggested: str):
    from exports_pdf import enregistrer
    path = enregistrer(parent, contents, suggested)
    if path:
        show_info(parent, f"PDF enregistré :\n{path}")
    return path


def open_pdf_folder(parent):
    try:
        from exports_pdf import ouvrir_dossier
        ouvrir_dossier(parent)
    except Exception as exc:
        show_error(parent, exc)


def backup_database(parent):
    fenetre = parent.window()
    try:
        fichier = fenetre.sauvegardes.creer()
        show_info(parent, tr("Sauvegarde chiffrée créée."))
        return fichier
    except Exception as exc:
        show_error(parent, exc)
        return None


def export_journal_csv(parent) -> Path | None:
    if not exiger_admin(parent): return None
    suggested = f"journal-{g.aujourd_hui().year}.csv"
    path, _ = QFileDialog.getSaveFileName(parent, tr("Exporter le journal"), suggested, "CSV (*.csv)")
    if not path:
        return None
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([tr("Date"), tr("Libellé"), tr("Type"), "Montant " + regional.configuration()["devise"]])
    for op in db.lister_operations(g.aujourd_hui().year):
        writer.writerow([op["date_operation"], op["libelle"], op["type_operation"], money_text(op["montant_centiemes"])])
    Path(path).write_text("\ufeff" + output.getvalue(), encoding="utf-8")
    show_info(parent, f"Journal exporté :\n{path}")
    return Path(path)


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setProperty("class", "card")


class MetricCard(Card):
    def __init__(self, caption: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 15, 18, 15)
        self.caption = QLabel(caption)
        self.caption.setProperty("class", "metricCaption")
        self.value = QLabel("—")
        self.value.setProperty("class", "metricValue")
        layout.addWidget(self.caption)
        layout.addWidget(self.value)


class Page(QWidget):
    navigate = Signal(str)

    def __init__(self, eyebrow: str, title: str, lead: str = "", parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        outer.addWidget(self.scroll)
        self.body = QWidget()
        self.scroll.setWidget(self.body)
        self.layout = QVBoxLayout(self.body)
        self.layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.layout.setContentsMargins(32, 26, 32, 40)
        self.layout.setSpacing(14)
        eye = QLabel(tr(eyebrow).upper())
        eye.setObjectName("eyebrow")
        heading = QLabel(tr(title))
        heading.setObjectName("title")
        self.layout.addWidget(eye)
        self.heading_row = QHBoxLayout()
        self.heading_row.addWidget(heading)
        self.heading_row.addStretch()
        self.layout.addLayout(self.heading_row)
        if lead:
            l = QLabel(tr(lead))
            l.setObjectName("lead")
            l.setWordWrap(True)
            self.layout.addWidget(l)

    def refresh(self):
        pass


class FormDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr(title))
        self.setMinimumWidth(520)
        self.root = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        body = QWidget()
        self.scroll.setWidget(body)
        self.form = QFormLayout(body)
        self.form.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.root.addWidget(self.scroll)
        self.resize(560, 480)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.root.addWidget(self.buttons)


class ClientDialog(FormDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(tr("Client"), parent)
        data = data or {}
        self.nom = QLineEdit(data.get("nom", ""))
        self.tel = QLineEdit(data.get("telephone", ""))
        self.email = QLineEdit(data.get("email", ""))
        self.adresse = QTextEdit(data.get("adresse", ""))
        self.form.addRow(tr("Nom *"), self.nom)
        self.form.addRow(tr("Téléphone"), self.tel)
        self.form.addRow(tr("Adresse e-mail"), self.email)
        self.form.addRow(tr("Adresse"), self.adresse)

    def values(self):
        return self.nom.text(), self.tel.text(), self.email.text(), self.adresse.toPlainText()


class ArticleDialog(FormDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(tr("Article / prestation"), parent)
        data = data or {}
        self.reference = QLineEdit(data.get("reference", ""))
        self.designation = QLineEdit(data.get("designation", ""))
        self.type_article = QComboBox()
        self.type_article.addItem(tr("Produit"), "produit")
        self.type_article.addItem(tr("Prestation"), "service")
        self.type_article.setCurrentIndex(max(0, self.type_article.findData(data.get("type_article", "produit"))))
        self.unite = QLineEdit(data.get("unite", "pièce"))
        self.achat = QLineEdit(money_text(data.get("prix_achat_centiemes", 0)))
        self.vente = QLineEdit(money_text(data.get("prix_vente_centiemes", 0)))
        self.taxe = QLineEdit(decimal_text(data.get("taxe_centiemes", 0)))
        self.form.addRow(tr("Référence *"), self.reference)
        self.form.addRow(tr("Désignation *"), self.designation)
        self.form.addRow(tr("Type"), self.type_article)
        self.form.addRow(tr("Unité"), self.unite)
        self.form.addRow(tr("Prix d’achat · " + regional.configuration()["devise"] + ""), self.achat)
        self.form.addRow(tr("Prix de vente HT · " + regional.configuration()["devise"] + ""), self.vente)
        self.form.addRow(tr("Taxe à la vente · %"), self.taxe)

    def values(self):
        return (
            self.reference.text(), self.designation.text(), self.type_article.currentData(), self.unite.text(),
            self.achat.text(), self.vente.text(), self.taxe.text(),
        )


class OperationDialog(FormDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(tr("Opération"), parent)
        data = data or {}
        self.date = make_date(data.get("date_operation"))
        self.libelle = QLineEdit(data.get("libelle", ""))
        self.type = QComboBox()
        self.type.addItem(tr("Recette"), "recette")
        self.type.addItem(tr("Dépense"), "depense")
        self.type.setCurrentIndex(max(0, self.type.findData(data.get("type_operation", "recette"))))
        self.montant = QLineEdit(money_text(data.get("montant_centiemes")))
        self.form.addRow(tr("Date"), self.date)
        self.form.addRow(tr("Libellé"), self.libelle)
        self.form.addRow(tr("Type"), self.type)
        self.form.addRow(tr("Montant · " + regional.configuration()["devise"] + ""), self.montant)

    def values(self):
        return iso_date(self.date), self.libelle.text(), self.type.currentData(), self.montant.text()


class QuoteCreateDialog(FormDialog):
    def __init__(self, parent=None):
        super().__init__(tr("Nouveau devis"), parent)
        self.client = QComboBox()
        for item in db.lister_clients():
            self.client.addItem(item["nom"], item["id"])
        self.date = make_date(g.aujourd_hui().isoformat())
        self.objet = QLineEdit()
        self.form.addRow(tr("Client"), self.client)
        self.form.addRow(tr("Date"), self.date)
        self.form.addRow(tr("Objet"), self.objet)

    def values(self):
        return self.client.currentData(), iso_date(self.date), self.objet.text()


class QuoteLineDialog(FormDialog):
    def __init__(self, data=None, allow_catalog=True, parent=None):
        super().__init__(tr("Ligne de devis"), parent)
        data = data or {}
        self.reference = QLineEdit(data.get("reference", ""))
        self.designation = QLineEdit(data.get("designation", ""))
        self.unite = QLineEdit(data.get("unite", "pièce"))
        self.quantite = QLineEdit(decimal_text(data.get("quantite_centiemes", 100)) or "1")
        self.prix = QLineEdit(money_text(data.get("prix_unitaire_centiemes", 0)))
        self.taxe = QLineEdit(decimal_text(data.get("taxe_centiemes", 0)))
        self.catalogue = QCheckBox(tr("Enregistrer aussi dans le catalogue"))
        self.catalogue.setVisible(allow_catalog)
        self.type = QComboBox()
        self.type.addItem(tr("Produit"), "produit")
        self.type.addItem(tr("Prestation"), "service")
        self.type.setVisible(allow_catalog)
        self.form.addRow(tr("Référence"), self.reference)
        self.form.addRow(tr("Désignation *"), self.designation)
        self.form.addRow(tr("Unité *"), self.unite)
        self.form.addRow("Quantité *", self.quantite)
        self.form.addRow(tr("Prix unitaire HT · " + regional.configuration()["devise"] + ""), self.prix)
        self.form.addRow(tr("Taxe · %"), self.taxe)
        if allow_catalog:
            self.form.addRow("", self.catalogue)
            self.form.addRow(tr("Type catalogue"), self.type)

    def values(self):
        return (
            self.designation.text(), self.unite.text(), self.quantite.text(), self.prix.text(), self.taxe.text(),
            self.reference.text(), self.catalogue.isChecked(), self.type.currentData(),
        )


class CatalogLineDialog(FormDialog):
    def __init__(self, parent=None):
        super().__init__(tr("Ajouter depuis le catalogue"), parent)
        self.article = QComboBox()
        self.articles = db.lister_articles()
        for a in self.articles:
            self.article.addItem(f'{a["reference"]} — {a["designation"]} · {fcfp(a["prix_vente_centiemes"])} HT', a["id"])
        self.quantite = QLineEdit("1")
        self.form.addRow(tr("Catalogue"), self.article)
        self.form.addRow(tr("Quantité"), self.quantite)

    def values(self):
        aid = self.article.currentData()
        article = next((x for x in self.articles if x["id"] == aid), None)
        return article, self.quantite.text()


class PaymentDialog(FormDialog):
    def __init__(self, refund=False, parent=None):
        super().__init__(tr("Remboursement") if refund else tr("Paiement reçu"), parent)
        self.date = make_date(g.aujourd_hui().isoformat())
        self.amount = QLineEdit()
        self.mode = QComboBox()
        for text, key in [(tr("Virement"), "virement"), (tr("Carte"), "carte"), (tr("Espèces"), "especes"), (tr("Chèque"), "cheque"), (tr("Autre"), "autre")]:
            self.mode.addItem(text, key)
        self.reference = QLineEdit()
        self.reference.setVisible(not refund)
        self.form.addRow(tr("Date"), self.date)
        self.form.addRow(tr("Montant · " + regional.configuration()["devise"] + ""), self.amount)
        self.form.addRow(tr("Moyen"), self.mode)
        if not refund:
            self.form.addRow(tr("Référence"), self.reference)

    def values(self):
        return iso_date(self.date), self.amount.text(), self.mode.currentData(), self.reference.text()


class CreditDialog(QDialog):
    def __init__(self, document, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Émettre un avoir"))
        self.setMinimumWidth(600)
        outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        body = QWidget()
        root = QVBoxLayout(body)
        root.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll)
        intro = QLabel(tr("Indiquez les quantités à créditer. Laissez 0 pour une ligne non concernée."))
        intro.setWordWrap(True)
        root.addWidget(intro)
        self.fields = {}
        form = QFormLayout()
        for line in document["contenu"]["lignes"]:
            field = QLineEdit("0")
            form.addRow(f'{line["designation"]} · facturé {decimal_text(line["quantite_centiemes"])}', field)
            self.fields[str(line["id"])] = field
        root.addLayout(form)
        self.motif = QTextEdit()
        root.addWidget(QLabel(tr("Motif de correction")))
        root.addWidget(self.motif)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self):
        return self.motif.toPlainText(), {key: field.text() for key, field in self.fields.items()}


class StockDialog(FormDialog):
    def __init__(self, parent=None):
        super().__init__(tr("Mouvement de stock"), parent)
        self.article = QComboBox()
        for a in g.stock():
            self.article.addItem(f'{a["reference"]} — {a["designation"]}', a["id"])
        self.date = make_date(g.aujourd_hui().isoformat())
        self.quantity = QLineEdit("1")
        self.direction = QComboBox()
        self.direction.addItem(tr("Entrée"), "entree")
        self.direction.addItem(tr("Sortie"), "sortie")
        self.reason = QLineEdit()
        self.form.addRow(tr("Produit"), self.article)
        self.form.addRow(tr("Date"), self.date)
        self.form.addRow(tr("Quantité"), self.quantity)
        self.form.addRow(tr("Sens"), self.direction)
        self.form.addRow(tr("Motif"), self.reason)

    def values(self):
        return self.article.currentData(), iso_date(self.date), self.quantity.text(), self.direction.currentData(), self.reason.text()


class ReminderDialog(FormDialog):
    def __init__(self, parent=None):
        super().__init__(tr("Nouvelle échéance"), parent)
        self.title = QLineEdit()
        self.date = make_date(g.aujourd_hui().isoformat())
        self.source = QLineEdit()
        self.form.addRow(tr("Titre"), self.title)
        self.form.addRow(tr("Échéance"), self.date)
        self.form.addRow(tr("Lien source"), self.source)

    def values(self):
        return self.title.text().strip(), iso_date(self.date), self.source.text().strip()


def ouvrir_lien_officiel(parent, paypal=False):
    try:
        if not paypal and not UpdateInstructionsDialog(parent).exec():
            return
        key = "paypal_url" if paypal else "telechargements_url"
        url = editeur.lien(editeur.officiels().get(key, ""), paypal=paypal)
        if not url or not QDesktopServices.openUrl(QUrl(url)):
            show_info(parent, "Impossible d’ouvrir la page. Vérifiez votre navigateur.")
    except Exception as exc:
        show_error(parent, exc)


class UpdateInstructionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mettre à jour Patenteasy")
        self.setFixedWidth(500)
        self.setMinimumHeight(300)
        v = QVBoxLayout(self); v.setContentsMargins(22, 20, 22, 20); v.setSpacing(14)
        text = QLabel("Dans le dossier Proton :\n\n1. Ouvrez « Mise à jour Windows ».\n2. Téléchargez l’installateur le plus récent.\n3. Fermez Patenteasy.\n4. Lancez l’installateur par-dessus la version actuelle.\n\nSauvegardez vos données avant la mise à jour. Ne désinstallez pas Patenteasy.")
        text.setWordWrap(True); v.addWidget(text)
        bar = QHBoxLayout(); bar.addStretch()
        bar.addWidget(button(tr("Annuler"), self.reject, secondary=True))
        bar.addWidget(button("Ouvrir les téléchargements", self.accept))
        v.addLayout(bar)


class NewsletterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Bienvenue dans Patenteasy"))
        self.setFixedWidth(530)
        self.setMinimumHeight(270)
        v = QVBoxLayout(self); v.setContentsMargins(22, 20, 22, 20); v.setSpacing(12)
        text = QLabel("Vous souhaitez être informé des nouveautés et des logiciels de ska_987 ?")
        text.setWordWrap(True); v.addWidget(text)
        self.email = QLineEdit(); self.email.setPlaceholderText(tr("Votre adresse mail"))
        self.email.setMaxLength(254); v.addWidget(self.email)
        note = QLabel("Facultatif. Votre messagerie s’ouvre avec une demande prête à envoyer. Cliquez ensuite sur Envoyer.")
        note.setWordWrap(True); v.addWidget(note)
        self.status = QLabel(); self.status.setWordWrap(True); v.addWidget(self.status)
        bar = QHBoxLayout(); bar.addStretch()
        bar.addWidget(button(tr("Plus tard"), self.reject, secondary=True))
        bar.addWidget(button(tr("Je souhaite être informé"), self.demander))
        v.addLayout(bar)

    def demander(self):
        try:
            url = editeur.demande_informations(self.email.text())
            if QDesktopServices.openUrl(QUrl(url)):
                self.accept()
            else:
                QApplication.clipboard().setText("À : sav.centreprotech@proton.me\nObjet : Nouveautés ska_987\n\nJe souhaite être informé des nouveautés et des logiciels de ska_987.\nMon adresse mail : " + self.email.text().strip())
                self.status.setText("Aucune messagerie n’a pu être ouverte. La demande a été copiée : collez-la dans un mail à sav.centreprotech@proton.me.")
        except ValueError as exc:
            self.status.setText(str(exc)); self.email.setFocus()


def proposer_nouveautes(parent):
    settings = QSettings(str(db.BASE_DIR / "interface.ini"), QSettings.Format.IniFormat)
    if settings.value("bienvenue_vue", False, type=bool):
        return
    NewsletterDialog(parent).exec()
    settings.setValue("bienvenue_vue", True)
    settings.sync()


class DashboardPage(Page):
    def __init__(self, parent=None):
        super().__init__(tr("Votre activité"), tr("Tableau de bord"), "Votre activité en " + regional.configuration()["devise"] + "", parent)
        self.donation_button = button(tr("Faire un don"), self.donate, secondary=True)
        self.donation_button.setObjectName("donationButton")
        self.donation_button.setToolTip("Soutenir ska_987 sur PayPal — contribution facultative")
        self.update_button = button(tr("Mettre à jour"), lambda: demander_verification(self), secondary=True)
        links = QVBoxLayout()
        for widget in (self.donation_button, self.update_button):
            widget.setMinimumWidth(190)
            widget.setStyleSheet("min-height: 28px; padding: 10px 16px; font-size: 11pt;")
            links.addWidget(widget)
        self.heading_row.addLayout(links)
        actions = QHBoxLayout()
        actions.addWidget(button(tr("Créer un devis"), lambda: self.navigate.emit("devis")))
        actions.addWidget(button(tr("Ajouter une opération"), lambda: self.navigate.emit("journal"), secondary=True))
        actions.addWidget(button(tr("Ajouter un client"), lambda: self.navigate.emit("clients")))
        actions.addStretch()
        self.layout.addLayout(actions)
        metrics = QGridLayout()
        self.m_recettes = MetricCard(tr("Recettes enregistrées cette année"))
        self.m_depenses = MetricCard(tr("Dépenses enregistrées"))
        self.m_restant = MetricCard(tr("Reste à encaisser"))
        self.m_treso = MetricCard(tr("Trésorerie suivie"))
        for i, w in enumerate([self.m_recettes, self.m_depenses, self.m_restant, self.m_treso]):
            metrics.addWidget(w, 0, i)
        self.layout.addLayout(metrics)
        self.alert = QLabel()
        self.alert.setWordWrap(True)
        self.alert.setVisible(False)
        self.layout.addWidget(self.alert)
        grid = QGridLayout()
        self.unpaid = QTableWidget()
        self.unpaid.doubleClicked.connect(self.open_invoice)
        configure_table(self.unpaid, [tr("Facture / client"), tr("Reste dû"), tr("Échéance")])
        self.reminders = QTableWidget()
        configure_table(self.reminders, [tr("Échéance"), tr("Rappel")])
        box1 = QGroupBox(tr("Factures à encaisser"))
        l1 = QVBoxLayout(box1); l1.addWidget(self.unpaid);l1.addWidget(button(tr("Préparer une relance"),self.relance,secondary=True))
        box2 = QGroupBox(tr("Prochaines échéances"))
        l2 = QVBoxLayout(box2); l2.addWidget(self.reminders)
        grid.addWidget(box1, 0, 0)
        grid.addWidget(box2, 0, 1)
        self.layout.addLayout(grid)
        self.quotes = QTableWidget()
        self.quotes.doubleClicked.connect(self.open_quote)
        configure_table(self.quotes, [tr("Devis"), tr("Client"), tr("Objet"), tr("État")])
        box3 = QGroupBox(tr("Devis récents"))
        l3 = QVBoxLayout(box3); l3.addWidget(self.quotes)
        self.layout.addWidget(box3)
        self.layout.addStretch()

    def open_invoice(self):
        ident = selected_id(self.unpaid)
        if ident is not None: InvoiceDialog(ident, self).exec(); self.refresh()

    def open_quote(self):
        ident = selected_id(self.quotes)
        if ident is not None: QuoteEditorDialog(ident, self).exec(); self.refresh()

    def donate(self):
        ouvrir_lien_officiel(self, paypal=True)

    def refresh(self):
        e = db.obtenir_entreprise() or {}
        current_year = g.aujourd_hui().year
        summary = db.obtenir_resume_annuel(current_year)
        docs = g.documents()
        unpaid = []
        unpaid_ids=[]
        remaining = 0
        for d in docs:
            if d["type"] != "facture":
                continue
            rest = max(0, d["total_centiemes"] - d["paye"] - d["credite"])
            if not rest:
                continue
            client = json.loads(d["instantane"])["client"]["nom"]
            unpaid.append([f'{d["numero"]} · {client}', fcfp(rest), d["echeance"]])
            unpaid_ids.append(d["id"])
            remaining += rest
        self.m_recettes.value.setText(fcfp(summary["recettes"]))
        self.m_depenses.value.setText(fcfp(summary["depenses"]))
        self.m_restant.value.setText(fcfp(remaining))
        treasury = None
        if e.get("date_solde_depart"):
            ops = g.liste(
                "SELECT * FROM operations WHERE date_operation>=? AND date_operation<=?",
                (e["date_solde_depart"], g.aujourd_hui().isoformat()),
            )
            treasury = e.get("solde_depart_centiemes", 0) + sum(
                op["montant_centiemes"] * (1 if op["type_operation"] == "recette" else -1) for op in ops
            )
        self.m_treso.value.setText(fcfp(treasury) if treasury is not None else tr("À initialiser"))
        fill_table(self.unpaid, unpaid,unpaid_ids)
        reminders = g.liste("SELECT * FROM rappels WHERE fait=0 ORDER BY echeance LIMIT 8")
        fill_table(self.reminders, [[x["echeance"], x["titre"]] for x in reminders])
        quotes = db.lister_devis()[:6]
        fill_table(self.quotes, [[f'#{x["id"]}', x["nom_client"], x["objet"], x["statut"]] for x in quotes], [x["id"] for x in quotes])
        alerts = list(summary.get("alertes", []))
        fiscal_reminder = g.rappel_seuil_ca(current_year)
        if fiscal_reminder:
            alerts.append(fiscal_reminder)
        if not e.get("nom"):
            alerts.insert(0, tr("Commencez par renseigner votre entreprise."))
        self.alert.setText("\n".join("• " + x for x in alerts))
        self.alert.setVisible(bool(alerts))

    def relance(self):
        ident=selected_id(self.unpaid)
        if ident is None:show_info(self,tr("Sélectionnez une facture à relancer."));return
        from interface_beta import relancer
        relancer(self,ident)


class ClientsPage(Page):
    def __init__(self, parent=None):
        super().__init__(tr("Répertoire"), tr("Clients"), tr("Coordonnées utilisées dans les devis et factures."), parent)
        bar = QHBoxLayout()
        bar.addWidget(button(tr("Ajouter un client"), self.add))
        bar.addWidget(button(tr("Modifier"), self.edit, secondary=True))
        bar.addStretch()
        self.layout.addLayout(bar)
        self.recherche=QLineEdit();self.recherche.setPlaceholderText(tr("Rechercher par nom ou numéro"));self.recherche.textChanged.connect(lambda _texte:self.refresh());self.layout.addWidget(self.recherche)
        self.table = QTableWidget()
        configure_table(self.table, [tr("Nom"), tr("Téléphone"), tr("E-mail"), tr("Adresse")])
        self.table.doubleClicked.connect(self.edit)
        self.layout.addWidget(self.table)

    def refresh(self):
        rows = db.lister_clients()
        terme=self.recherche.text().casefold().strip()
        if terme:rows=[x for x in rows if terme in " ".join(str(x.get(k,"")) for k in ("nom","telephone","email")).casefold()]
        fill_table(self.table, [[x["nom"], x["telephone"], x["email"], x["adresse"]] for x in rows], [x["id"] for x in rows])

    def add(self):
        d = ClientDialog(parent=self)
        if d.exec():
            try:
                db.ajouter_client(*d.values()); self.refresh()
            except Exception as exc: show_error(self, exc)

    def edit(self):
        ident = selected_id(self.table)
        if ident is None: return
        data = db.obtenir_client(ident)
        d = ClientDialog(data, self)
        if d.exec():
            try:
                db.modifier_client(ident, *d.values()); self.refresh()
            except Exception as exc: show_error(self, exc)


class ArticlesPage(Page):
    def __init__(self, parent=None):
        super().__init__(tr("Catalogue"), tr("Produits et prestations"), tr("Prix et taux utilisés pour préremplir les devis."), parent)
        bar = QHBoxLayout()
        bar.addWidget(button(tr("Ajouter"), self.add))
        bar.addWidget(button(tr("Modifier"), self.edit, secondary=True))
        bar.addWidget(button(tr("Supprimer"), self.delete, danger=True))
        bar.addStretch()
        self.layout.addLayout(bar)
        self.table = QTableWidget()
        configure_table(self.table, [tr("Référence"), tr("Désignation"), tr("Type"), tr("Unité"), tr("Achat"), tr("Vente HT"), tr("Taxe %")])
        self.table.doubleClicked.connect(self.edit)
        self.layout.addWidget(self.table)

    def refresh(self):
        rows = db.lister_articles()
        fill_table(self.table, [[x["reference"], x["designation"], tr("Produit") if x["type_article"] == "produit" else tr("Prestation"), x["unite"], fcfp(x["prix_achat_centiemes"]), fcfp(x["prix_vente_centiemes"]), decimal_text(x["taxe_centiemes"])] for x in rows], [x["id"] for x in rows])

    def add(self):
        d = ArticleDialog(parent=self)
        if d.exec():
            try: db.ajouter_article(*d.values()); self.refresh()
            except Exception as exc: show_error(self, exc)

    def edit(self):
        ident = selected_id(self.table)
        if ident is None: return
        d = ArticleDialog(db.obtenir_article(ident), self)
        if d.exec():
            try: db.modifier_article(ident, *d.values()); self.refresh()
            except Exception as exc: show_error(self, exc)

    def delete(self):
        ident = selected_id(self.table)
        if ident is None: return
        if confirm(self, tr("Supprimer cet élément du catalogue ?")):
            try: db.supprimer_article(ident); self.refresh()
            except Exception as exc: show_error(self, exc)


class QuoteEditorDialog(QDialog):
    changed = Signal()

    def __init__(self, quote_id: int, parent=None):
        super().__init__(parent)
        self.quote_id = quote_id
        self._loading = True
        self._ready = False
        self._dirty = False
        self.setWindowTitle(tr("Devis"))
        self.resize(1120, 790)
        outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        body = QWidget()
        root = QVBoxLayout(body)
        root.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll)
        self.status = QLabel()
        self.status.setObjectName("lead")
        root.addWidget(self.status)
        self.save_state=QLabel();self.save_state.setWordWrap(True);root.addWidget(self.save_state)
        header = QGroupBox(tr("En-tête du devis"))
        form = QGridLayout(header)
        self.client = QComboBox()
        self.clients = db.lister_clients()
        for c in self.clients: self.client.addItem(c["nom"], c["id"])
        self.date = make_date()
        self.objet = QLineEdit()
        self.validite = QSpinBox(); self.validite.setRange(1, 365)
        form.addWidget(QLabel(tr("Client")), 0, 0); form.addWidget(self.client, 0, 1)
        form.addWidget(QLabel(tr("Date")), 0, 2); form.addWidget(self.date, 0, 3)
        form.addWidget(QLabel(tr("Objet")), 1, 0); form.addWidget(self.objet, 1, 1, 1, 3)
        form.addWidget(QLabel(tr("Validité (jours)")), 2, 0); form.addWidget(self.validite, 2, 1)
        root.addWidget(header)
        linebar = QHBoxLayout()
        self.add_catalog_btn = button(tr("Ajouter du catalogue"), self.add_catalog)
        self.add_free_btn = button(tr("Ajouter une ligne libre"), self.add_free, secondary=True)
        self.edit_line_btn = button(tr("Modifier la ligne"), self.edit_line, secondary=True)
        self.remove_line_btn = button(tr("Retirer la ligne"), self.remove_line, danger=True)
        for b in [self.add_catalog_btn, self.add_free_btn, self.edit_line_btn, self.remove_line_btn]: linebar.addWidget(b)
        linebar.addStretch()
        root.addLayout(linebar)
        self.lines = QTableWidget()
        configure_table(self.lines, [tr("Référence"), tr("Désignation"), tr("Quantité"), tr("Prix HT"), tr("Taxe %"), tr("Total HT")])
        self.lines.doubleClicked.connect(self.edit_line)
        root.addWidget(self.lines, 1)
        self.total = QLabel(); self.total.setWordWrap(True); self.total.setProperty("class", "metricValue"); self.total.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(self.total)
        actions = QGridLayout()
        self.save_btn = button(tr("Enregistrer le brouillon"), self.save_header)
        self.pdf_btn = button(tr("Aperçu PDF"), self.preview_pdf, secondary=True)
        self.export_btn = button(tr("Exporter le PDF"), self.export_pdf, secondary=True)
        self.emit_btn = button(tr("Finaliser le devis"), self.emit_quote)
        self.accept_btn = button(tr("Marquer accepté"), lambda: self.decision("accepte"))
        self.refuse_btn = button(tr("Marquer refusé"), lambda: self.decision("refuse"), danger=True)
        self.invoice_btn = button(tr("Créer la facture"), self.create_invoice)
        self.duplicate_btn = button(tr("Dupliquer"), self.duplicate, secondary=True)
        close = button(tr("Fermer"), self.accept, secondary=True)
        for i, b in enumerate([self.save_btn, self.pdf_btn, self.export_btn, self.emit_btn, self.accept_btn, self.refuse_btn, self.invoice_btn, self.duplicate_btn]):
            actions.addWidget(b, i // 4, i % 4)
        outer.addWidget(close)
        root.addLayout(actions)
        conditions_note = QLabel(tr("Les conditions facultatives se définissent dans Réglages et s’affichent en bas du PDF."))
        conditions_note.setWordWrap(True)
        root.addWidget(conditions_note)
        self.refresh()
        self._ready = True
        self.auto_save = QTimer(self);self.auto_save.setSingleShot(True);self.auto_save.setInterval(650)
        self.auto_save.timeout.connect(lambda:self.save_header(quiet=True,refresh=False))
        for entry in (self.objet,):entry.textChanged.connect(self.edited)
        self.date.entry.textChanged.connect(self.edited);self.client.currentIndexChanged.connect(self.edited);self.validite.valueChanged.connect(self.edited)

    def edited(self,*_):
        if self._loading:return
        self._dirty=True;self.save_state.setText(tr("Enregistrement…"));self.auto_save.start()

    def state(self):
        return {'client_id':self.client.currentData(),'date':self.date.entry.text(),'objet':self.objet.text(),'validite':self.validite.value()}

    def closeEvent(self,event):
        if self._ready and self._dirty and not self.save_header(quiet=True,refresh=False):
            event.ignore();return
        event.accept()

    def done(self,result):
        if self._ready and self._dirty and not self.save_header(quiet=True,refresh=False):return
        super().done(result)

    def refresh(self,keep_header=False):
        self._loading=True
        d = db.obtenir_devis(self.quote_id)
        if not d:
            self.reject(); return
        s = g.calculer(self.quote_id)
        self.status.setText(tr("Devis")+" "+(d.get("numero") or tr("brouillon")+" #"+str(d["id"]))+" · "+tr(d["statut"])+" · "+d["nom_client"])
        if not keep_header:
            idx = self.client.findData(d["client_id"])
            if idx >= 0: self.client.setCurrentIndex(idx)
            self.date.setDate(qdate_from_iso(d["date_devis"]))
            self.objet.setText(d["objet"])
            self.validite.setValue(d.get("validite_jours", 30))
            pending=g.lire_brouillon_ui(self.quote_id) if d['statut']=='brouillon' else None
            if pending:
                self.client.setCurrentIndex(max(0,self.client.findData(pending['client_id'])))
                self.date.entry.setText(pending['date']);self.objet.setText(pending['objet']);self.validite.setValue(pending['validite'])
                self.save_state.setText(tr("Brouillon enregistré · vérifiez les champs incomplets."))
            else:self.save_state.setText(tr("Brouillon enregistré automatiquement.") if d['statut']=='brouillon' else tr("Document finalisé."))
        lines = s["lignes"]
        fill_table(self.lines, [[x.get("reference", ""), x["designation"], f'{decimal_text(x["quantite_centiemes"])} {x["unite"]}', fcfp(x["prix_unitaire_centiemes"]), decimal_text(x["taxe_centiemes"]), fcfp(x["ht"])] for x in lines], [x["id"] for x in lines])
        regime = s.get("regime")
        total = tr("Total HT : ")+fcfp(s["ht"])
        if regime:
            total += "   ·   "+regional.configuration()["nom_taxe"]+" : "+fcfp(s["tva"])+"   ·   "+tr("Total")+" : "+fcfp(s["ttc"])
        else:
            total += "   ·   "+tr("Total")+" : "+fcfp(s["ttc"])+" · "+tr("Sans taxe calculée")
        self.total.setText(total)
        draft = d["statut"] == "brouillon"
        sent = d["statut"] == "envoye"
        accepted = d["statut"] == "accepte"
        for w in [self.client, self.date, self.objet, self.validite]: w.setEnabled(draft)
        for b in [self.save_btn, self.add_catalog_btn, self.add_free_btn, self.edit_line_btn, self.remove_line_btn]: b.setVisible(draft)
        self.emit_btn.setVisible(draft)
        self.accept_btn.setVisible(sent); self.refuse_btn.setVisible(sent)
        self.invoice_btn.setVisible(accepted)
        self.changed.emit()
        self._loading=False

    def save_header(self,quiet=False,refresh=True):
        if hasattr(self,'auto_save'):self.auto_save.stop()
        if db.obtenir_devis(self.quote_id)['statut']!='brouillon':return True
        try:
            g.enregistrer_brouillon_ui(self.quote_id,self.state())
            self._dirty=False
        except Exception as exc:
            self.save_state.setText(tr("Enregistrement impossible. Vos modifications restent dans cette fenêtre."))
            if not quiet:show_error(self,exc)
            return False
        try:
            g.modifier_devis(self.quote_id,self.client.currentData(),iso_date(self.date),self.objet.text(),self.validite.value())
            with g.connexion() as c:c.execute('DELETE FROM brouillons_ui WHERE devis_id=?',(self.quote_id,))
            self.save_state.setText(tr("Brouillon enregistré automatiquement."))
            if refresh:self.refresh(keep_header=True)
            return True
        except ValueError as exc:
            self.save_state.setText(tr("Brouillon enregistré · "+str(exc)))
            if not quiet:show_error(self,exc)
            return quiet
        except Exception as exc:
            if not quiet:show_error(self,exc)
            return False

    def preview_pdf(self):
        if not self.save_header(refresh=False):return
        try:
            from apercu_pdf import ouvrir
            s=g.calculer(self.quote_id);d=db.obtenir_devis(self.quote_id)
            ouvrir(self,generer(s,not bool(d.get('instantane'))),(d.get('numero') or 'devis-brouillon')+'.pdf')
        except Exception as exc:show_error(self,exc)

    def add_catalog(self):
        if not self.save_header(quiet=True,refresh=False):return
        d = CatalogLineDialog(self)
        if d.exec():
            article, qty = d.values()
            if not article: return
            try:
                db.ajouter_ligne_devis(self.quote_id, article["designation"], article["unite"], qty, money_text(article["prix_vente_centiemes"]), decimal_text(article["taxe_centiemes"]), article["reference"], False, article["type_article"])
                self.refresh(keep_header=True)
            except Exception as exc: show_error(self, exc)

    def add_free(self):
        if not self.save_header(quiet=True,refresh=False):return
        d = QuoteLineDialog(parent=self)
        if d.exec():
            try: db.ajouter_ligne_devis(self.quote_id, *d.values()); self.refresh(keep_header=True)
            except Exception as exc: show_error(self, exc)

    def edit_line(self):
        if not self.save_header(quiet=True,refresh=False):return
        line_id = selected_id(self.lines)
        if line_id is None: return
        data = db.obtenir_ligne_devis(self.quote_id, line_id)
        d = QuoteLineDialog(data, allow_catalog=False, parent=self)
        if d.exec():
            vals = d.values()
            try:
                db.modifier_ligne_devis(self.quote_id, line_id, vals[0], vals[1], vals[2], vals[3], vals[4], vals[5])
                self.refresh(keep_header=True)
            except Exception as exc: show_error(self, exc)

    def remove_line(self):
        if not self.save_header(quiet=True,refresh=False):return
        line_id = selected_id(self.lines)
        if line_id is None: return
        if confirm(self, tr("Retirer cette ligne du devis ?")):
            try: db.supprimer_ligne_devis(self.quote_id, line_id); self.refresh(keep_header=True)
            except Exception as exc: show_error(self, exc)

    def emit_quote(self):
        if not confirm(self, tr("Émettre ce devis ? Un numéro sera attribué et cette version sera figée.")):
            return
        try:
            if not self.save_header():
                return
            g.emettre_devis(self.quote_id)
            self.refresh()
        except Exception as exc:
            show_error(self, exc)

    def decision(self, status):
        try: g.decision_devis(self.quote_id, status); self.refresh()
        except Exception as exc: show_error(self, exc)

    def export_pdf(self):
        if not self.save_header(refresh=False):return
        try:
            s = g.calculer(self.quote_id)
            d = db.obtenir_devis(self.quote_id)
            name = (d.get("numero") or f"devis-brouillon-{self.quote_id}") + ".pdf"
            save_pdf(self, generer(s, not bool(d.get("instantane"))), name)
        except Exception as exc: show_error(self, exc)

    def duplicate(self):
        if not self.save_header(refresh=False):return
        try:
            new_id = g.dupliquer_devis(self.quote_id)
            show_info(self, f"Copie créée : devis #{new_id}")
            self.changed.emit()
        except Exception as exc: show_error(self, exc)

    def create_invoice(self):
        d = QDialog(self); d.setWindowTitle(tr("Créer la facture"))
        layout = QFormLayout(d)
        invoice_date = make_date(g.aujourd_hui().isoformat())
        due = make_date(g.aujourd_hui().isoformat())
        layout.addRow(tr("Date de facture"), invoice_date); layout.addRow(tr("Échéance"), due)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); layout.addRow(bb)
        if d.exec():
            try:
                fid = g.creer_facture(self.quote_id, iso_date(invoice_date), iso_date(due))
                self.changed.emit(); self.refresh()
                InvoiceDialog(fid, self).exec()
                self.changed.emit()
            except Exception as exc: show_error(self, exc)


class QuotesPage(Page):
    def __init__(self, parent=None):
        super().__init__(tr("Ventes"), tr("Devis"), tr("Préparez vos devis, puis créez vos factures."), parent)
        bar = QHBoxLayout()
        bar.addWidget(button(tr("Créer un devis"), self.add))
        bar.addWidget(button(tr("Ouvrir"), self.open, secondary=True))
        bar.addWidget(button(tr("Ouvrir le dossier PDF"), lambda: open_pdf_folder(self), secondary=True))
        bar.addStretch(); self.layout.addLayout(bar)
        self.recherche=QLineEdit();self.recherche.setPlaceholderText(tr("Rechercher par nom ou numéro"));self.recherche.textChanged.connect(lambda _texte:self.refresh());self.layout.addWidget(self.recherche)
        self.table = QTableWidget(); configure_table(self.table, [tr("N°"), tr("Date"), tr("Client"), tr("Objet"), tr("État")])
        self.table.doubleClicked.connect(self.open); self.layout.addWidget(self.table)

    def refresh(self):
        rows = db.lister_devis()
        enriched = []
        ids = []
        for x in rows:
            d = db.obtenir_devis(x["id"])
            terme=self.recherche.text().casefold().strip()
            if terme and terme not in " ".join(str(v) for v in (d.get("numero",""),x["nom_client"],x["objet"],x["id"])).casefold():continue
            enriched.append([d.get("numero") or f'Brouillon #{x["id"]}', x["date_devis"], x["nom_client"], x["objet"], x["statut"]])
            ids.append(x["id"])
        fill_table(self.table, enriched, ids)

    def add(self):
        if not db.lister_clients():
            show_info(self, tr("Ajoutez d’abord un client.")); return
        d = QuoteCreateDialog(self)
        if d.exec():
            try:
                ident = g.creer_devis(*d.values())
                self.refresh(); QuoteEditorDialog(ident, self).exec(); self.refresh()
            except Exception as exc: show_error(self, exc)

    def open(self):
        ident = selected_id(self.table)
        if ident is None: return
        dlg = QuoteEditorDialog(ident, self); dlg.changed.connect(self.refresh); dlg.exec(); self.refresh()


class InvoiceDialog(QDialog):
    changed = Signal()
    def __init__(self, document_id: int, parent=None):
        super().__init__(parent)
        self.document_id = document_id
        self.resize(980, 720)
        self.setWindowTitle(tr("Facture / avoir"))
        outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        body = QWidget()
        root = QVBoxLayout(body)
        root.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll)
        self.heading = QLabel(); self.heading.setObjectName("title"); self.heading.setWordWrap(True); root.addWidget(self.heading)
        self.metrics = QLabel(); self.metrics.setObjectName("lead"); self.metrics.setWordWrap(True); root.addWidget(self.metrics)
        self.lines = QTableWidget(); configure_table(self.lines, [tr("Référence"), tr("Désignation"), tr("Quantité"), tr("Prix HT"), tr("Total HT")]); root.addWidget(self.lines, 1)
        self.payments = QTableWidget(); configure_table(self.payments, [tr("Date"), tr("Montant"), tr("Moyen"), tr("Référence")])
        box = QGroupBox(tr("Paiements enregistrés")); boxl = QVBoxLayout(box); boxl.addWidget(self.payments); root.addWidget(box)
        bar = QGridLayout()
        self.pdf_btn = button(tr("Aperçu PDF"), self.preview_pdf, secondary=True)
        self.export_btn = button(tr("Exporter le PDF"), self.export_pdf, secondary=True)
        self.pay_btn = button(tr("Enregistrer un paiement"), self.pay)
        self.credit_btn = button(tr("Émettre un avoir"), self.credit, danger=True)
        self.refund_btn = button(tr("Enregistrer un remboursement"), self.refund, secondary=True)
        for i, b in enumerate([self.pdf_btn, self.export_btn, self.pay_btn, self.credit_btn, self.refund_btn]):
            bar.addWidget(b, i // 3, i % 3)
        bar.addWidget(button(tr("Fermer"), self.accept, secondary=True), 1, 2); outer.addLayout(bar)
        self.refresh()

    def refresh(self):
        d = g.document(self.document_id)
        c = d["contenu"]
        self.heading.setText(f'{d["numero"]} · {c["client"]["nom"]}')
        self.metrics.setText(f'Total {fcfp(d["total_centiemes"])} · Réglé {fcfp(d["paye"])} · Avoirs {fcfp(d["credite"])}' + (f' · Reste {fcfp(d["reste"])}' if d["type"] == "facture" else ""))
        fill_table(self.lines, [[x.get("reference", ""), x["designation"], f'{decimal_text(x["quantite_centiemes"])} {x["unite"]}', fcfp(x["prix_unitaire_centiemes"]), fcfp(x["ht"])] for x in c["lignes"]])
        fill_table(self.payments, [[x["date_paiement"], fcfp(x["montant_centiemes"]), x["mode"], x["reference"]] for x in d["paiements"]])
        self.pay_btn.setVisible(d["type"] == "facture" and d["reste"] > 0)
        self.credit_btn.setVisible(d["type"] == "facture" and d["credite"] < d["total_centiemes"])
        self.refund_btn.setVisible(d.get("a_rembourser", 0) > 0)
        if not est_admin(self):
            self.credit_btn.hide(); self.refund_btn.hide()
        self.changed.emit()

    def preview_pdf(self):
        try:
            from apercu_pdf import ouvrir
            d = g.document(self.document_id)
            ouvrir(self, generer(d["contenu"]), d["numero"] + ".pdf")
        except Exception as exc:
            show_error(self, exc)

    def export_pdf(self):
        try:
            d = g.document(self.document_id)
            save_pdf(self, generer(d["contenu"]), d["numero"] + ".pdf")
        except Exception as exc: show_error(self, exc)

    def pay(self):
        dlg = PaymentDialog(False, self)
        if dlg.exec():
            try:
                day, amount, mode, ref = dlg.values(); g.payer(self.document_id, day, amount, mode, ref); QApplication.instance().fenetre_principale.gestion_comptes.tracer(tr("Encaissement client"), str(self.document_id)); self.refresh()
            except Exception as exc: show_error(self, exc)

    def credit(self):
        if not exiger_admin(self): return
        doc = g.document(self.document_id)
        dlg = CreditDialog(doc, self)
        if dlg.exec():
            motif, quantities = dlg.values()
            try:
                aid = g.creer_avoir(self.document_id, motif, quantities)
                show_info(self, f"Avoir créé (document #{aid})."); self.refresh()
            except Exception as exc: show_error(self, exc)

    def refund(self):
        if not exiger_admin(self): return
        dlg = PaymentDialog(True, self)
        if dlg.exec():
            try:
                day, amount, mode, _ = dlg.values(); g.rembourser(self.document_id, day, amount, mode); self.refresh()
            except Exception as exc: show_error(self, exc)


class InvoicesPage(Page):
    def __init__(self, parent=None):
        super().__init__(tr("Documents"), tr("Factures et encaissements"), tr("Retrouvez une facture pour enregistrer un paiement."), parent)
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(tr("Numéro exact de facture"))
        self.recherche.returnPressed.connect(self.refresh)
        self.recherche.textChanged.connect(lambda _texte: self.refresh())
        bar = QHBoxLayout(); bar.addWidget(self.recherche); bar.addWidget(button(tr("Rechercher"), self.refresh)); bar.addWidget(button(tr("Ouvrir"), self.open, secondary=True)); bar.addWidget(button(tr("Ouvrir le dossier PDF"), lambda: open_pdf_folder(self), secondary=True))
        self.layout.addLayout(bar)
        self.table = QTableWidget(); configure_table(self.table, [tr("Numéro"), tr("Date"), tr("Client"), tr("Total"), tr("Réglé"), tr("Reste")])
        self.table.doubleClicked.connect(self.open); self.layout.addWidget(self.table)

    def refresh(self):
        texte = self.recherche.text().strip()
        if not est_admin(self) and not texte:
            fill_table(self.table, [], []); return
        rows=[]; ids=[]
        for d in g.documents():
            if texte:
                contenu_recherche=json.loads(d["instantane"])
                if est_admin(self):
                    if texte.casefold() not in (d["numero"]+" "+contenu_recherche["client"]["nom"]).casefold():continue
                elif d["numero"].casefold()!=texte.casefold():continue
            if not est_admin(self) and d["type"] != "facture": continue
            content=json.loads(d["instantane"]); rest=max(0,d["total_centiemes"]-d["paye"]-d["credite"])
            rows.append([d["numero"], d["date_document"], content["client"]["nom"], fcfp(d["total_centiemes"]), fcfp(d["paye"]), fcfp(rest)])
            ids.append(d["id"])
        fill_table(self.table, rows, ids)

    def open(self):
        ident=selected_id(self.table)
        if ident is None:return
        d=InvoiceDialog(ident,self);d.changed.connect(self.refresh);d.exec();self.refresh()


class JournalPage(Page):
    def __init__(self, parent=None):
        super().__init__(tr("Trésorerie"), tr("Recettes et dépenses"), tr("Notez vos recettes et vos dépenses."), parent)
        top=QHBoxLayout(); self.year=QSpinBox(); self.year.setRange(1900, 9999); self.year.setValue(g.aujourd_hui().year); self.year.valueChanged.connect(self.refresh)
        top.addWidget(QLabel(tr("Année")));top.addWidget(self.year);top.addWidget(button(tr("Ajouter une opération"),self.add));top.addWidget(button(tr("Modifier"),self.edit,secondary=True));top.addWidget(button(tr("Supprimer"),self.delete,danger=True));top.addWidget(button(tr("Exporter CSV"),self.exporter_csv,secondary=True));top.addStretch();self.layout.addLayout(top)
        metrics=QHBoxLayout();self.rec=MetricCard(tr("Recettes"));self.dep=MetricCard(tr("Dépenses"));self.diff=MetricCard(tr("Différence"))
        for m in [self.rec,self.dep,self.diff]:metrics.addWidget(m)
        self.layout.addLayout(metrics)
        self.alert=QLabel();self.alert.setWordWrap(True);self.layout.addWidget(self.alert)
        self.table=QTableWidget();configure_table(self.table,[tr("Date"),tr("Libellé"),tr("Type"),tr("Montant")]);self.table.doubleClicked.connect(self.edit);self.layout.addWidget(self.table)

    def refresh(self,*_):
        year=self.year.value(); summary=db.obtenir_resume_annuel(year);self.rec.value.setText(fcfp(summary["recettes"]));self.dep.value.setText(fcfp(summary["depenses"]));self.diff.value.setText(fcfp(summary["difference"]));self.alert.setText("\n".join("• "+a for a in summary.get("alertes",[])))
        rows=db.lister_operations(year);fill_table(self.table,[[x["date_operation"],x["libelle"],x["type_operation"],fcfp(x["montant_centiemes"])] for x in rows],[x["id"] for x in rows])

    def add(self):
        d=OperationDialog(parent=self)
        if d.exec():
            try:db.ajouter_operation(*d.values());self.refresh()
            except Exception as exc:show_error(self,exc)

    def _protected(self,ident):
        return bool(g.liste('SELECT id FROM paiements WHERE operation_id=?',(ident,)) or g.liste('SELECT id FROM remboursements WHERE operation_id=?',(ident,)))

    def edit(self):
        ident=selected_id(self.table)
        if ident is None:return
        if self._protected(ident):show_info(self,"Cette opération provient d’un paiement ou remboursement de facture et doit rester liée au document.");return
        d=OperationDialog(db.obtenir_operation(ident),self)
        if d.exec():
            try:db.modifier_operation(ident,*d.values());self.refresh()
            except Exception as exc:show_error(self,exc)

    def delete(self):
        ident=selected_id(self.table)
        if ident is None:return
        if self._protected(ident):show_info(self,"Cette opération provient d’un paiement ou remboursement de facture et ne peut pas être supprimée ici.");return
        if confirm(self,tr("Supprimer cette opération ?")):
            try:db.supprimer_operation(ident);self.refresh()
            except Exception as exc:show_error(self,exc)


    def exporter_csv(self):
        if not exiger_admin(self):return
        fichier,_=QFileDialog.getSaveFileName(self,tr('Export pour le comptable'),f'Recettes-depenses-{self.year.value()}.csv','CSV (*.csv)')
        if not fichier:return
        try:self.window().beta.exporter_csv(self.year.value(),fichier);show_info(self,'Export enregistré. Ce fichier contient vos opérations en clair : transmettez-le à votre comptable par un moyen privé.')
        except Exception as e:show_error(self,e)

class StockPage(Page):
    def __init__(self,parent=None):
        super().__init__(tr("Inventaire"),tr("Stock"),tr("Suivez les quantités de vos produits."),parent)
        bar=QHBoxLayout();bar.addWidget(button(tr("Nouveau mouvement"),self.move));bar.addStretch();self.layout.addLayout(bar)
        self.table=QTableWidget();configure_table(self.table,[tr("Référence"),tr("Produit"),tr("Unité"),tr("Stock")]);self.layout.addWidget(self.table)
        self.movements=QTableWidget();configure_table(self.movements,[tr("Date"),tr("Produit"),tr("Quantité"),tr("Motif")])
        box=QGroupBox(tr("Mouvements récents"));bl=QVBoxLayout(box);bl.addWidget(self.movements);self.layout.addWidget(box)

    def refresh(self):
        rows=g.stock();fill_table(self.table,[[x["reference"],x["designation"],x["unite"],decimal_text(x["stock"])] for x in rows],[x["id"] for x in rows])
        mov=g.liste('SELECT s.*,a.designation FROM stock_mouvements s JOIN articles a ON a.id=s.article_id ORDER BY date_mouvement DESC,s.id DESC')
        fill_table(self.movements,[[x["date_mouvement"],x["designation"],decimal_text(x["quantite_centiemes"]),x["motif"]] for x in mov])

    def move(self):
        if not g.stock():show_info(self,tr("Ajoutez d’abord un produit au catalogue."));return
        d=StockDialog(self)
        if d.exec():
            try:g.bouger_stock(*d.values());self.refresh()
            except Exception as exc:show_error(self,exc)


class RemindersPage(Page):
    def __init__(self,parent=None):
        super().__init__(tr("Organisation"),tr("Échéances"),tr("Retrouvez vos prochaines dates importantes."),parent)
        bar=QHBoxLayout();bar.addWidget(button(tr("Ajouter"),self.add));bar.addWidget(button(tr("Basculer fait / à faire"),self.toggle,secondary=True));self.import_local=button("Importer Taxe 2026 · Polynésie",self.import_2026,secondary=True);self.import_local.setVisible(regional.configuration()["pays"]=="PF");bar.addWidget(self.import_local);bar.addStretch();self.layout.addLayout(bar)
        self.table=QTableWidget();configure_table(self.table,[tr("Échéance"),tr("Titre"),tr("État"),tr("Source")]);self.layout.addWidget(self.table)

    def refresh(self):
        rows=g.liste('SELECT * FROM rappels ORDER BY fait,echeance');fill_table(self.table,[[x["echeance"],x["titre"],tr("Fait") if x["fait"] else tr("À faire"),x["source"]] for x in rows],[x["id"] for x in rows])

    def add(self):
        d=ReminderDialog(self)
        if d.exec():
            title,day,source=d.values()
            try:
                if not title:raise ValueError("Titre obligatoire.")
                if source and not source.startswith(("https://","http://")):raise ValueError("Utilisez un lien http ou https.")
                with g.connexion() as c:c.execute('INSERT OR IGNORE INTO rappels(titre,echeance,source) VALUES(?,?,?)',(title,g.date_valide(day),source))
                self.refresh()
            except Exception as exc:show_error(self,exc)

    def toggle(self):
        ident=selected_id(self.table)
        if ident is None:return
        try:
            with g.connexion() as c:c.execute('UPDATE rappels SET fait=1-fait WHERE id=?',(ident,))
            self.refresh()
        except Exception as exc:show_error(self,exc)

    def import_2026(self):
        if regional.configuration()["pays"] != "PF":return
        e=db.obtenir_entreprise();period=e.get('periodicite_tva','')
        if not period:show_info(self,"Choisissez d’abord la périodicité Taxe dans Réglages.");return
        dates=['01-15','02-16','03-16','04-15','05-15','06-15','07-15','08-17','09-15','10-15','11-16','12-15']
        try:
            with g.connexion() as c:
                for i,day in enumerate(dates,1):
                    if period=='trimestrielle' and i not in (1,4,7,10):continue
                    c.execute('INSERT OR IGNORE INTO rappels(titre,echeance,source) VALUES(?,?,?)',(f'Taxe {period} — échéance 2026','2026-'+day,'https://www.service-public.pf/dicp/calendrier-fiscal-polynesie-2026/'))
            self.refresh()
        except Exception as exc:show_error(self,exc)


class CompanyPage(Page):
    def __init__(self,parent=None):
        super().__init__(tr("Identité"),tr("Mon entreprise"),tr("Identité et formats utilisés dans vos documents."),parent)
        card=QGroupBox(tr("Coordonnées"));form=QFormLayout(card)
        self.nom=QLineEdit();self.responsable=QLineEdit();self.tel=QLineEdit();self.email=QLineEdit();self.adresse=QTextEdit();self.tahiti=QLineEdit();self.rcs=QLineEdit()
        for label,w in [(tr("Nom de l’entreprise *"),self.nom),(tr("Responsable"),self.responsable),(tr("Téléphone"),self.tel),(tr("E-mail"),self.email),(tr("Adresse"),self.adresse),(tr("Identifiant professionnel (facultatif)"),self.tahiti),(tr("Registre / autre identifiant (facultatif)"),self.rcs)]:form.addRow(label,w)
        self.layout.addWidget(card)
        formats=QGroupBox(tr("Pays et formats"));f=QFormLayout(formats)
        self.pays=QComboBox();self.pays.addItem(tr("Profil général · pays non renseigné"), "")
        countries=[]
        for country in QLocale.Country:
            code=QLocale.territoryToCode(country)
            if len(code)==2:countries.append((QLocale.territoryToString(country),code))
        for name,code in sorted(set(countries)):self.pays.addItem(name+' · '+code,code)
        self.devise=QLineEdit();self.devise.setMaxLength(3);self.devise.setPlaceholderText("EUR, USD, XPF…")
        self.precision=QSpinBox();self.precision.setRange(0,4)
        self.langue=QComboBox();self.langue.addItem("Français",'fr');self.langue.addItem("English",'en')
        self.format_date=QComboBox()
        for key,label in regional.FORMATS.items():self.format_date.addItem(label,key)
        self.nom_taxe=QLineEdit();self.mention_exoneree=QLineEdit();self.libelle_identifiant=QLineEdit()
        for label,w in [(tr("Pays"),self.pays),(tr("Devise · code de trois lettres"),self.devise),(tr("Décimales des montants"),self.precision),(tr("Langue"),self.langue),(tr("Format des dates"),self.format_date),(tr("Nom de la taxe"),self.nom_taxe),(tr("Mention sans taxe (facultatif)"),self.mention_exoneree),(tr("Libellé de l’identifiant"),self.libelle_identifiant)]:f.addRow(label,w)
        note=QLabel(tr("Choisissez la devise et sa précision avant de saisir vos premiers montants. Les taxes sont définies par vos choix ; les rappels locaux sont informatifs."));note.setWordWrap(True);f.addRow(note)
        self.layout.addWidget(formats);self.layout.addWidget(button(tr("Enregistrer les coordonnées et formats"),self.save))
        self.saved=QLabel();self.saved.setWordWrap(True);self.layout.addWidget(self.saved)
        box=QGroupBox(tr("Début d’activité (facultatif)"));fl=QFormLayout(box);self.start=DateInput(optional=True);fl.addRow(tr("Date"),self.start);self.layout.addWidget(box);self.layout.addWidget(button(tr("Enregistrer la date de début"),self.save_start,secondary=True));self.layout.addStretch()

    def refresh(self):
        e=db.obtenir_entreprise() or {};cfg=regional.configuration(e)
        self.nom.setText(e.get('nom',''));self.responsable.setText(e.get('responsable',''));self.tel.setText(e.get('telephone',''));self.email.setText(e.get('email',''));self.adresse.setPlainText(e.get('adresse',''));self.tahiti.setText(e.get('numero_tahiti',''));self.rcs.setText(e.get('numero_rcs',''))
        self.pays.setCurrentIndex(max(0,self.pays.findData(cfg['pays'])));self.devise.setText(cfg['devise']);self.precision.setValue(cfg['decimales']);self.langue.setCurrentIndex(max(0,self.langue.findData(cfg['langue'])));self.format_date.setCurrentIndex(max(0,self.format_date.findData(cfg['format_date'])))
        self.nom_taxe.setText(cfg['nom_taxe']);self.mention_exoneree.setText(cfg['mention_sans_taxe']);self.libelle_identifiant.setText(cfg['libelle_identifiant'])
        if e.get('date_debut_activite'):self.start.setDate(qdate_from_iso(e['date_debut_activite']))
        else:self.start.clear()

    def save(self):
        try:
            g.regler_region(self.pays.currentData(),self.devise.text(),self.precision.value(),self.format_date.currentData(),self.langue.currentData(),self.nom_taxe.text(),self.mention_exoneree.text(),self.libelle_identifiant.text())
            db.modifier_entreprise(self.nom.text(),self.responsable.text(),self.tel.text(),self.email.text(),self.adresse.toPlainText(),self.tahiti.text(),self.rcs.text())
            QSettings().setValue("langue",self.langue.currentData())
            self.saved.setText(tr("Enregistré. Les changements de langue et de format seront appliqués à la prochaine ouverture."))
        except Exception as exc:show_error(self,exc)

    def save_start(self):
        try:db.enregistrer_debut_activite(iso_date(self.start));self.saved.setText(tr("Date de début enregistrée."))
        except Exception as exc:show_error(self,exc)


class RepriseMonthDialog(FormDialog):
    def __init__(self,year,month,data=None,parent=None):
        super().__init__(f"Reprise · {MOIS[month-1]} {year}",parent);data=data or {};self.rec=QLineEdit(money_text(data.get('recettes_centiemes')));self.dep=QLineEdit(money_text(data.get('depenses_centiemes')));self.checked=QCheckBox(tr("Montants vérifiés"));self.checked.setChecked(bool(data.get('verifie')));self.form.addRow(tr("Recettes · " + regional.configuration()["devise"] + ""),self.rec);self.form.addRow(tr("Dépenses · " + regional.configuration()["devise"] + ""),self.dep);self.form.addRow("",self.checked)
    def values(self):return self.rec.text(),self.dep.text(),self.checked.isChecked()


class RecoveryPage(Page):
    def __init__(self,parent=None):
        super().__init__(tr("Historique"),tr("Reprise de données"),tr("Ajoutez les montants des mois précédents une seule fois."),parent)
        top=QHBoxLayout();self.year=QSpinBox();self.year.setRange(1900,9999);self.year.setValue(g.aujourd_hui().year);self.year.valueChanged.connect(self.refresh);top.addWidget(QLabel(tr("Année")));top.addWidget(self.year);top.addStretch();self.layout.addLayout(top)
        settings=QGroupBox(tr("Période et situation antérieure"));f=QFormLayout(settings);self.end=make_date();self.ca_n1=QLineEdit();f.addRow(tr("Date de fin de reprise"),self.end);f.addRow(tr("CA année N−1 · " + regional.configuration()["devise"] + ""),self.ca_n1);self.layout.addWidget(settings)
        buttons=QHBoxLayout();buttons.addWidget(button(tr("Enregistrer la période"),self.save_end));buttons.addWidget(button(tr("Enregistrer CA N−1"),self.save_ca,secondary=True));buttons.addWidget(button(tr("Taxe et CA"),lambda:self.navigate.emit("fiscalite"),secondary=True));buttons.addStretch();self.layout.addLayout(buttons)
        self.status=QLabel();self.status.setWordWrap(True);self.layout.addWidget(self.status)
        self.table=QTableWidget();configure_table(self.table,[tr("Mois"),tr("Recettes"),tr("Dépenses"),tr("Vérifié")]);self.table.doubleClicked.connect(self.edit_month);self.layout.addWidget(self.table)
        self.layout.addWidget(QLabel(tr("Double-cliquez un mois pour saisir ou corriger ses montants.")))

    def refresh(self,*_):
        year=self.year.value();f=db.obtenir_fiscalite_annuelle(year) or {};self.end.setDate(qdate_from_iso(f.get('date_fin_reprise')));self.ca_n1.setText(money_text(f.get('ca_n1_centiemes')))
        data={x['mois']:x for x in db.lister_reprise_mensuelle(year)};rows=[];ids=[]
        for m in range(1,13):
            x=data.get(m,{});rows.append([MOIS[m-1],fcfp(x.get('recettes_centiemes')),fcfp(x.get('depenses_centiemes')),tr("Oui") if x.get('verifie') else tr("Non")]);ids.append(m)
        fill_table(self.table,rows,ids);ctrl=db.verifier_reprise(year);self.status.setText(ctrl['message']+(f" Mois à compléter : {', '.join(MOIS[m-1] for m in ctrl['mois_manquants'])}." if ctrl.get('mois_manquants') else ""))

    def edit_month(self):
        month=selected_id(self.table)
        if month is None:return
        year=self.year.value();current=next((x for x in db.lister_reprise_mensuelle(year) if x['mois']==month),None);d=RepriseMonthDialog(year,month,current,self)
        if d.exec():
            try:db.enregistrer_reprise_mensuelle(year,month,*d.values());self.refresh()
            except Exception as exc:show_error(self,exc)
    def save_end(self):
        try:db.enregistrer_fin_reprise(self.year.value(),iso_date(self.end));self.refresh()
        except Exception as exc:show_error(self,exc)
    def save_ca(self):
        try:db.enregistrer_ca_n1(self.year.value(),self.ca_n1.text());self.refresh()
        except Exception as exc:show_error(self,exc)


class FiscalPage(Page):
    def __init__(self, parent=None):
        super().__init__(tr("Votre activité"), tr("Taxe et chiffre d’affaires"), tr("Choisissez la Taxe utilisée pour vos documents."), parent)
        card = QGroupBox(tr("Choix pour l’année"))
        form = QFormLayout(card)
        self.year = QSpinBox()
        self.year.setRange(1900, 9999)
        self.year.setValue(g.aujourd_hui().year)
        self.year.valueChanged.connect(self.refresh)
        self.regime = QComboBox()
        self.regime.addItem(tr("Sans choix · aucune Taxe calculée"), "")
        self.regime.addItem(tr("Sans taxe calculée"), "franchise")
        self.regime.addItem(tr("Taxe applicable"), "reel")
        row = QHBoxLayout()
        row.addWidget(self.regime, 1)
        row.addWidget(button(tr("Effacer le choix"), lambda: self.regime.setCurrentIndex(0), secondary=True))
        self.ca = QLineEdit()
        self.ca.setPlaceholderText(tr("Facultatif"))
        form.addRow(tr("Année"), self.year)
        form.addRow(tr("Taxe"), row)
        form.addRow(tr("CA annuel · " + regional.configuration()["devise"] + ""), self.ca)
        self.layout.addWidget(card)
        self.layout.addWidget(button(tr("Enregistrer"), self.save))
        self.proposal = QLabel()
        self.proposal.setWordWrap(True)
        self.layout.addWidget(self.proposal)
        self.local_note = QLabel("Profil Polynésie française : au-delà de 10 000 000 XPF, déclarez le dépassement à la DICP. Ce rappel ne bloque aucune opération.")
        self.local_note.setWordWrap(True);self.layout.addWidget(self.local_note)
        self.local_button=button(tr("Informations DICP"),lambda:QDesktopServices.openUrl(QUrl("https://www.service-public.pf/dicp/")),secondary=True)
        self.layout.addWidget(self.local_button)
        self.layout.addStretch()

    def refresh(self, *_):
        f = db.obtenir_fiscalite_annuelle(self.year.value()) or {}
        self.regime.setCurrentIndex(max(0, self.regime.findData(f.get('regime_confirme', ''))))
        self.ca.setText(money_text(f.get('ca_annee_centiemes')))
        self.proposal.setText(g.rappel_seuil_ca(self.year.value()))
        local=regional.configuration()['pays']=='PF' and regional.configuration()['devise']=='XPF'
        self.local_note.setVisible(local);self.local_button.setVisible(local)

    def save(self):
        try:
            g.confirmer_fiscalite(self.year.value(), self.regime.currentData(), ca=self.ca.text())
            self.refresh()
            show_info(self, tr("Enregistré."))
        except Exception as exc:
            show_error(self, exc)


class SettingsPage(Page):
    def __init__(self,parent=None):
        super().__init__(tr("Préférences"),tr("Réglages"),tr("Personnalisez vos documents et votre suivi."),parent)
        docs=QGroupBox(tr("Documents"));f=QFormLayout(docs);self.validity=QSpinBox();self.validity.setRange(1,365);self.terms=QTextEdit();self.payment=QTextEdit();self.note=QTextEdit();
        explication = QLabel(tr("Conditions facultatives : affichées en bas des devis et factures. Les changements s’appliquent aussi aux documents existants lors du prochain aperçu ou export PDF. Laissez un champ vide pour ne pas l’afficher."))
        explication.setWordWrap(True);f.addRow(explication)
        for field in (self.terms,self.payment,self.note):
            field.setFixedHeight(90);field.setPlaceholderText(tr("Facultatif — texte à afficher sur les documents"))
        f.addRow(tr("Validité des devis · jours"),self.validity);f.addRow(tr("Conditions de vente (facultatif)"),self.terms);f.addRow(tr("Règlement (facultatif)"),self.payment);f.addRow(tr("Mentions complémentaires"),self.note);self.layout.addWidget(docs)
        tva=QGroupBox(tr("Taxe et trésorerie"));tf=QFormLayout(tva);self.period=QComboBox();self.period.addItem(tr("Non renseignée / sans déclaration"),"");self.period.addItem("Mensuelle","mensuelle");self.period.addItem("Trimestrielle","trimestrielle");self.balance_date=DateInput(optional=True);self.balance=QLineEdit();tf.addRow(tr("Fréquence des déclarations"),self.period);tf.addRow(tr("Date du solde de départ · " + regional.FORMATS[regional.configuration()["format_date"]]),self.balance_date);tf.addRow(tr("Solde banque + caisse · " + regional.configuration()["devise"] + ""),self.balance);self.layout.addWidget(tva);self.layout.addWidget(button(tr("Enregistrer les réglages"),self.save))
        actions=QHBoxLayout();actions.addWidget(button(tr("Sauvegarder la base"),lambda:backup_database(self)));actions.addWidget(button(tr("Exporter le journal CSV"),lambda:export_journal_csv(self),secondary=True));actions.addStretch();self.layout.addLayout(actions);self.layout.addStretch()
    def refresh(self):
        e=db.obtenir_entreprise() or {};self.validity.setValue(e.get('validite_devis_jours',30));self.terms.setPlainText(e.get('conditions_vente',''));self.payment.setPlainText(e.get('conditions_reglement',''));self.note.setPlainText(e.get('mention_complementaire',''));self.period.setCurrentIndex(max(0,self.period.findData(e.get('periodicite_tva',''))));self.balance_date.setDate(qdate_from_iso(e['date_solde_depart'])) if e.get('date_solde_depart') else self.balance_date.clear();self.balance.setText(money_text(e.get('solde_depart_centiemes',0)))
    def save(self):
        try:g.regler_entreprise(self.validity.value(),self.terms.toPlainText(),self.payment.toPlainText(),self.note.toPlainText(),self.period.currentData(),self.balance.text(),iso_date(self.balance_date));self.refresh();show_info(self,tr("Réglages enregistrés."))
        except Exception as exc:show_error(self,exc)

def demander_verification(parent):
    fenetre = parent.window()
    fenetre.verifier_updates(manuel=True)

class UpdatesPage(Page):
    def __init__(self, parent=None):
        super().__init__("Patenteasy", tr("Mises à jour"), f"Version installée : {VERSION}", parent)
        texte = tr("Recherche sécurisée des versions disponibles. L’installation se fait avec votre accord.") if est_admin(self) else tr("Vous serez informé des nouvelles versions. Seul l’administrateur peut les installer.")
        label=QLabel(texte);label.setWordWrap(True);self.layout.addWidget(label)
        self.layout.addWidget(button(tr("Vérifier les mises à jour"), lambda: demander_verification(self)))
        self.layout.addStretch()


class HelpPage(Page):
    def __init__(self,parent=None):
        super().__init__("Patenteasy",tr("Aide et contact"),tr("Logiciel libre · GNU GPL v3+ · données conservées localement."),parent)
        intro=QGroupBox(tr("Premiers pas"));v=QVBoxLayout(intro);text=QLabel(tr("1. Renseignez votre entreprise, votre devise et vos formats.\n2. Choisissez le calcul des taxes et vos préférences.\n3. Ajoutez clients et catalogue.\n4. Créez un devis et vérifiez son aperçu PDF.\n5. Finalisez le devis ; après acceptation, créez la facture et enregistrez les paiements."));text.setWordWrap(True);v.addWidget(text);self.layout.addWidget(intro)
        limits=QGroupBox(tr("Points importants"));lv=QVBoxLayout(limits);lbl=QLabel(tr("Taxe : choisissez le calcul souhaité dans Taxe et CA.\nStock : ajoutez vous-même les entrées et sorties.\nTrésorerie : renseignez le solde de départ et toutes les opérations.\nWindows et Android : les versions gratuites ne se synchronisent pas."));lbl.setWordWrap(True);lv.addWidget(lbl);self.layout.addWidget(limits)
        self.layout.addWidget(button(tr("Recevoir les nouveautés de ska_987"), lambda: NewsletterDialog(self).exec(), secondary=True))
        self.layout.addWidget(button(tr("Participer à l’amélioration"), self.participer, secondary=True))
        self.layout.addWidget(button(tr("Signaler un problème"), self.signaler, secondary=True))
        bar=QHBoxLayout();bar.addWidget(button(tr("Contacter le support"),lambda:QDesktopServices.openUrl(QUrl('mailto:sav.centreprotech@proton.me'))));local=button("DICP",lambda:QDesktopServices.openUrl(QUrl('https://www.service-public.pf/dicp/')),secondary=True);local.setVisible(regional.configuration()["pays"]=="PF");bar.addWidget(local);bar.addWidget(button(tr("Licence GNU GPL v3"),lambda:QDesktopServices.openUrl(QUrl('https://www.gnu.org/licenses/gpl-3.0.html')),secondary=True));bar.addStretch();self.layout.addLayout(bar);self.layout.addStretch()

    def participer(self):
        from interface_comptes import ParticipationDialog
        ParticipationDialog(self).exec()

    def signaler(self):
        from urllib.parse import urlencode
        texte=f"Patenteasy {VERSION} — Windows\nDécrivez le problème et les étapes pour le reproduire.\nNe joignez ni base de données, ni mot de passe, ni données de clients."
        if QMessageBox.question(self,"Rapport de problème",texte+"\n\nOuvrir ce brouillon dans votre messagerie ?",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl('mailto:sav.centreprotech@proton.me?'+urlencode({'subject':'Problème Patenteasy '+VERSION,'body':texte})))


class CreationAdminDialog(QDialog):
    def __init__(self, comptes, parent=None):
        super().__init__(parent)
        self.comptes = comptes
        self.compte = None

        self.setWindowTitle(tr("Bienvenue dans Patenteasy"))
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)

        texte = QLabel(
            "Créez votre compte administrateur.\n"
            "Il reste sur cet appareil."
        )
        texte.setWordWrap(True)
        layout.addWidget(texte)

        formulaire = QFormLayout()

        self.identifiant = QLineEdit()
        self.identifiant.setMaxLength(40)
        self.identifiant.setPlaceholderText(tr("Exemple : admin"))

        self.mot_de_passe = QLineEdit()
        self.mot_de_passe.setMaxLength(256)
        self.mot_de_passe.setEchoMode(QLineEdit.EchoMode.Password)
        self.mot_de_passe.setPlaceholderText(
            tr("Au moins 12 caractères")
        )

        self.confirmation = QLineEdit()
        self.confirmation.setMaxLength(256)
        self.confirmation.setEchoMode(QLineEdit.EchoMode.Password)

        formulaire.addRow(tr("Identifiant"), self.identifiant)
        formulaire.addRow(tr("Mot de passe"), self.mot_de_passe)
        formulaire.addRow(tr("Confirmer"), self.confirmation)
        layout.addLayout(formulaire)

        self.erreur = QLabel()
        self.erreur.setWordWrap(True)
        layout.addWidget(self.erreur)

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        boutons.button(
            QDialogButtonBox.StandardButton.Ok
        ).setText(tr("Créer mon compte"))
        boutons.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText(tr("Quitter"))

        boutons.accepted.connect(self.creer)
        boutons.rejected.connect(self.reject)
        layout.addWidget(boutons)
        layout.addWidget(button(tr("Récupérer une sauvegarde"),self.restaurer,secondary=True))

    def restaurer(self):
        from recuperation_ui import RecuperationDialog
        dialog=RecuperationDialog(self.comptes,self)
        if dialog.exec():self.compte=dialog.compte;self.accept()

    def creer(self):
        mot_de_passe = self.mot_de_passe.text()

        if mot_de_passe != self.confirmation.text():
            self.erreur.setText(
                tr("Les deux mots de passe sont différents.")
            )
            return

        try:
            self.compte = self.comptes.creer_premier_admin(
                self.identifiant.text(), mot_de_passe
            )
        except ValueError as erreur:
            self.erreur.setText(str(erreur))
            return
        except Exception:
            self.erreur.setText(
                tr("Le compte n’a pas pu être enregistré.")
            )
            return

        self.mot_de_passe.clear()
        self.confirmation.clear()
        self.accept()


class ConnexionDialog(QDialog):
    def __init__(self, comptes, parent=None):
        super().__init__(parent)
        self.comptes = comptes
        self.compte = None

        self.setWindowTitle(tr("Connexion à Patenteasy"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        formulaire = QFormLayout()

        self.identifiant = QLineEdit()
        self.identifiant.setMaxLength(40)

        self.mot_de_passe = QLineEdit()
        self.mot_de_passe.setMaxLength(256)
        self.mot_de_passe.setEchoMode(QLineEdit.EchoMode.Password)

        formulaire.addRow(tr("Identifiant"), self.identifiant)
        formulaire.addRow(tr("Mot de passe"), self.mot_de_passe)
        layout.addLayout(formulaire)

        self.erreur = QLabel()
        self.erreur.setWordWrap(True)
        layout.addWidget(self.erreur)

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        boutons.button(
            QDialogButtonBox.StandardButton.Ok
        ).setText(tr("Se connecter"))
        boutons.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText(tr("Quitter"))

        layout.addWidget(button(tr("Accès administrateur oublié"), self.recuperer, secondary=True))
        boutons.accepted.connect(self.connecter)
        boutons.rejected.connect(self.reject)
        layout.addWidget(boutons)

    def recuperer(self):
        if not self.comptes.coffre.metadata.exists():
            show_info(self,"La récupération sera disponible après migration du compte administrateur.");return
        from interface_comptes import SecretDialog
        d=SecretDialog(tr("Récupération administrateur"),self)
        d.identifiant.setPlaceholderText(tr("Code de récupération"))
        if d.exec():
            try:
                ident=self.comptes.recuperer(d.identifiant.text(),d.secret.text())
                self.identifiant.setText(ident)
                show_info(self,"Mot de passe rétabli. Connectez-vous ; un nouveau code de récupération vous sera présenté.")
            except Exception as e:show_error(self,e)

    def connecter(self):
        try:
            self.compte = self.comptes.authentifier(
                self.identifiant.text(),
                self.mot_de_passe.text()
            )
        except Exception:
            self.erreur.setText(
                tr("La connexion n’a pas pu être vérifiée.")
            )
            return

        self.mot_de_passe.clear()

        if self.compte is None:
            self.erreur.setText(
                "Connexion refusée. Vérifiez vos identifiants.\n"
                "Après plusieurs erreurs, attendez une minute."
            )
            return

        self.accept()

def compte_de(widget):
    courant = widget

    while courant is not None:
        compte = getattr(courant, "compte_connecte", None)
        if compte is not None:
            return compte
        courant = courant.parentWidget()

    return {}


def est_admin(widget):
    return compte_de(widget).get("role") == "admin"


def exiger_admin(widget):
    if est_admin(widget):
        return True

    QMessageBox.warning(
        widget,
        tr("Accès réservé"),
        "Cette action est réservée à l’administrateur."
    )
    return False

class AccueilUtilisateurPage(Page):
    def __init__(self, parent=None):
        super().__init__(
            "Patenteasy",
            tr("Mon espace de travail"),
            tr("Clients, devis et règlements."),
            parent
        )

        actions = [
            (tr("Clients"), "clients"),
            (tr("Devis"), "devis"),
            (tr("Encaissements clients"), "factures"),
            (tr("Règlements fournisseurs"), "journal"),
        ]

        for texte, destination in actions:
            self.layout.addWidget(button(
                texte,
                lambda destination=destination:
                    self.navigate.emit(destination)
            ))

        self.layout.addStretch()


class ReglementsFournisseursPage(Page):
    def __init__(self, parent=None):
        super().__init__(
            tr("Opérations courantes"),
            tr("Règlements fournisseurs"),
            tr("Enregistrez un règlement effectué."),
            parent
        )

        self.layout.addWidget(button(
            tr("Enregistrer un règlement"),
            self.ajouter_reglement
        ))
        self.layout.addStretch()

    def ajouter_reglement(self):
        if compte_de(self).get("role") not in (
            "admin", "utilisateur"
        ):
            return

        dialogue = OperationDialog(parent=self)
        dialogue.setWindowTitle(tr("Règlement fournisseur"))
        dialogue.type.setCurrentIndex(
            dialogue.type.findData("depense")
        )
        dialogue.type.setEnabled(False)
        dialogue.libelle.setPlaceholderText(
            tr("Fournisseur et référence de facture")
        )

        if dialogue.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            jour, libelle, _, montant = dialogue.values()
            db.ajouter_operation(
                jour, libelle, "depense", montant
            )
            self.window().gestion_comptes.tracer(tr("Règlement fournisseur"))
            QMessageBox.information(
                self,
                tr("Règlement enregistré"),
                "Le règlement fournisseur a été enregistré."
            )
        except Exception as erreur:
            show_error(self, erreur)


class MainWindow(QMainWindow):
    def __init__(self, compte_connecte, gestion_comptes):
        super().__init__()

        self.compte_connecte = dict(compte_connecte)
        self.gestion_comptes = gestion_comptes
        from sauvegardes import GestionSauvegardes
        self.sauvegardes = GestionSauvegardes(gestion_comptes)
        from beta_fonctions import ServicesBeta
        self.beta = ServicesBeta(gestion_comptes,self.sauvegardes)
        self.verrouille = False
        self.derniere_activite = __import__('time').monotonic()
        self.timer_session = QTimer(self)
        self.timer_session.setInterval(30_000)
        self.timer_session.timeout.connect(self.surveiller_session)
        self.timer_session.start()
        self.timer_sauvegardes = QTimer(self)
        self.timer_sauvegardes.setInterval(300_000)
        self.timer_sauvegardes.timeout.connect(self.sauvegarde_auto)
        self.timer_sauvegardes.start()
        QApplication.instance().installEventFilter(self)

        self.pages_autorisees = (
            None if est_admin(self) else {
                "dashboard", "clients", "devis",
                "factures", "journal", "stock", "help", "preferences", "updates"
            }
        )
        self.resultats_updates = Queue()
        self.verification_updates_en_cours = False
        self.verification_updates_manuelle = False
        self.update_disponible = None

        self.timer_updates = QTimer(self)
        self.timer_updates.setInterval(250)
        self.timer_updates.timeout.connect(self.recevoir_updates)
        role = tr("Administrateur") if est_admin(self) else tr("Utilisateur")
        self.setWindowTitle(f"Patenteasy {VERSION} — {self.compte_connecte['identifiant']} · {role}")
        icon = ROOT / "static" / "patenteasy.ico"
        if icon.exists(): self.setWindowIcon(QIcon(str(icon)))
        self.resize(1320, 860)
        self.setMinimumSize(780, 520)
        central=QWidget();self.setCentralWidget(central);outer=QHBoxLayout(central);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        side=QFrame();side.setObjectName("sidebar");side.setFixedWidth(230);sl=QVBoxLayout(side);sl.setContentsMargins(22,26,22,20);brand=QLabel("Patenteasy.");brand.setObjectName("brand");tag=QLabel(tr("Votre activité, simplement."));tag.setObjectName("tagline");sl.addWidget(brand);sl.addWidget(tag);sl.addSpacing(24)
        self.nav=QListWidget();self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.nav.setObjectName("navigation");sl.addWidget(self.nav,1);foot=QLabel("Développé par ska_987\nLogiciel libre · GNU GPL v3+");foot.setObjectName("sidebarFoot");sl.addWidget(foot);outer.addWidget(side)
        workspace=QWidget();wl=QVBoxLayout(workspace);wl.setContentsMargins(0,0,0,0);wl.setSpacing(0);top=QFrame();top.setObjectName("topbar");tl=QHBoxLayout(top);tl.setContentsMargins(28,13,28,13);a=QLabel(tr("Gestion de votre activité"));a.setObjectName("topbarText");b=QLabel("" + regional.configuration()["devise"] + " · Sur cet ordinateur");b.setObjectName("topbarText");tl.addWidget(a);tl.addStretch();tl.addWidget(b);wl.addWidget(top)
        self.alerte_sauvegarde=QPushButton();self.alerte_sauvegarde.setStyleSheet("background:#fff4df;color:#703500;padding:10px;text-align:left;");self.alerte_sauvegarde.clicked.connect(lambda:self.show_page('preferences'));wl.addWidget(self.alerte_sauvegarde)
        self.stack=QStackedWidget();wl.addWidget(self.stack,1);outer.addWidget(workspace,1)
        self.pages={}
        from interface_comptes import ComptesPage, PreferencesPage
        from interface_beta import DemarragePage
        specs=[
            ("dashboard",tr("Tableau de bord"),DashboardPage),("clients",tr("Clients"),ClientsPage),("articles",tr("Catalogue"),ArticlesPage),("devis",tr("Devis"),QuotesPage),("factures",tr("Factures & avoirs"),InvoicesPage),("journal",tr("Recettes & dépenses"),JournalPage),("stock",tr("Stock"),StockPage),("echeances",tr("Échéances"),RemindersPage),("entreprise",tr("Mon entreprise"),CompanyPage),("reprise",tr("Reprise de données"),RecoveryPage),("fiscalite",tr("Taxe et CA"),FiscalPage),("reglages",tr("Réglages"),SettingsPage),("updates",tr("Mises à jour"),UpdatesPage),("help",tr("Aide & contact"),HelpPage),
        ]
        specs.extend([("preferences", tr("Mes préférences"), PreferencesPage)])
        if est_admin(self):
            specs.append(("comptes", tr("Comptes utilisateurs"), ComptesPage))
            specs.append(("demarrage", tr("Bien démarrer"), DemarragePage))
        if not est_admin(self):
            remplacements = {
                "dashboard": AccueilUtilisateurPage,
                "journal": ReglementsFournisseursPage,
            }

            specs = [
                (key, label, remplacements.get(key, cls))
                for key, label, cls in specs
                if key in self.pages_autorisees
            ]

            specs = [
                (
                    key,
                    tr("Règlements fournisseurs")
                    if key == "journal"
                    else tr("Encaissements clients")
                    if key == "factures"
                    else label,
                    cls
                )
                for key, label, cls in specs
            ]
        for key,label,cls in specs:
            item=QListWidgetItem(label);item.setData(Qt.ItemDataRole.UserRole,key);self.nav.addItem(item);page=cls(self);page.navigate.connect(self.show_page);self.pages[key]=page;self.stack.addWidget(page)
        self.nav.currentItemChanged.connect(self._nav_changed)
        self.nav.setCurrentRow(0)
        if est_admin(self) and not (db.obtenir_entreprise() or {}).get("nom"):
            self.show_page("demarrage")
        self.appliquer_theme()
        self.rafraichir_sauvegarde()

    def rafraichir_sauvegarde(self):
        message=self.beta.etat_sauvegarde();self.alerte_sauvegarde.setText(message+" · Ouvrir les réglages");self.alerte_sauvegarde.setVisible(bool(message))

    def verifier_updates(self, manuel=False):
        if self.verification_updates_en_cours:
            if manuel:
                self.verification_updates_manuelle = True
                self.statusBar().showMessage(
                    "Vérification déjà en cours…"
                )
            return

        self.verification_updates_en_cours = True
        self.verification_updates_manuelle = manuel

        if manuel:
            self.statusBar().showMessage(
                "Recherche des mises à jour…"
            )

        file_resultats = self.resultats_updates

        def travail():
            try:
                resultat = verifier_mise_a_jour()
                file_resultats.put((resultat, None))
            except Exception as erreur:
                file_resultats.put((None, erreur))

        self.timer_updates.start()
        Thread(target=travail, daemon=True).start()

    def recevoir_updates(self):
        try:
            resultat, erreur = self.resultats_updates.get_nowait()
        except Empty:
            return

        self.timer_updates.stop()
        self.verification_updates_en_cours = False
        manuel = self.verification_updates_manuelle
        self.verification_updates_manuelle = False
        self.statusBar().clearMessage()

        if erreur is not None:
            if manuel:
                QMessageBox.warning(
                    self,
                    tr("Mises à jour"),
                    "La vérification n’a pas abouti.\n"
                    "Réessayez plus tard. Aucun fichier n’a été installé."
                )
            return

        if not resultat.get("configure"):
            if manuel:
                QMessageBox.information(
                    self,
                    tr("Mises à jour"),
                    "Le service de mise à jour n’est pas configuré."
                )
            return

        if not resultat.get("nouvelle"):
            self.update_disponible = None
            if manuel:
                QMessageBox.information(
                    self,
                    tr("Mises à jour"),
                    "Aucune version plus récente n’est disponible."
                )
            return

        self.update_disponible = resultat

        if not est_admin(self):
            QMessageBox.information(self, "Nouvelle version disponible", "Une nouvelle version est disponible. Contactez votre administrateur pour l’installer.")
            return
        choix = QMessageBox.question(
            self,
            "Nouvelle version disponible",
            "Patenteasy " + resultat["version"] + " est disponible.\n\n"
            "Voulez-vous télécharger cette version ?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if choix == QMessageBox.StandardButton.Yes:
            self.telecharger_update()

    def telecharger_update(self):
        if not exiger_admin(self): return
        if getattr(self, "telechargement_en_cours", False):
            QMessageBox.information(
                self,
                tr("Mises à jour"),
                "Un téléchargement est déjà en cours."
            )
            return

        if not self.update_disponible:
            return

        self.telechargement_en_cours = True
        self.resultats_telechargement = Queue()

        self.timer_telechargement = QTimer(self)
        self.timer_telechargement.setInterval(250)
        self.timer_telechargement.timeout.connect(
            self.recevoir_telechargement
        )

        self.statusBar().showMessage(
            "Téléchargement de la mise à jour…"
        )

        # Copie du résultat dont la signature a été vérifiée.
        version_proposee = dict(self.update_disponible)
        self.version_telechargee = version_proposee
        file_resultats = self.resultats_telechargement
        dossier = db.BASE_DIR / "mises-a-jour"

        def travail():
            try:
                fichier = telecharger_mise_a_jour(
                    version_proposee, dossier
                )
                file_resultats.put((fichier, None))
            except Exception as erreur:
                file_resultats.put((None, erreur))

        self.timer_telechargement.start()
        Thread(target=travail, daemon=True).start()

    def recevoir_telechargement(self):
        try:
            fichier, erreur = (
                self.resultats_telechargement.get_nowait()
            )
        except Empty:
            return

        self.timer_telechargement.stop()
        self.timer_telechargement.deleteLater()
        self.telechargement_en_cours = False
        self.statusBar().clearMessage()

        if erreur is not None:
            QMessageBox.warning(
                self,
                "Téléchargement interrompu",
                "La mise à jour n’a pas pu être téléchargée "
                "et vérifiée.\n\n"
                "Aucun programme n’a été lancé. "
                "Vous pouvez réessayer plus tard."
            )
            return

        self.fichier_update = fichier

        choix = QMessageBox.question(
            self,
            "Mise à jour prête",
            "Le téléchargement est vérifié.\n\n"
            "Installer maintenant ? Une sauvegarde sera créée, "
            "puis Patenteasy se fermera.",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if choix == QMessageBox.StandardButton.Yes:
            self.installer_update()

    def installer_update(self):
        if not exiger_admin(self): return
        if os.name != "nt":
            QMessageBox.information(
                self,
                tr("Mises à jour"),
                "Cet installateur est destiné à Windows."
            )
            return

        try:
            fichier = Path(self.fichier_update)
            version_proposee = dict(self.version_telechargee)

            if version_proposee.get("format") != "exe":
                raise RuntimeError(
                    "Cette version nécessite une installation manuelle."
                )

            # Dans la version PyInstaller, le même exécutable possède un
            # mode d'assistance dédié. Il est lancé avant la fermeture de
            # l'application principale, attend sa fin, revérifie le fichier,
            # puis démarre l'installateur Windows.
            if getattr(sys, "frozen", False):
                commande = [
                    str(Path(sys.executable).resolve()),
                    "--install-update",
                    str(os.getpid()),
                    str(fichier.resolve()),
                    version_proposee["sha256"],
                    str(version_proposee["taille"]),
                ]
                repertoire_travail = str(
                    Path(sys.executable).resolve().parent
                )
            else:
                # Mode développeur : le script reste directement exécutable
                # avec Python sans dépendre du paquet PyInstaller.
                assistant = ROOT / "installer_mise_a_jour.py"
                if not assistant.is_file():
                    raise FileNotFoundError(
                        "Le programme d’installation de mise à jour manque."
                    )
                lanceur = Path(sys.executable).with_name("pythonw.exe")
                if not lanceur.is_file():
                    lanceur = Path(sys.executable)
                commande = [
                    str(lanceur),
                    str(assistant),
                    str(os.getpid()),
                    str(fichier.resolve()),
                    version_proposee["sha256"],
                    str(version_proposee["taille"]),
                ]
                repertoire_travail = str(ROOT)

            self.sauvegardes.creer("avant-mise-a-jour")
            self.gestion_comptes.tracer("Installation mise à jour", version_proposee["version"])

            subprocess.Popen(
                commande,
                cwd=repertoire_travail,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        except Exception as erreur:
            QMessageBox.warning(
                self,
                "Installation annulée",
                str(erreur)
            )
            return

        QApplication.instance().quit()

    def est_admin(self):
        return self.compte_connecte.get("role") == "admin"

    def exiger_admin(self):
        if self.est_admin():
            return True

        QMessageBox.warning(
            self,
            tr("Accès réservé"),
            "Cette action est réservée à l’administrateur."
        )
        return False

    def appliquer_theme(self):
        from PySide6.QtGui import QColor
        p=self.gestion_comptes.preferences()
        style=APP_QSS
        if p.get("theme")=="Sombre":
            for a,b in {"#f4f6f9":"#171d28","#182336":"#e5eaf2","background: white":"background: #232c3a","background: #fff":"background: #232c3a","#dce3ed":"#455269","#65748a":"#bbc6d7","#eef2f7":"#2c384b"}.items():style=style.replace(a,b)
            style+="\nQLineEdit,QTextEdit,QComboBox,QSpinBox,QDateEdit,QTableWidget {background:#232c3a;color:#e5eaf2;} QHeaderView::section {background:#2c384b;color:#e5eaf2;} QTableWidget {alternate-background-color:#293344;selection-background-color:#37577a;selection-color:#ffffff;} QTableWidget::item:selected {background:#37577a;color:#ffffff;} QLineEdit,QTextEdit,QComboBox,QSpinBox,QDateEdit {selection-background-color:#37577a;selection-color:#ffffff;}"
        if p.get("theme")=="Personnalisé":
            c=QColor(p.get("accent","#2563eb"))
            if c.isValid():
                couleur=c.name();texte="#182336" if c.lightnessF()>0.6 else "white"
                style+=f"\nQPushButton {{background:{couleur};color:{texte};}} QPushButton[secondary=\"true\"] {{background:#e8eef8;color:#182336;}} QPushButton[danger=\"true\"] {{background:#b91c1c;color:white;}}"
        QApplication.instance().setStyleSheet(style)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.MouseButtonPress,QEvent.KeyPress,QEvent.Wheel):
            self.derniere_activite=__import__('time').monotonic()
        return super().eventFilter(obj,event)

    def surveiller_session(self):
        delai=self.gestion_comptes.preferences().get("verrouillage",15)*60
        if not self.verrouille and __import__('time').monotonic()-self.derniere_activite>=delai:self.verrouiller()

    def verrouiller(self):
        if self.verrouille:return
        if getattr(self,"telechargement_en_cours",False):
            self.statusBar().showMessage("Attendez la fin du téléchargement avant de changer de session.");return
        if QApplication.activeModalWidget() is not None:
            # Ferme les formulaires ouverts avant de cacher l’espace de travail.
            QApplication.activeModalWidget().reject()
        self.timer_updates.stop()
        self.verrouille=True;self.hide()
        app=QApplication.instance();app.setQuitOnLastWindowClosed(False)
        self.gestion_comptes.coffre.verrouiller()
        d=ConnexionDialog(self.gestion_comptes)
        if d.exec()!=QDialog.Accepted:app.quit();return
        self.compte_connecte=d.compte
        # Reconstruit les pages : aucun écran de l’ancien rôle n’est réutilisé.
        nouvelle=MainWindow(d.compte,self.gestion_comptes)
        app.fenetre_principale=nouvelle;nouvelle.show();app.setQuitOnLastWindowClosed(True)
        self.timer_session.stop();self.timer_sauvegardes.stop();self.timer_updates.stop()
        self.deleteLater()

    def sauvegarde_auto(self):
        if self.verrouille:return
        try:self.sauvegardes.automatique()
        except Exception:
            from coffre import ecrire_json
            m=self.gestion_comptes.coffre.lire();m['sauvegardes']['erreur']='Sauvegarde automatique impossible.';ecrire_json(self.gestion_comptes.coffre.metadata,m)
        self.rafraichir_sauvegarde()

    def _nav_changed(self,current,previous):
        if current:self.show_page(current.data(Qt.ItemDataRole.UserRole),sync_nav=False)

    def show_page(self,key:str,sync_nav=True):
        if self.pages_autorisees is not None and key not in self.pages_autorisees:
            show_info(self, "Page réservée à l’administrateur.")
            return
        page=self.pages.get(key)
        if not page:return
        try:page.refresh();self.rafraichir_sauvegarde()
        except Exception as exc:show_error(self,exc)
        self.stack.setCurrentWidget(page)
        if sync_nav:
            for row in range(self.nav.count()):
                if self.nav.item(row).data(Qt.ItemDataRole.UserRole)==key:
                    self.nav.setCurrentRow(row);break


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    import localisation
    localisation.ACTIVE=QSettings("ska_987","Patenteasy").value("langue","fr")
    app.setApplicationName("Patenteasy")
    app.setOrganizationName("ska_987")
    app.setStyleSheet(APP_QSS)

    # La fermeture du dialogue de connexion ne doit pas
    # terminer Qt avant l’ouverture de la fenêtre principale.
    app.setQuitOnLastWindowClosed(False)

    comptes = GestionComptes()
    comptes.initialiser()

    if comptes.premier_compte_requis():
        dialogue = CreationAdminDialog(comptes)
    else:
        dialogue = ConnexionDialog(comptes)

    if dialogue.exec() != QDialog.DialogCode.Accepted:
        return 0

    compte_connecte = dialogue.compte
    g.migrer()
    import localisation
    localisation.ACTIVE=regional.configuration()['langue']
    MOIS[:]=[tr(m) for m in MOIS]
    comptes.tracer(tr("Connexion"))
    dialogue.deleteLater()

    window = MainWindow(compte_connecte, comptes)
    window.show()
    app.fenetre_principale = window

    app.setQuitOnLastWindowClosed(True)

    def apres_ouverture():
        from interface_comptes import ParticipationDialog
        if est_admin(window) and not (db.obtenir_entreprise() or {}).get("nom"):
            window.show_page("entreprise")
        if comptes.coffre.code_recuperation:
            d=QDialog(window);d.setWindowTitle(tr("Votre code de récupération"));v=QVBoxLayout(d)
            l=QLabel(tr("Conservez ce code hors de l’ordinateur. Il permet de rétablir votre accès administrateur. Le développeur n’en possède aucune copie."));l.setWordWrap(True);v.addWidget(l)
            champ=QLineEdit(comptes.coffre.code_recuperation);champ.setReadOnly(True);v.addWidget(champ)
            v.addWidget(button(tr("Copier"),lambda:QApplication.clipboard().setText(champ.text()),secondary=True))
            v.addWidget(button(tr("J’ai conservé mon code"),d.accept));d.exec();comptes.coffre.code_recuperation=None
        if est_admin(window) and not window.sauvegardes.configuration()["dossier"]:
            QMessageBox.information(window,tr("Sauvegardes"),"Choisissez un dossier pour vos sauvegardes chiffrées. Vous pourrez le modifier dans Mes préférences.")
            window.pages["preferences"].dossier()
        m=comptes.coffre.lire()
        if est_admin(window) and not m.get("participation_proposee"):
            ParticipationDialog(window).exec();m=comptes.coffre.lire();m["participation_proposee"]=True
            from coffre import ecrire_json
            ecrire_json(comptes.coffre.metadata,m)
        prefs=comptes.preferences()
        if prefs.get('version_vue')!=VERSION:
            from interface_beta import nouveautes
            nouveautes(window);prefs['version_vue']=VERSION;comptes.enregistrer_preferences(prefs)
        window.sauvegarde_auto()
        window.verifier_updates()

    QTimer.singleShot(0, apres_ouverture)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
