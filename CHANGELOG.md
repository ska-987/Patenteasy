# Changelog

Toutes les modifications importantes de Patenteasy seront documentées dans ce fichier.

Le projet suit un versionnement de type `MAJEUR.MINEUR.CORRECTIF` lorsque cela est applicable.

## [Unreleased]

## [0.3.9] - 2026-10-08

- Sélection lisible en thèmes clair et sombre ; désélection avec Échap.
- Défilement des formulaires, devis, factures et avoirs.
- Conditions et mentions repliables et facultatives.
- Choix de TVA annuel effaçable, sans dates ni attestation obligatoire.
- CA facultatif ; rappel au-delà de 10 millions sans blocage ni changement de TVA imposé.
- Documents déjà émis conservés à l'identique.
- Installation Windows complète, assistant de mise à jour intégré conservé.
- Construction et vérification du programme distribué sous Windows.
- Android reste en 0.3.7.


## [0.3.8] - 2026-10-07

### Corrigé

- Mise à jour Windows fiabilisée dans le paquet PyInstaller.
- Suppression de la dépendance à un `pythonw.exe` externe pour l'assistant de mise à jour.
- Assistant de mise à jour embarqué dans `Patenteasy.exe` via le mode `--install-update`.
- Installateur Inno Setup aligné sur la version Windows 0.3.8 et le nom `Patenteasy-Windows-0.3.8-Installation.exe`.

### Technique

- `installer_mise_a_jour.py` est explicitement inclus dans la compilation PyInstaller.
- La version Android reste en 0.3.7 : cette correction concerne uniquement l'édition Windows.

## [0.3.7]

### Ajouté

- Mise en place du dépôt GitHub officiel.
- Ajout de la documentation de base du projet.
- Ajout de la licence GNU GPLv3.
- Préparation de la structure pour la version de bureau PySide6 / Qt.

### Modifié

- Documentation regroupée dans le dossier `docs/`.
- README simplifié et mis à jour pour Patenteasy 0.3.7.
- Instructions d'installation remplacées par une version unique et actuelle.
- Assemblage Windows adapté à la nouvelle organisation de la documentation.

### Supprimé

- Anciens guides 0.3.2 / 0.3.5 devenus obsolètes.
