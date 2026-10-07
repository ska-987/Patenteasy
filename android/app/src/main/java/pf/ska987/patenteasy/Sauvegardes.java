// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import android.content.*;
import android.net.Uri;
import android.provider.DocumentsContract;
import android.database.Cursor;
import org.json.*;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;

/** Sauvegardes chiffrées, destination SAF choisie uniquement par l'administrateur. */
final class Sauvegardes {
    private final Context contexte;private final Coffre coffre;private final SharedPreferences prefs;
    Sauvegardes(Context c,Coffre vault){contexte=c;coffre=vault;prefs=c.getSharedPreferences("sauvegardes",Context.MODE_PRIVATE);}
    synchronized void choisir(Uri dossier) throws Exception {
        coffre.admin();contexte.getContentResolver().takePersistableUriPermission(dossier,Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        String avant=prefs.getString("dossier","");if(!prefs.edit().putString("dossier",dossier.toString()).commit())throw new IOException("Réglage non enregistré.");
        try{faire();}catch(Exception e){prefs.edit().putString("dossier",avant).commit();throw e;}
    }
    synchronized String etat() throws Exception {coffre.exiger();return new JSONObject().put("configure",!prefs.getString("dossier","").isEmpty()).put("derniere",prefs.getLong("derniere",0)).put("erreur",prefs.getString("erreur","")).toString();}
    synchronized void automatique() {try{coffre.exiger();if(!prefs.getString("dossier","").isEmpty()&&!jour().equals(prefs.getString("jour","")))faire();}catch(Exception e){prefs.edit().putString("erreur","Sauvegarde automatique impossible. Vérifiez le dossier choisi.").commit();}}
    private String jour(){return new SimpleDateFormat("yyyy-MM-dd",Locale.ROOT).format(new Date());}
    synchronized Uri faire() throws Exception {
        try{return faireVerifiee();}catch(Exception e){prefs.edit().putString("erreur","Sauvegarde impossible. Vérifiez le dossier choisi.").commit();throw e;}
    }
    private Uri faireVerifiee() throws Exception {
        coffre.exiger();String path=prefs.getString("dossier","");if(path.isEmpty())throw new IOException("L'administrateur doit choisir un dossier de sauvegarde.");
        Uri tree=Uri.parse(path),parent=DocumentsContract.buildDocumentUriUsingTree(tree,DocumentsContract.getTreeDocumentId(tree));
        String nom="Patenteasy-Android-"+new SimpleDateFormat("yyyyMMdd-HHmmss-SSS",Locale.ROOT).format(new Date())+".pebackup";
        byte[] data=coffre.backup();Uri fichier=DocumentsContract.createDocument(contexte.getContentResolver(),parent,"application/octet-stream",nom);
        if(fichier==null)throw new IOException("Création de sauvegarde impossible.");
        try(OutputStream out=contexte.getContentResolver().openOutputStream(fichier,"wt")){if(out==null)throw new IOException("Dossier inaccessible.");out.write(data);}catch(Exception e){try{DocumentsContract.deleteDocument(contexte.getContentResolver(),fichier);}catch(Exception ignore){}throw e;}
        // Relire et comparer avant d'annoncer une sauvegarde réussie.
        byte[] lu=Coffre.lire(contexte.getContentResolver().openInputStream(fichier),20000000);
        if(!java.security.MessageDigest.isEqual(lu,data))throw new IOException("Sauvegarde non vérifiée.");
        long now=System.currentTimeMillis();prefs.edit().putLong("derniere",now).putString("jour",jour()).putString("erreur","").commit();coffre.audit("Sauvegarde vérifiée");nettoyer(tree,now);return fichier;
    }
    private void nettoyer(Uri tree,long now){
        // Conserver au minimum les 28 derniers jours ; ne toucher qu'aux fichiers créés par cette édition.
        try{Uri enfants=DocumentsContract.buildChildDocumentsUriUsingTree(tree,DocumentsContract.getTreeDocumentId(tree));try(Cursor c=contexte.getContentResolver().query(enfants,new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_LAST_MODIFIED},null,null,null)){
            if(c==null)return;while(c.moveToNext()){String n=c.getString(1);long date=c.getLong(2);if(n.matches("Patenteasy-Android-[0-9]{8}-[0-9]{6}-[0-9]{3}\\.pebackup")&&date>0&&date<now-28L*86400000)DocumentsContract.deleteDocument(contexte.getContentResolver(),DocumentsContract.buildDocumentUriUsingTree(tree,c.getString(0)));}
        }}catch(Exception ignore){}
    }
    synchronized void restaurer(Uri fichier) throws Exception {coffre.admin();byte[] data=Coffre.lire(contexte.getContentResolver().openInputStream(fichier),20000000);faire();coffre.restaurer(data);}
}
