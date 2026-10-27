# Patenteasy — développement en cours

Branche de travail : `dev/en-cours`. Aucun nouveau numéro de version ni publication Cloudflare sur cette branche.

## Tester sous Windows

Installez `Patenteasy-Windows-TEST-Installation.exe`. Il ajoute un raccourci **Patenteasy TEST** et une installation distincte. Fermez le Patenteasy habituel avant le premier lancement : l'édition TEST propose de copier la base et ses accès. Connectez-vous avec les mêmes identifiants et mots de passe.

La base habituelle reste dans `%LOCALAPPDATA%\PatenteasyLocal`. La copie de travail reste dans `%LOCALAPPDATA%\PatenteasyLocal-DEV`. Une copie existante n'est jamais remplacée au lancement ou lors d'une réinstallation. Les sauvegardes automatiques, les préférences PDF et les journaux sont séparés. Les mises à jour de production et la publication sont désactivées dans cette édition.

Le numéro actuel est conservé et la fenêtre indique **TEST · copie indépendante**. Les documents créés ici servent uniquement aux essais : ils ne doivent pas être envoyés aux clients.

## Corrections à vérifier

- Franchise en base : montant TTC des dépenses, recettes et différence de trésorerie ; pas de détail TVA inutile. Le régime par défaut vient du choix dans **Taxe et CA**. Un choix historique de période dans Finances ne modifie pas les factures émises.
- Dans **Réglages → Mes banques**, saisir un nom par ligne et enregistrer.
- À l'encaissement ou au règlement fournisseur : sélectionner une banque et, si utile, une référence de chèque ou de virement. La banque reste facultative, les espèces restent en caisse.
- Dans **Recettes et dépenses**, filtrer par banque et rechercher un numéro de facture ou une référence de règlement. La banque apparaît également dans le CSV et l'historique des encaissements.

Les noms historiques restent associés aux paiements même si une banque est retirée des réglages. Aucun RIB, connexion bancaire ou rapprochement automatique n'est demandé.

## Retour vers la version habituelle

Aucun import automatique de TEST vers la base habituelle. Quand les corrections seront validées, préparer séparément l'import et ses contrôles en conservant une sauvegarde. Si l'activité a continué dans les deux bases, ne pas remplacer l'une par l'autre : factures, règlements et numérotation devront être comparés avant de décider du transfert.
