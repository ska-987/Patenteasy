# Patenteasy — bêta 0.4.1

Gestion locale des clients, devis, factures et encaissements pour les indépendants et petites entreprises, quel que soit leur métier.

**Développeur :** ska_987 · **Licence :** GNU GPL v3 ou ultérieure  
**Windows :** interface native PySide6/Qt, 64 bits · **Android :** Android 8 ou supérieur

Les deux applications fonctionnent avec leurs données locales. Elles ne synchronisent pas automatiquement les données entre ordinateur et téléphone.

## Télécharger et installer

**La bêta 0.4.1 est construite et testée, mais sa publication Cloudflare attend les clés de signature et les accès de publication de l’éditeur.** L’APK portant la mention `A-SIGNER` ne s’installe pas.

| Version | Où la trouver | État |
| --- | --- | --- |
| Windows 0.4.1 | [Constructions GitHub Actions](https://github.com/ska-987/Patenteasy/actions/workflows/windows-release.yml), artefact `Patenteasy-Windows-0.4.1` | Installeur complet construit et vérifié |
| Android 0.4.1 | Même workflow, artefact `Patenteasy-Android-0.4.1-A-SIGNER` | Construction vérifiée ; signature originale nécessaire |
| Versions déjà publiées | [Releases GitHub](https://github.com/ska-987/Patenteasy/releases) | Dernier installeur Windows publié sur GitHub : bêta 0.4.0 |

Les artefacts Actions nécessitent une connexion GitHub et sont conservés 30 jours. Après publication, la release `v0.4.1-beta` regroupera l’installeur Windows et l’APK signée.

État du catalogue Cloudflare vérifié le **8 octobre 2026** : Windows **0.3.8**, Android **0.3.7**. Le numéro de version dans les sources ne signifie donc pas que la mise à jour est déjà distribuée.

Sous Windows, l’installeur contient le programme et ses dépendances : aucun Python à installer pour utiliser l’application. Fermer Patenteasy et installer par-dessus la version existante. Sous Android, sauvegarder puis installer l’APK officiellement signée par-dessus l’application, sans la désinstaller.

Voir [l’installation détaillée](docs/INSTALLATION.md).

## Ce qui change dans la bêta 0.4.1

- **Factures accessibles :** ouverture depuis les listes et le tableau de bord, avec accès à l’aperçu, à l’export PDF et à l’encaissement.
- **Référence et désignation séparées :** colonnes distinctes dans les devis, factures et PDF.
- **Conditions facultatives dans Réglages :** enregistrement automatique des conditions de vente, de règlement et informations complémentaires. Elles apparaissent aussi sur les anciens documents au prochain aperçu ou export, au bas du PDF. Les montants et paiements enregistrés sont conservés.
- **Nouveau client depuis un devis :** création et sélection du client sans perdre les lignes ni les informations déjà saisies.
- **Accès rapide aux PDF :** Windows propose un dossier `Patenteasy` sur le Bureau au premier export, ou un autre dossier. Android permet de choisir un dossier via le sélecteur système. Le choix est mémorisé ; Réglages permet de le changer. Android propose aussi l’ouverture du dernier PDF.
- **Dates plus simples :** séparateurs automatiques. Windows propose JJ/MM/AA, MM/JJ/AA ou AAAA-MM-JJ ; Android utilise JJ/MM/AA.
- **Profil général :** pays et identifiants professionnels facultatifs, devise à trois lettres et précision monétaire de 0 à 4 décimales. Le choix de taxe reste à l’utilisateur. Le chiffre d’affaires est facultatif et ne bloque aucun document.
- **Confort sur Windows :** sélection lisible et facile à effacer, défilement amélioré et brouillons enregistrés pendant la saisie.

Les anciennes données conservent leur devise et leur précision ; aucune conversion monétaire automatique n’est effectuée. Windows propose une interface français/anglais ; l’interface Android reste en français.

Le rappel de seuil de chiffre d’affaires de 10 millions concerne uniquement le profil Polynésie/XPF. Il est informatif. Les conditions et obligations applicables restent définies par l’utilisateur pour son activité et son pays.

Voir [les nouveautés détaillées](docs/NOUVEAUTES_0.4.1.md).

## Fonctions disponibles

Entreprise et clients, catalogue, devis, factures, encaissements partiels ou complets, avoirs, journal, recherches, exports PDF/CSV, comptes locaux administrateur/utilisateur, sauvegardes et récupération des données. L’édition Windows comporte également la gestion des stocks et des fonctions de suivi plus avancées.

Les nouvelles sauvegardes Windows chiffrées peuvent être restaurées sur un autre PC depuis l’écran de création de compte, avec le mot de passe administrateur ou le code de récupération correspondant à la sauvegarde. Les anciennes sauvegardes nécessitent également leur fichier `acces.json` pour une restauration sur un autre PC.

## Mises à jour et publication

Les applications vérifient les mises à jour à partir d’un catalogue HTTPS signé. Android demande la confirmation système pour installer une nouvelle APK.

Le [workflow Windows et Android](.github/workflows/windows-release.yml) construit et contrôle les deux applications à partir du même commit. Sur `main`, il signe puis publie automatiquement sur Cloudflare **si les secrets de l’éditeur sont configurés**. Les téléchargements des deux applications sont vérifiés avant l’envoi du catalogue signé, puis une release GitHub bêta est créée.

Sans les accès nécessaires, le workflow indique **Publication non effectuée** et conserve les constructions disponibles. Une tâche verte ne signifie pas, à elle seule, que la publication a eu lieu.

La [procédure de publication 0.4.1](distribution/PUBLICATION-0.4.1.md) décrit les sept secrets GitHub et le script `Publier-0.4.1.cmd` pour publier depuis le PC éditeur. La signature Android originale et la clé originale du catalogue sont requises ; elles restent hors du dépôt.

## Vérifications

La construction 0.4.1 du [commit testé](https://github.com/ska-987/Patenteasy/actions/runs/37848368831) a passé les tests Windows, les vérifications du programme livré, la mise à niveau depuis 0.4.0 et la réinstallation avec conservation des données de test.

Android a passé les tests du modèle, de l’interface DOM, du rendu Chromium, du coffre, du catalogue signé et du CSV ; l’APK a été construite avec le SDK officiel. Les ponts Android et le stockage sont simulés dans ces tests. **L’installation sur un téléphone réel et les exports PDF natifs restent à vérifier sur appareil avant diffusion générale.**

Voir [le parcours de bêta-test 0.4.1](docs/BETA_TEST_0.4.1.md).

## Développer depuis les sources

L’assistant Windows `INSTALLER.cmd` recherche Python 3.10.1 à 3.14 et prépare les dépendances. Python 3.10.0 est refusé par cet assistant.

```text
INSTALLER.cmd
LANCER.cmd
```

Depuis la racine du dépôt, avec les dépendances de test installées :

```text
python -m pytest -q tests
node --test android/tests/mobile_model.test.cjs
```

Les tests d’interface Android nécessitent linkedom ou Playwright selon le parcours ; les tests JVM nécessitent JDK 17 et la bibliothèque org.json. Voir [la compilation et les tests Android](android/COMPILER.md).

Compilation Windows : `distribution/COMPILER_WINDOWS.cmd`. Compilation Android : `android/compiler_apk.py`, selon les [instructions Android](android/COMPILER.md).

## Organisation des sources

| Emplacement | Rôle |
| --- | --- |
| `qt_app.py`, `application_windows.py` | Interface et lancement Windows natifs |
| `database.py`, `gestion.py` | Données locales et logique métier |
| `pdf_documents.py` | Documents PDF Windows |
| `mises_a_jour.py` | Catalogue signé et mises à jour Windows |
| `android/` | Application Android, interface, stockage, PDF et mises à jour |
| `distribution/` | Construction, signature et publication |
| `docs/` | Documentation utilisateur et développeur |

L’ancienne interface web reste dans les sources pour compatibilité et certains tests ; Windows utilise Qt.

## Documentation et licence

- [Installation](docs/INSTALLATION.md)
- [Nouveautés 0.4.1](docs/NOUVEAUTES_0.4.1.md)
- [Bêta-test 0.4.1](docs/BETA_TEST_0.4.1.md)
- [Publication Windows et Android](distribution/PUBLICATION-0.4.1.md)
- [Architecture Qt](docs/ARCHITECTURE_QT.md)
- [GNU GPL v3 ou ultérieure](LICENSE)

Les composants tiers conservent leurs licences à proximité des composants concernés. Les clés privées, mots de passe, sauvegardes et données utilisateur doivent rester hors du dépôt.
