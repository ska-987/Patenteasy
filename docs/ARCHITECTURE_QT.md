# Architecture PySide6 / Qt

La refonte bureau remplace l'ancien lancement Windows basé sur WebView2 par une vraie interface native PySide6/Qt.

## Principaux éléments

- `qt_app.py` : interface PySide6 native, navigation et pages bureau ;
- `application_windows.py` : lancement Windows sans serveur localhost ni WebView2 ;
- `lancer.py` : ouverture directe de l'application Qt depuis les sources ;
- `database.py` : accès aux données locales ;
- `gestion.py` : logique métier des documents, paiements, avoirs et stock ;
- `pdf_documents.py` : génération des documents PDF.

## Développement sous Windows

1. Exécuter `INSTALLER.cmd`.
2. Exécuter `LANCER.cmd` ou `.venv\Scripts\pythonw.exe lancer.py`.
3. Pour compiler l'application Windows, utiliser `distribution\COMPILER_WINDOWS.cmd`.

La base utilisateur installée reste dans `%LOCALAPPDATA%\PatenteasyLocal\data\patenteasy.db`.
