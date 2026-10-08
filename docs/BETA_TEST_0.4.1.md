# Patenteasy bêta 0.4.1 — parcours de vérification

Faire les essais sur des données de test et conserver une sauvegarde avant toute mise à jour. Installer par-dessus la version existante. Sous Android, attendre l’APK signée avec la clé originale ; le fichier `A-SIGNER.apk` ne s’installe pas.

## Parcours utilisateur

1. Vérifier la version 0.4.1, les comptes et la conservation des documents existants.
2. Ouvrir une ancienne facture non réglée depuis la liste, puis depuis le tableau de bord. Vérifier les accès à l’aperçu, à l’export PDF et à l’encaissement.
3. Dans Réglages, saisir des conditions de règlement, quitter la page et la rouvrir. Vérifier que le texte a été conservé.
4. Revenir à l’ancienne facture et effectuer un nouvel export. Vérifier les conditions au bas du PDF, les colonnes référence/désignation et les montants inchangés. Modifier les conditions dans Réglages, puis réexporter pour contrôler leur actualisation.
5. Essayer des conditions vides, puis un texte long et un document comportant plusieurs lignes/pages. Vérifier que le texte reste lisible et complet.
6. Commencer un devis avec plusieurs lignes, créer un nouveau client depuis le devis et vérifier que la saisie est conservée et que le client est sélectionné. Essayer aussi l’annulation et la création du premier client.
7. Enregistrer un encaissement partiel, puis le solde d’une facture de test. Vérifier le reste à encaisser et le journal.
8. Tester la saisie des dates sans séparateurs, une date incomplète dans un brouillon et les formats proposés sur Windows.
9. Avec un nouveau profil de test, laisser les identifiants et le chiffre d’affaires vides. Choisir un pays, une devise et une précision différents avant les premiers montants. Vérifier l’absence de blocage fiscal.
10. Sous Windows, tester sélection, désélection et défilement. Choisir le dossier PDF au premier export, puis l’ouvrir depuis l’application.
11. Sous Android, choisir un dossier PDF, effectuer plusieurs exports, rouvrir le dernier PDF et essayer un dossier devenu inaccessible.
12. Vérifier la sauvegarde et la restauration, puis les droits des comptes administrateur et utilisateur. Après publication, tester la proposition de mise à jour et la confirmation Android.

## Vérifications déjà effectuées

Pour le [commit 7ef5893](https://github.com/ska-987/Patenteasy/actions/runs/37848368831) :

- Windows : tests Python, programme livré, installation depuis 0.4.0 puis réinstallation ; conservation des données de test.
- Android : 9 tests du modèle, 43 contrôles DOM, 19 contrôles Chromium, 25 contrôles du coffre JVM, 3 contrôles du catalogue et vérification CSV.
- Construction Android avec le SDK officiel et contrôle de version, package, taille et empreinte.

Les tests DOM/Chromium utilisent un pont Android simulé ; les tests du coffre utilisent un stockage Android simulé. **L’installation et les exports PDF natifs n’ont pas encore été vérifiés sur un téléphone réel.** Le certificat original est exigé par la publication, mais l’APK livrée à signer n’a pas encore reçu cette signature.

Le workflow a signalé « Publication non effectuée » faute de secrets configurés. Les applications ne sont pas annoncées comme publiées sur Cloudflare.

## Assistance

sav.centreprotech@proton.me
