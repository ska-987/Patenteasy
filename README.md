# Patenteasy

**Version Windows :** 0.4.0
**Version Android :** 0.3.7

Application de gestion locale pour indépendants, artisans et petites entreprises.

**Développeur :** ska_987  
**Plateformes :** Windows 64 bits et Android 8+  
**Licence :** GNU GPL v3 ou ultérieure

## Éditions

Patenteasy existe en deux éditions locales indépendantes :

- **Windows 0.4.0** : interface de bureau native PySide6/Qt, sans Edge/WebView2 et sans serveur HTTP local ;
- **Android 0.3.7** : application hors ligne avec stockage local sur le téléphone.

Il n'y a pas de synchronisation automatique entre Windows et Android.

## Fonctions principales

Gestion de l'entreprise, clients, catalogue, devis, factures, paiements, avoirs, journal, sauvegardes et export de données. L'édition Windows propose également des fonctions plus avancées de stock, fiscalité et suivi.

## Installation Windows

Téléchargez l’installeur complet depuis les versions publiées du dépôt. Il contient
le programme et ses dépendances ; Python n’est pas nécessaire. Installez par-dessus
la version actuelle pour conserver les comptes et les données.

La version 0.4.0 propose un profil général : pays facultatif, devise libre à trois lettres,
précision de 0 à 4 décimales, interface français/anglais, dates JJ/MM/AA, MM/JJ/AA ou
AAAA-MM-JJ. Choisissez la devise avant d’enregistrer des montants ; les montants déjà
enregistrés ne sont jamais convertis automatiquement. Les anciens profils conservent
la devise XPF et leurs deux décimales historiques.

Les identifiants professionnels et conditions restent facultatifs. Le choix de taxe
est défini par l’utilisateur. Le CA reste facultatif ; le rappel de 10 millions
concerne uniquement la Polynésie avec la devise XPF et ne bloque aucun document.
Le logiciel n’assure pas la conformité réglementaire de chaque pays.

Les brouillons conservent automatiquement les champs saisis, y compris une date
incomplète. L’aperçu PDF reprend les dernières données valides. Les nouvelles
sauvegardes chiffrées se récupèrent sur un PC sans données depuis l’écran de création
de compte, avec le mot de passe administrateur ou le code correspondant au moment
de la sauvegarde. Les anciennes sauvegardes nécessitent aussi le fichier acces.json
sur un autre PC. Conservez les sauvegardes et secrets de récupération hors du PC.

Les mises à jour sont vérifiées automatiquement à l’ouverture avec un catalogue
signé. Le dossier de publication et son assistant sont décrits dans
[distribution/PUBLICATION-0.4.0.txt](distribution/PUBLICATION-0.4.0.txt).

## Travail en cours, sans nouvelle release

La branche `work/factures-pdf` produit un installeur de test. Elle ne crée aucune
release, aucun tag et ne publie aucun catalogue de mise à jour. La version interne
reste inchangée jusqu’à validation de la beta.

Les factures s’ouvrent depuis leur liste et le tableau de bord pour l’aperçu PDF,
l’export et l’encaissement. Les références et désignations utilisent des colonnes
séparées, y compris dans le PDF. Au premier export, l’utilisateur peut créer
`Patenteasy` sur son Bureau ou choisir un autre dossier. L’emplacement est mémorisé
pour les prochains exports ; le bouton « Ouvrir le dossier PDF » donne un accès direct.

## Architecture

- `database.py` : données locales et accès SQLite ;
- `gestion.py` : logique métier ;
- `qt_app.py` : interface Windows PySide6/Qt ;
- `application_windows.py` : lanceur Windows ;
- `pdf_documents.py` : génération PDF ;
- `mises_a_jour.py` : vérification et téléchargement de mises à jour via catalogue HTTPS signé ;
- `android/` : sources Android, interface, stockage local et compilation APK.

L'ancienne interface web reste dans les sources pour compatibilité et certains tests, mais l'application Windows utilise l'interface Qt.

## Développement

Python 3.10.1 à 3.14 est pris en charge pour travailler depuis les sources. Sous Windows, `INSTALLER.cmd` sélectionne automatiquement la version compatible la plus récente disponible. Python 3.10.0 est explicitement refusé car incompatible avec PyInstaller.

Sous Windows :

```text
INSTALLER.cmd
LANCER.cmd
```

Pour les tests Python :

```powershell
python -m pytest -q
```

Pour le modèle mobile :

```powershell
node --test tests/mobile_model.test.cjs
```

## Compilation

Windows : `distribution/COMPILER_WINDOWS.cmd`

Android : voir [android/COMPILER.md](android/COMPILER.md).

Les clés de signature et mots de passe doivent rester hors du dépôt.

## Documentation

La documentation détaillée est regroupée dans [docs/](docs/) :

- [Installation](docs/INSTALLATION.md)
- [Bêta-test 0.3.7](docs/BETA_TEST_0.3.7.md)
- [Architecture Qt](docs/ARCHITECTURE_QT.md)
- [Nouveautés 0.3.7](docs/NOUVEAUTES_0.3.7.md)

## Licence

Le code Patenteasy est distribué sous GNU GPL v3 ou ultérieure. Les composants tiers conservent leurs propres licences, stockées à proximité des composants concernés.
