# Nouveautés Patenteasy — bêta 0.4.1

Développeur : **ska_987**. Versions Windows et Android : **0.4.1**.

## Devis, factures et encaissements

Les factures s’ouvrent pour consulter le document, exporter le PDF et enregistrer un encaissement. Les références et désignations ont des colonnes séparées dans l’interface et les documents PDF.

Un nouveau client peut être créé directement pendant la préparation d’un devis. Il est ensuite sélectionné sans perdre les lignes, l’objet ou la date déjà saisis.

## Conditions facultatives

Les conditions de vente, de règlement et informations complémentaires sont créées et modifiées uniquement dans Réglages. Elles s’enregistrent automatiquement.

Les documents utilisent les conditions actuelles au prochain aperçu ou export, y compris les anciens devis et les anciennes factures non réglées. Les PDF déjà enregistrés doivent être exportés à nouveau pour contenir le nouveau texte. Les conditions apparaissent au bas du document ; les textes longs peuvent occuper plusieurs pages.

Ces changements de texte ne recalculent pas les anciens documents et ne modifient pas leurs montants ou leurs paiements.

## Exports PDF

Sous Windows, le premier export propose la création d’un dossier `Patenteasy` sur le Bureau ou le choix d’un autre dossier. Le choix est mémorisé et un bouton permet d’ouvrir le dossier PDF.

Sous Android, le premier export utilise le sélecteur de dossier système. Réglages permet de modifier cet emplacement et d’ouvrir le dernier PDF. La génération native produit un tableau paginé avec référence et désignation séparées.

## Profil et saisie

Le profil accepte un pays facultatif, des identifiants professionnels facultatifs, une devise à trois lettres et de 0 à 4 décimales monétaires. Le choix de taxe et le chiffre d’affaires restent facultatifs. Les informations de chiffre d’affaires ne bloquent pas les documents.

Les montants existants ne sont pas convertis automatiquement. Les anciennes données XPF conservent leur précision historique ; les documents déjà émis gardent leur identité et leurs montants enregistrés.

Les séparateurs de date sont ajoutés pendant la saisie. Windows propose trois formats et une interface français/anglais ; Android utilise JJ/MM/AA et une interface française.

La sélection et le défilement de l’interface Windows ont été améliorés. Les brouillons permettent de conserver une saisie incomplète avant l’émission du document.

## Publication

Le workflow GitHub construit les deux éditions, puis signe et publie sur Cloudflare si les accès sont configurés. Le catalogue signé est envoyé après vérification des deux téléchargements. La confirmation d’installation Android reste gérée par le système.

La construction 0.4.1 est terminée. La signature de production et la publication restent nécessaires pour distribuer l’APK. Voir [le README](../README.md) et [la procédure de publication](../distribution/PUBLICATION-0.4.1.md).
