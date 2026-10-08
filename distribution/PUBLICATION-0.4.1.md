# Patenteasy bêta 0.4.1 — Windows et Android

Windows : `Patenteasy-Windows-0.4.1-Installation.exe`.
Android : `Patenteasy-Android-0.4.1.apk`, après signature originale.
Ne désinstallez pas l’ancienne application : installez la mise à jour par-dessus.

Les conditions facultatives s’enregistrent dans Réglages et s’affichent dans les
anciens documents lors du prochain export. Nouveau client depuis le devis,
référence et désignation séparées, profil général et dossier PDF mémorisé.

## Publication depuis le PC éditeur

Le dossier de publication contient les deux constructions du même commit,
leurs manifestes de vérification et `apksigner.jar` provenant du SDK officiel.
Le fichier `A-SIGNER.apk` n’est pas une application installable.

La clé Android originale reste dans son emplacement privé. Le certificat
doit rester `cfc8d95ee97be9a7a80eca28de72178d7e9cd01236dc8187c69ba1c60ff7c119`.
La clé Ed25519 reste à
`%LOCALAPPDATA%\ska_987\signature-patenteasy\cle-privee.pem`.

Double-cliquez sur `Publier-0.4.1.cmd`. Le script demande uniquement les accès
qui ne sont pas déjà configurés sur votre PC ; aucune clé n’est copiée dans
les livrables ou les sources. Java 17 et Python 3.10+ sont nécessaires.

Le script vérifie les constructions, signe l’APK, vérifie le certificat,
signe le catalogue, envoie les deux fichiers dans `patenteasy-releases`,
relit leurs octets depuis R2 et depuis les URL publiques puis envoie
`catalogue.json` en dernier. Un échec avant cette dernière étape conserve le
catalogue publié précédemment. Le Worker existant n’est pas remplacé.

## Publication automatique depuis GitHub

Le workflow construit et teste les deux applications à chaque commit sur
`main`. La publication nécessite ces secrets de dépôt, configurés par l’éditeur :

| Secret | Contenu |
| --- | --- |
| `PATENTEASY_ANDROID_KEYSTORE_BASE64` | Keystore Android original en base64 |
| `PATENTEASY_ANDROID_KEY_ALIAS` | Alias de la clé originale |
| `PATENTEASY_ANDROID_KEY_PASSWORD` | Mot de passe de la clé |
| `PATENTEASY_CATALOGUE_PRIVATE_KEY` | Clé privée PEM Ed25519 originale |
| `CLOUDFLARE_ACCOUNT_ID` | Identifiant du compte R2 |
| `R2_ACCESS_KEY_ID` | Identifiant d’accès au bucket |
| `R2_SECRET_ACCESS_KEY` | Secret d’accès au bucket |

Ces secrets ne doivent jamais être ajoutés au code ni envoyés dans une conversation.
Sans eux, le workflow fournit l’installeur Windows et l’APK à signer ; il
indique explicitement que la publication n’a pas eu lieu. Les contrôles de
construction continuent à fonctionner.

Avec les accès configurés, la release GitHub `v0.4.1-beta` contient les deux
applications après vérification Cloudflare. Android demande la confirmation
système pour installer une mise à jour ; Windows propose l’installeur vérifié.
