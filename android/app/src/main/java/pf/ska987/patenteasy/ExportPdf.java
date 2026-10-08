// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import android.app.Activity;
import android.content.SharedPreferences;
import android.net.Uri;
import android.provider.DocumentsContract;
import java.io.*;
import java.util.concurrent.*;
/** PDF dans le dossier choisi, sans accès global au stockage. */
final class ExportPdf {
    interface Retour {void message(String texte);}
    private final Activity activity;private final Coffre coffre;private final SharedPreferences preferences;private final Retour retour;
    private final ExecutorService travail=Executors.newSingleThreadExecutor();private volatile boolean enCours=false,fermee=false;
    ExportPdf(Activity a,Coffre c,SharedPreferences p,Retour r){activity=a;coffre=c;preferences=p;retour=r;}
    boolean occupe(){return enCours;}
    boolean configure(){return !preferences.getString("dossier_pdf","").isEmpty();}
    void choisir(Uri uri,int flags)throws Exception {
        activity.getContentResolver().takePersistableUriPermission(uri,flags & (android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION|android.content.Intent.FLAG_GRANT_WRITE_URI_PERMISSION));
        if(!preferences.edit().putString("dossier_pdf",uri.toString()).commit())throw new IOException("Dossier non enregistré.");
    }
    void creer(String nom,String donnees)throws Exception {
        coffre.exiger();if(enCours||fermee)throw new IOException("Terminez l’export en cours.");
        if(donnees.length()>4000000||nom.length()>200)throw new IOException("Document trop volumineux.");
        final Uri dossier=Uri.parse(preferences.getString("dossier_pdf",""));final String fichier=nom.replaceAll("[^A-Za-z0-9._-]","_")+".pdf";
        enCours=true;travail.execute(()->{
            File temporaire=null;Uri cible=null;
            try {
                temporaire=File.createTempFile("patenteasy-pdf-",".pdf",activity.getCacheDir());
                try(OutputStream flux=new FileOutputStream(temporaire)){DocumentPdf.produire(donnees,flux);}
                if(fermee||Thread.currentThread().isInterrupted())throw new IOException("Export annulé.");coffre.exiger();
                Uri parent=DocumentsContract.buildDocumentUriUsingTree(dossier,DocumentsContract.getTreeDocumentId(dossier));
                cible=DocumentsContract.createDocument(activity.getContentResolver(),parent,"application/pdf",fichier);if(cible==null)throw new IOException("Dossier inaccessible.");
                try(InputStream in=new FileInputStream(temporaire);OutputStream out=activity.getContentResolver().openOutputStream(cible,"wt")){
                    if(out==null)throw new IOException("Fichier inaccessible.");byte[] bloc=new byte[65536];int n;
                    while((n=in.read(bloc))!=-1){if(fermee||Thread.currentThread().isInterrupted())throw new IOException("Export annulé.");out.write(bloc,0,n);}
                }
                if(preferences.edit().putString("dernier_pdf",cible.toString()).commit())retour.message("PDF enregistré : "+fichier+". Retrouvez-le dans votre dossier PDF.");
                else retour.message("PDF enregistré dans votre dossier ; le raccourci du dernier PDF n’a pas pu être mémorisé.");
            }catch(Exception e){if(cible!=null)try{DocumentsContract.deleteDocument(activity.getContentResolver(),cible);}catch(Exception ignore){}retour.message("Export PDF impossible : "+e.getMessage()+". Vous pouvez choisir un autre dossier dans Réglages.");}
            finally{if(temporaire!=null)temporaire.delete();enCours=false;}
        });
    }
    void fermer(){fermee=true;travail.shutdownNow();}
}
