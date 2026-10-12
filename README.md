# Patenteasy — bêta 0.4.2

Gestion locale des clients, devis, factures et encaissements pour les indépendants et petites entreprises.

Développeur **ska_987** · GNU GPL v3 ou ultérieure · Windows 64 bits (PySide6/Qt) et Android 8 ou supérieur.

## Correctif des règlements partiels

Les factures et leurs PDF affichent le total initial, les règlements reçus avec leur détail et le reste à régler. Les avoirs sont déduits. Chaque nouvel aperçu ou export utilise les paiements actuellement enregistrés, sans modifier les montants de la facture émise. Les PDF déjà sauvegardés doivent être réexportés.

Exemple : total 10 000, règlement reçu 3 000, reste à régler 7 000. Plusieurs paiements successifs sont cumulés ; le règlement complet affiche un solde nul.

## Installation et distribution

Le workflow Windows et Android construit les installateurs et exécute les contrôles. La publication nécessite les clés originales et les accès configurés ; sans ces secrets, les constructions restent disponibles pour une publication depuis le PC éditeur.

La version distribuée fait référence dans [le catalogue signé Cloudflare](https://patenteasy-updates.sav-centreprotech.workers.dev/catalogue.json). Le code 0.4.2 dans ce dépôt ne signifie pas à lui seul que le catalogue est déjà publié.

- Windows : installer par-dessus la version existante. Python n’est pas nécessaire.
- Android : installer l’APK signée avec le certificat original, sans désinstaller. Le versionCode passe à 11 pour permettre la mise à jour depuis 0.4.1.

Les sources, installateurs et instructions sont proposés par l’éditeur et dans les [releases](https://github.com/ska-987/Patenteasy/releases). Faire une sauvegarde avant installation.

## Fonctionnement

Clients, catalogue, devis, factures, encaissements, avoirs, recherches, PDF, comptes locaux, sauvegardes chiffrées et récupération. Windows comporte aussi stocks et suivi plus avancé. Les données Windows et Android restent locales et indépendantes : aucune synchronisation automatique.

Les conditions facultatives sont enregistrées dans Réglages et reprises lors des nouveaux exports. Le profil accepte pays et identifiants facultatifs, devise et précision monétaire ; aucune conversion des montants existants.

## Vérifications

Les tests couvrent paiements partiels successifs, règlement complet, avoirs, préservation de l’instantané émis, PDF Windows et données transmises au générateur PDF Android. Les contrôles DOM et Chromium utilisent un pont Android simulé ; l’installation et le PDF natif restent à confirmer sur téléphone réel.

## Développement

```text
INSTALLER.cmd
LANCER.cmd
python -m pytest -q tests
node --test android/tests/mobile_model.test.cjs
```

Voir [la documentation](docs/README.md), [la compilation Android](android/COMPILER.md) et [la licence](LICENSE). Les clés privées, mots de passe, données clients et sauvegardes restent hors du dépôt.
