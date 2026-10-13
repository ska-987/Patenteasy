# Documentation développeur de Patenteasy

Cette page regroupe les informations techniques. Pour utiliser l’application, consulter le [guide utilisateur](GUIDE-UTILISATEUR.md).

## Sources et branches

GitHub : `ska-987/Patenteasy`. GitLab est le miroir secondaire.

Le module annuel et ses repères visuels sont dans la branche `release/module-annuel-0.4.4`. La branche `main` conserve actuellement la base 0.4.2 : la documentation publique peut présenter les fonctionnalités de la distribution plus récente sans signifier que ces branches ont été fusionnées.

## Développement et tests

- [Architecture Windows Qt](ARCHITECTURE_QT.md)
- [Compilation Android](../android/COMPILER.md)
- [Publication Windows et Android](../distribution/PUBLICATION-0.4.2.md)

```text
INSTALLER.cmd
LANCER.cmd
python -m pytest -q tests
node --test android/tests/mobile_model.test.cjs
```

La distribution Windows utilise PySide6/Qt. Les contrôles Android comprennent le modèle, le DOM, Chromium avec un pont Android simulé et la JVM. Les vérifications simulées ne remplacent pas l’installation et l’essai du PDF natif sur téléphone.

## Publication

Construire et vérifier les applications d’un même commit. Utiliser les clés originales pour la signature Android et celle du catalogue des mises à jour.

Le paquet éditeur habituel contient les constructions, les manifestes, `Signer-catalogue.cmd` et `LIRE-EN-PREMIER.txt`. Signer localement, envoyer les fichiers Windows, Android et sources dans le bucket R2 `patenteasy-releases`, puis publier `catalogue.json` en dernier. Conserver le Worker existant et vérifier la mise à jour depuis l’application installée.

Le catalogue officiel est disponible à l’adresse :
https://patenteasy-updates.sav-centreprotech.workers.dev/catalogue.json

Les secrets de signature et les accès R2 configurés dans GitHub permettent la publication par le workflow concerné. Sans eux, une compilation réussie ne signifie pas que la mise à jour est publiée.

La clé publique du License Manager vérifie les licences annuelles des clients. Elle est distincte de la clé qui vérifie les catalogues de mise à jour.

Les clés privées, mots de passe, données clients et sauvegardes restent hors des dépôts.

## Historique

- [Nouveautés 0.4.1](NOUVEAUTES_0.4.1.md)
- [Parcours de test 0.4.1](BETA_TEST_0.4.1.md)
- [Nouveautés 0.3.7](NOUVEAUTES_0.3.7.md)
- [Parcours de test 0.3.7](BETA_TEST_0.3.7.md)

Les licences des composants tiers restent à leur emplacement d’origine.
