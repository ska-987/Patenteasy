// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;

import android.app.Activity;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.*;
import android.print.*;
import android.provider.DocumentsContract;
import android.webkit.*;
import java.io.*;

/** PDF dans le dossier choisi par l’utilisateur. Aucun accès global au stockage. */
final class ExportPdf {
    interface Retour { void message(String texte); }
    private final Activity activity;
    private final Coffre coffre;
    private final SharedPreferences preferences;
    private final Retour retour;
    private WebView vue;
    private PrintDocumentAdapter adaptateur;
    private ParcelFileDescriptor sortie;
    private File temporaire;
    private CancellationSignal annulation;private boolean fermeture=false;
    ExportPdf(Activity a,Coffre c,SharedPreferences p,Retour r){activity=a;coffre=c;preferences=p;retour=r;}
    boolean occupe(){return vue!=null;}
    boolean configure(){return !preferences.getString("dossier_pdf","").isEmpty();}
    void choisir(Uri uri,int flags) throws Exception {
        activity.getContentResolver().takePersistableUriPermission(uri,flags & (android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION|android.content.Intent.FLAG_GRANT_WRITE_URI_PERMISSION));
        if(!preferences.edit().putString("dossier_pdf",uri.toString()).commit())throw new IOException("Dossier non enregistré.");
    }
    void creer(String nom,String html) throws Exception {
        coffre.exiger();
        if(occupe())throw new IOException("Terminez l’export en cours.");
        if(html.length()>4000000)throw new IOException("Document trop volumineux.");
        final Uri dossier=Uri.parse(preferences.getString("dossier_pdf",""));
        final String fichier=nom.replaceAll("[^A-Za-z0-9._-]","_")+".pdf";
        temporaire=File.createTempFile("patenteasy-pdf-",".pdf",activity.getCacheDir());
        vue=new WebView(activity);
        vue.getSettings().setJavaScriptEnabled(false);vue.getSettings().setBlockNetworkLoads(true);
        vue.getSettings().setAllowFileAccess(false);vue.getSettings().setAllowContentAccess(false);
        vue.setWebViewClient(new WebViewClient(){@Override public void onPageFinished(WebView v,String url){
            if(adaptateur!=null)return;
            try {
                adaptateur=v.createPrintDocumentAdapter(nom);adaptateur.onStart();annulation=new CancellationSignal();
                PrintAttributes attributs=new PrintAttributes.Builder().setMediaSize(PrintAttributes.MediaSize.ISO_A4)
                    .setResolution(new PrintAttributes.Resolution("pdf","PDF",300,300))
                    .setMinMargins(new PrintAttributes.Margins(350,350,350,350)).build();
                adaptateur.onLayout(null,attributs,annulation,new PrintDocumentAdapter.LayoutResultCallback(){
                    @Override public void onLayoutFinished(PrintDocumentInfo info,boolean change){
                        try {
                            sortie=ParcelFileDescriptor.open(temporaire,ParcelFileDescriptor.MODE_READ_WRITE|ParcelFileDescriptor.MODE_TRUNCATE);
                            adaptateur.onWrite(new PageRange[]{PageRange.ALL_PAGES},sortie,annulation,new PrintDocumentAdapter.WriteResultCallback(){
                                @Override public void onWriteFinished(PageRange[] pages){
                                    Uri cible=null;
                                    try {
                                        sortie.close();sortie=null;coffre.exiger();
                                        Uri parent=DocumentsContract.buildDocumentUriUsingTree(dossier,DocumentsContract.getTreeDocumentId(dossier));
                                        cible=DocumentsContract.createDocument(activity.getContentResolver(),parent,"application/pdf",fichier);
                                        if(cible==null)throw new IOException("Dossier inaccessible.");
                                        try(InputStream in=new FileInputStream(temporaire);OutputStream out=activity.getContentResolver().openOutputStream(cible,"wt")){
                                            if(out==null)throw new IOException("Fichier inaccessible.");
                                            byte[] bloc=new byte[65536];int n;while((n=in.read(bloc))!=-1)out.write(bloc,0,n);
                                        }
                                        preferences.edit().putString("dernier_pdf",cible.toString()).commit();
                                        retour.message("PDF enregistré : "+fichier+". Retrouvez-le dans votre dossier PDF.");
                                    }catch(Exception e){if(cible!=null)try{DocumentsContract.deleteDocument(activity.getContentResolver(),cible);}catch(Exception ignore){}erreur(e.getMessage());}
                                    finally{fermer();}
                                }
                                @Override public void onWriteFailed(CharSequence e){erreur(String.valueOf(e));fermer();}
                                @Override public void onWriteCancelled(){retour.message("Export annulé.");fermer();}
                            });
                        }catch(Exception e){erreur(e.getMessage());fermer();}
                    }
                    @Override public void onLayoutFailed(CharSequence e){erreur(String.valueOf(e));fermer();}
                    @Override public void onLayoutCancelled(){retour.message("Export annulé.");fermer();}
                },new Bundle());
            }catch(Exception e){erreur(e.getMessage());fermer();}
        }});
        vue.loadDataWithBaseURL(null,html,"text/html","UTF-8",null);
    }
    private void erreur(String e){retour.message("Export PDF impossible : "+e+". Vous pouvez choisir un autre dossier dans Réglages.");}
    void fermer(){
        if(fermeture)return;fermeture=true;
        if(annulation!=null&&!annulation.isCanceled())annulation.cancel();annulation=null;
        if(sortie!=null)try{sortie.close();}catch(Exception ignore){}sortie=null;
        if(adaptateur!=null)adaptateur.onFinish();adaptateur=null;
        if(vue!=null){vue.destroy();vue=null;}if(temporaire!=null)temporaire.delete();temporaire=null;fermeture=false;
    }
}
