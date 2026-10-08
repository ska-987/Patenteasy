# Installer Patenteasy — Windows et Android

## Disponibilité de la bêta 0.4.1

L’installeur Windows 0.4.1 est construit et vérifié. La construction Android 0.4.1 est disponible à signer ; **le fichier `A-SIGNER.apk` n’est pas installable**. La diffusion par mise à jour attend la signature originale et la publication du catalogue.

Consulter le [README principal](../README.md) pour les téléchargements et l’état de publication. Les anciennes versions déjà publiées restent dans les [releases GitHub](https://github.com/ska-987/Patenteasy/releases).

## Windows 64 bits

1. Faire une sauvegarde des données et fermer Patenteasy.
2. Pour la bêta 0.4.1, lancer `Patenteasy-Windows-0.4.1-Installation.exe` fourni par l’éditeur ou téléchargé depuis la construction vérifiée.
3. Installer par-dessus la version existante, puis ouvrir Patenteasy depuis son raccourci.
4. Vérifier la version affichée, les comptes et les documents précédents.

L’installeur inclut les dépendances : Python et Java ne sont pas nécessaires pour utiliser l’application Windows. L’interface est native PySide6/Qt ; Edge/WebView2 n’est pas requis. Les données utilisateur sont conservées dans `%LOCALAPPDATA%\PatenteasyLocal\data`.

## Android 8 ou supérieur

1. Faire une sauvegarde depuis l’application.
2. Attendre l’APK officiellement signée `Patenteasy-Android-0.4.1.apk`.
3. Autoriser, si Android le demande, l’installation depuis la source utilisée, puis confirmer l’installation par-dessus l’application existante.
4. Ne pas désinstaller l’ancienne application : cela supprimerait ses données locales.
5. Vérifier la version, la connexion et les documents après la mise à jour.

La même clé Android de signature doit être utilisée pour préserver la compatibilité des installations existantes. Un message de signature incompatible doit être résolu avec l’éditeur.

Au premier export PDF, Android permet de choisir un dossier accessible au téléphone. Réglages permet ensuite de changer le dossier ou d’ouvrir le dernier PDF.

## Publication par l’éditeur

Java et Python sont nécessaires sur le PC qui signe et publie, pas sur celui qui utilise l’installeur Windows. Voir [la publication 0.4.1](../distribution/PUBLICATION-0.4.1.md).

Les éditions Windows et Android ont des données locales indépendantes. Les clés de signature, mots de passe, sauvegardes privées et données utilisateur restent hors du dépôt Git.
