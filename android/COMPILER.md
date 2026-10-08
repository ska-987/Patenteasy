# Compiler Patenteasy Android 0.4.1

Dossier de travail : `C:\Users\MIKA\Documents\Patenteasy\android`.
Il faut Python 3.10+, JDK 17, SDK Android avec `platforms;android-35` et `build-tools;35.0.0`.
Le compilateur utilise aapt, javac, d8, zipalign et apksigner, sans Gradle.

Dans PowerShell, adaptez les chemins à vos installations :

```powershell
Set-Location "$env:USERPROFILE\Documents\Patenteasy\android"
$env:ANDROID_SDK_ROOT = "$env:LOCALAPPDATA\Android\Sdk"
$env:PATENTEASY_JDK = "C:\CHEMIN\VERS\jdk-17"
$env:PATENTEASY_KEYSTORE = "C:\CHEMIN\PRIVE\patenteasy-android.jks"
$env:PATENTEASY_KEY_ALIAS = "ska987"
$secret = Read-Host "Mot de passe de la clé Android" -AsSecureString
$env:PATENTEASY_KEY_PASSWORD = [System.Net.NetworkCredential]::new("", $secret).Password
try {
    py .\compiler_apk.py
    if ($LASTEXITCODE -ne 0) { throw "Compilation interrompue." }
} finally {
    Remove-Item Env:PATENTEASY_KEY_PASSWORD -ErrorAction SilentlyContinue
    Remove-Variable secret -ErrorAction SilentlyContinue
}
```

Sortie : `C:\Users\MIKA\Documents\Patenteasy\android\build\Patenteasy-Android-0.4.1.apk`.
Le keystore reste privé, extérieur au projet. N’utilisez pas une nouvelle clé : les mises à jour des installations existantes seraient refusées.

La construction CI produit un fichier « A-SIGNER.apk » qui n’est pas installable. La signature originale est appliquée par la publication ; aucun certificat de remplacement n’est créé.

Pour une version suivante, augmentez `versionCode` et `versionName` dans le manifeste. Les versions affichées dans l’interface et le code de vérification doivent être mises à jour aussi. Publiez un APK correspondant réellement à sa version et à son SHA-256.

Architecture :

- `Coffre.java` : clés, chiffrement, comptes et récupération.
- `Droits.java` : contrôle natif des écritures et protection des documents émis.
- `Sauvegardes.java` : dossier Android SAF et sauvegardes.
- `Catalogue.java`, `MisesAJour.java`, `UpdateProvider.java` : mises à jour signées et installation.
- `Connexion.java`, `MainActivity.java` : connexion et pont Android.
- `assets/model.js` : objets métier et numérotation.
- `assets/app.js`, `assets/index.html` : interface hors ligne.

La dépendance EdDSA-Java 0.3.0 est fournie dans `libs`, avec ses sources et sa licence CC0 dans `licences`.

Tests :

- `node --test tests/mobile_model.test.cjs` : modèle métier.
- `tests/run_tests.py` : chiffrement réel JCA et contrôles natifs, avec stockage Android simulé. Nécessite JDK 17 et `PATENTEASY_TEST_JSON_JAR` pointant vers org.json 20240303 de Maven Central.
- `tests/interface_dom.test.cjs` : interface simulée, nécessite linkedom.
- `tests/interface.test.cjs` : parcours Chromium à lancer dans un environnement où Chromium/Playwright fonctionnent. Le parcours a réussi dans GitHub Actions pour la construction 0.4.1 (19 contrôles). Le pont Android y est simulé ; il ne remplace pas un test sur téléphone.

Licence : GPL-3.0-or-later pour Patenteasy. Aucun compte développeur ni mot de passe universel n’est intégré aux binaires.
