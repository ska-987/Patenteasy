# SPDX-License-Identifier: GPL-3.0-or-later
"""Un emplacement mémorisé pour tous les devis, factures et avoirs PDF."""
from pathlib import Path
from PySide6.QtCore import QSettings, QStandardPaths, QUrl, QSaveFile, QIODevice
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox
from localisation import tr


def preferences():
    return QSettings('ska_987', 'Patenteasy')


def choisir_dossier(parent):
    settings = preferences()
    memorise = settings.value('exports_pdf/dossier', '', type=str)
    if memorise and Path(memorise).is_dir():
        return Path(memorise)
    bureau = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
    message = QMessageBox(parent)
    message.setWindowTitle(tr('Vos devis et factures PDF'))
    message.setText(tr('Créer un dossier Patenteasy sur le Bureau pour retrouver rapidement vos devis et factures ?'))
    message.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
    message.setDefaultButton(QMessageBox.StandardButton.Yes)
    message.button(QMessageBox.StandardButton.Yes).setText(tr('Créer sur le Bureau'))
    message.button(QMessageBox.StandardButton.No).setText(tr('Choisir un autre dossier'))
    message.button(QMessageBox.StandardButton.Cancel).setText(tr('Annuler'))
    choix = message.exec()
    if choix == QMessageBox.StandardButton.Cancel:
        return None
    if choix == QMessageBox.StandardButton.Yes and bureau:
        dossier = Path(bureau) / 'Patenteasy'
        dossier.mkdir(parents=True, exist_ok=True)
    else:
        nom = QFileDialog.getExistingDirectory(parent, tr('Dossier des devis et factures PDF'), bureau)
        if not nom:
            return None
        dossier = Path(nom)
    settings.setValue('exports_pdf/dossier', str(dossier))
    settings.sync()
    return dossier


def enregistrer(parent, contenu, nom):
    dossier = choisir_dossier(parent)
    if dossier is None:
        return None
    dialog = QFileDialog(parent, tr('Enregistrer le PDF'), str(dossier / Path(nom).name), 'Document PDF (*.pdf)')
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    dialog.setDefaultSuffix('pdf')
    if not dialog.exec():
        return None
    destination = Path(dialog.selectedFiles()[0])
    fichier = QSaveFile(str(destination))
    if not fichier.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(fichier.errorString())
    if fichier.write(contenu) != len(contenu):
        fichier.cancelWriting()
        raise OSError(fichier.errorString())
    if not fichier.commit():
        raise OSError(fichier.errorString())
    settings = preferences()
    settings.setValue('exports_pdf/dossier', str(destination.parent))
    settings.sync()
    return destination


def ouvrir_dossier(parent):
    dossier = choisir_dossier(parent)
    if dossier is None:
        return False
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(dossier))):
        raise OSError(tr('Le dossier PDF ne peut pas être ouvert.'))
    return True
