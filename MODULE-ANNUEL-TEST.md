# Patenteasy — module annuel, édition de test

Développé par ska_987. Cette branche est une préparation à tester, sans nouvelle release ni mise à jour du catalogue Cloudflare.

## Fonctions intégrées

- Licence SKA signée Ed25519, liée à Patenteasy et au nom de l'entreprise ; activation, expiration et modules autorisés contrôlés à chaque action. Retour aux fonctions gratuites à expiration, sans suppression des données.
- Windows : stockage dans la base chiffrée existante. Android : licence dans le coffre AES-GCM, vérification et calculs natifs Java, contrôles d'écriture indépendants des boutons.
- TVA sur les devis et factures toujours gratuite. Calculs financiers et préparation administrative réservés à l'administrateur avec licence.
- Dépenses détaillées HT / taux / TVA / TTC, plusieurs lignes et taux, justificatif et part déductible. Catégorie achats, autres charges, personnel, immobilisation ou cotisations RNS.
- Règlements fournisseurs partiels : une seule écriture de dépense par règlement. Windows permet aussi de rapprocher une dépense du journal sans créer un second décaissement.
- Recettes des factures reprises depuis les encaissements existants ; pas de nouveau journal de recettes concurrent.
- Calcul TVA perçue, exigible, déductible, crédit précédent, régularisations, montant à reverser et crédit. Franchise : aucune déduction. Biens / services à qualifier ; les débits nécessitent une autorisation explicitement confirmée.
- Dossiers préparatoires pour TVA 1010 / 1040, CPS RNS, IT et démarche TPE : données comptables et identité préremplies, export PDF de préparation, liste des informations manquantes, date vérifiée par l'administrateur, rappels et preuve de dépôt / paiement.

## Activation réelle

La clé publique Ed25519 personnelle de ska_987 est intégrée à Windows et Android. Les clés privées restent chez l’éditeur.

Dans SKA License Manager, créer une licence pour `patenteasy`, avec le nom exact de l'entreprise, la durée annuelle souhaitée et les fonctionnalités `finance_tva,administratif`. Importer le fichier signé depuis Licence annuelle. Un renouvellement s'effectue en important la nouvelle licence signée.

La vérification est locale : elle ne constitue pas une révocation à distance ni une protection absolue contre la modification du logiciel GPL. Le contrôle d'horloge détecte le recul par rapport à la dernière vérification locale ; il ne fournit pas une heure de serveur indépendante.

## Portée administrative de cette première intégration

Les PDF livrés sont des **dossiers préparatoires**, clairement marqués brouillon. Ils ne remplissent pas encore les cases des PDF officiels DICP/CPS et ne déposent rien sur les portails. Les autres revenus, annexes, charges fiscales et rapprochements nécessitent un complément. Ne pas présenter le journal de trésorerie comme une déclaration fiscale complète.

Les échéances sont renseignées et confirmées par l'administrateur à partir de sa situation et de la source officielle ; aucune périodicité inconnue n'est inventée. Les alertes concernent les dossiers enregistrés. Les anciens achats sans détail sont signalés et leur TVA n'est pas déduite automatiquement.

## Tests et installation

Les lanceurs Test ne créent pas de nouvelle version publique. Leur identifiant interne reste celui de la base actuelle ; sur Android, l'APK est signé avec le certificat habituel. Les données sont conservées mais une sauvegarde vérifiée reste recommandée avant un essai.

Les tests utilisent des clés éphémères exclusivement dans des dossiers isolés. Aucune clé privée de test ou d'éditeur n'est embarquée dans les lanceurs. Les tests CI Windows construisent l'EXE, l'installent deux fois et vérifient les données témoin ; les tests Android vérifient le modèle, les droits et les signatures sur JVM et interface simulée. Ils ne remplacent pas l'essai sur un téléphone réel.

## GitLab — copie de la branche de travail

Dans une copie locale du dépôt Patenteasy (pas dans le ZIP des sources) :

```powershell
git fetch origin work/module-financier
git switch -C work/module-financier origin/work/module-financier
git remote -v
# Seulement si le remote gitlab n'existe pas :
git remote add gitlab https://gitlab.com/ska-987/Patenteasy.git
git push -u gitlab work/module-financier
```

Aucun tag à créer avant validation et choix de la version définitive.
