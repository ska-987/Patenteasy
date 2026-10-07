# Patenteasy

**Version Windows :** 0.3.8  
**Version Android :** 0.3.7

Application de gestion locale pour indépendants, artisans et petites entreprises.

**Développeur :** ska_987  
**Plateformes :** Windows 64 bits et Android 8+  
**Licence :** GNU GPL v3 ou ultérieure

## Éditions

Patenteasy existe en deux éditions locales indépendantes :

- **Windows 0.3.8** : interface de bureau native PySide6/Qt, sans Edge/WebView2 et sans serveur HTTP local ;
- **Android 0.3.7** : application hors ligne avec stockage local sur le téléphone.

Il n'y a pas de synchronisation automatique entre Windows et Android.

## Fonctions principales

Gestion de l'entreprise, clients, catalogue, devis, factures, paiements, avoirs, journal, sauvegardes et export de données. L'édition Windows propose également des fonctions plus avancées de stock, fiscalité et suivi.

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

Python 3.10 ou ultérieur est requis pour travailler depuis les sources.

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
