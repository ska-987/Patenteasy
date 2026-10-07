// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import android.app.*;
import android.os.*;
import android.content.*;
import android.net.Uri;
import android.webkit.*;
import android.view.*;
import android.widget.*;
import android.print.*;
import java.io.*;
import java.util.concurrent.*;
import org.json.*;

/** Interface locale et pont vers le coffre : aucun serveur et aucun compte développeur. */
public class MainActivity extends Activity {
    private WebView web,impression;
    private Coffre coffre;private Sauvegardes sauvegardes;private MisesAJour updates;private Connexion connexion;
    private SharedPreferences preferences;
    private final ExecutorService travail=Executors.newSingleThreadExecutor();
    private final Handler horloge=new Handler(Looper.getMainLooper());
    private String csvEnAttente="";
    private boolean demandeConnexion=false,fermee=false,chargement=false;
    private final Runnable minuterie=new Runnable(){public void run(){if(fermee)return;if(coffre!=null&&coffre.ouverte()){try{coffre.exiger();}catch(Exception e){verrouiller();}if(coffre.ouverte())travail.execute(()->{sauvegardes.automatique();updates.automatique();});}horloge.postDelayed(this,60000);}};
    @Override public void onCreate(Bundle b){
        super.onCreate(b);getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE,WindowManager.LayoutParams.FLAG_SECURE);
        preferences=getSharedPreferences("patenteasy_local",MODE_PRIVATE);
        try{coffre=new Coffre(this);sauvegardes=new Sauvegardes(this,coffre);updates=new MisesAJour(this,coffre,sauvegardes,new JSONObject(configuration()));connexion=new Connexion(this,coffre,travail);}catch(Exception e){new AlertDialog.Builder(this).setTitle("Coffre inaccessible").setMessage("Aucune donnée n’a été effacée. Contactez sav.centreprotech@proton.me.").setPositiveButton("Fermer",(x,y)->finish()).show();return;}
        web=new WebView(this);web.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets;});setContentView(web,new ViewGroup.LayoutParams(-1,-1));
        WebSettings settings=web.getSettings();settings.setJavaScriptEnabled(true);settings.setDomStorageEnabled(false);settings.setAllowFileAccess(false);settings.setAllowContentAccess(false);settings.setAllowFileAccessFromFileURLs(false);settings.setAllowUniversalAccessFromFileURLs(false);settings.setBlockNetworkLoads(true);web.addJavascriptInterface(new PontLocal(),"Android");web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){Uri u=r.getUrl();if("https".equals(u.getScheme())||"mailto".equals(u.getScheme())){try{startActivity(new Intent(Intent.ACTION_VIEW,u));}catch(Exception e){message("Aucune application pour ouvrir ce lien.");}}return true;}
            @Override public void onPageFinished(WebView v,String u){if(!chargement&&u.equals("file:///android_asset/index.html")){chargement=true;try{JSONObject session=new JSONObject(coffre.session());setTitle("Patenteasy · "+session.getString("identifiant")+" · "+("admin".equals(session.getString("role"))?"Administrateur":"Utilisateur"));}catch(Exception e){verrouiller();}travail.execute(()->{sauvegardes.automatique();updates.automatique();});}}
        });
        demandeConnexion=true;connexion.afficher();horloge.postDelayed(minuterie,60000);
    }
    void choisirImport(){try{startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE),22);}catch(Exception e){message("Sélection de sauvegarde indisponible.");connexion.afficher();}}
    public void ouvrir(){demandeConnexion=false;chargement=false;web.loadUrl("file:///android_asset/index.html");}
    private void verrouiller(){runOnUiThread(()->{if(demandeConnexion||fermee)return;demandeConnexion=true;coffre.verrouiller();web.loadUrl("about:blank");connexion.afficher();});}
    @Override public void onUserInteraction(){super.onUserInteraction();if(coffre!=null){coffre.toucher();if(!coffre.ouverte()&&!demandeConnexion)verrouiller();}}
    @Override protected void onResume(){super.onResume();if(coffre!=null&&coffre.ouverte()){try{coffre.exiger();}catch(Exception e){verrouiller();}}}
    @Override protected void onDestroy(){fermee=true;horloge.removeCallbacksAndMessages(null);if(coffre!=null)coffre.verrouiller();if(web!=null){web.removeJavascriptInterface("Android");web.destroy();}travail.shutdownNow();super.onDestroy();}
    private void message(String s){runOnUiThread(()->{Toast.makeText(this,s,Toast.LENGTH_LONG).show();if(web!=null&&coffre.ouverte())web.evaluateJavascript("window.messageNatif&&messageNatif("+JSONObject.quote(s)+")",null);});}
    private String configuration(){try(InputStream in=getAssets().open("editeur.json")){return new String(Coffre.lire(in,100000),java.nio.charset.StandardCharsets.UTF_8);}catch(Exception e){return "{}";}}
    private interface Tache{Object run() throws Exception;}
    private String resultat(Tache t){try{return new JSONObject().put("ok",true).put("valeur",t.run()).toString();}catch(Exception e){if(!coffre.ouverte())verrouiller();try{return new JSONObject().put("ok",false).put("erreur",e.getMessage()==null?"Opération impossible.":e.getMessage()).toString();}catch(Exception ignore){return "{\"ok\":false}";}}}
    private void fond(String succes,Tache t){travail.execute(()->{try{t.run();message(succes);}catch(Exception e){message(e.getMessage()==null?"Opération impossible.":e.getMessage());}runOnUiThread(()->{if(coffre.ouverte())web.evaluateJavascript("window.actualiserReglages&&actualiserReglages()",null);});});}
    @Override protected void onActivityResult(int req,int result,Intent data){super.onActivityResult(req,result,data);if(result!=RESULT_OK||data==null){if(req==22)connexion.afficher();if(req==30)csvEnAttente="";return;}
        if(req==30){try{coffre.admin();try(OutputStream o=getContentResolver().openOutputStream(data.getData(),"wt")){if(o==null)throw new IOException("Destination inaccessible.");o.write(csvEnAttente.getBytes(java.nio.charset.StandardCharsets.UTF_8));}coffre.audit("Export CSV");message("Export enregistré. Ce fichier contient vos opérations en clair : partagez-le par un moyen privé.");}catch(Exception e){message("Export impossible : "+e.getMessage());}finally{csvEnAttente="";}}
        if(req==22){connexion.importer(data.getData());}
        if(req==20){Uri u=data.getData();fond("Dossier choisi. Première sauvegarde vérifiée.",()->{sauvegardes.choisir(u);return true;});}
        if(req==21){Uri u=data.getData();new AlertDialog.Builder(this).setTitle("Restaurer la sauvegarde ?").setMessage("Les comptes et mots de passe de la sauvegarde seront repris. Une copie actuelle sera créée avant. Les documents émis ne peuvent pas être perdus.").setNegativeButton("Annuler",null).setPositiveButton("Restaurer",(a,b)->travail.execute(()->{try{sauvegardes.restaurer(u);runOnUiThread(()->{message("Sauvegarde restaurée. Reconnectez-vous.");verrouiller();});}catch(Exception e){message("Restauration refusée : "+e.getMessage());}})).show();}
        if(req==13){Uri uri=data.getData();Intent envoi=new Intent(Intent.ACTION_SEND).setType("application/pdf").putExtra(Intent.EXTRA_STREAM,uri).putExtra(Intent.EXTRA_SUBJECT,"Document Patenteasy");envoi.setClipData(ClipData.newUri(getContentResolver(),"Document Patenteasy",uri));envoi.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);try{startActivity(Intent.createChooser(envoi,"Envoyer le PDF"));}catch(Exception e){message("Aucune application de partage disponible.");}}
    }
    public class PontLocal {
        @JavascriptInterface public String charger(){try{return coffre.charger();}catch(Exception e){verrouiller();throw new IllegalStateException("Coffre verrouillé ou inaccessible.");}}
        @JavascriptInterface public boolean sauver(String json){try{return coffre.sauver(json);}catch(Exception e){message(e.getMessage());if(!coffre.ouverte())verrouiller();return false;}}
        @JavascriptInterface public String session(){return resultat(()->new JSONObject(coffre.session()));}
        @JavascriptInterface public void deconnexion(){verrouiller();}
        @JavascriptInterface public boolean bienvenueVue(){return preferences.getBoolean("participation_beta_vue",false);}
        @JavascriptInterface public boolean marquerBienvenue(){return preferences.edit().putBoolean("participation_beta_vue",true).commit();}
        @JavascriptInterface public String configuration(){return MainActivity.this.configuration();}
        @JavascriptInterface public String comptes(){return resultat(()->new JSONArray(coffre.listeComptes()));}
        @JavascriptInterface public String creerCompte(String id,String mot){return resultat(()->{coffre.creerUtilisateur(id,mot);return true;});}
        @JavascriptInterface public String activer(String id,boolean actif){return resultat(()->{coffre.actif(id,actif);return true;});}
        @JavascriptInterface public String preferences(String json){return resultat(()->{coffre.preferences(json);return true;});}
        @JavascriptInterface public String motDePasse(String ancien,String nouveau){return resultat(()->{coffre.changerMot(ancien,nouveau);return true;});}
        @JavascriptInterface public String journalAcces(){return resultat(()->new JSONArray(coffre.journal()));}
        @JavascriptInterface public String sauvegardeEtat(){return resultat(()->new JSONObject(sauvegardes.etat()));}
        @JavascriptInterface public void choisirSauvegarde(){runOnUiThread(()->{try{coffre.admin();Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);startActivityForResult(i,20);}catch(Exception e){message(e.getMessage());}});}
        @JavascriptInterface public void sauvegarder(){fond("Sauvegarde chiffrée vérifiée.",()->sauvegardes.faire());}
        @JavascriptInterface public void restaurer(){runOnUiThread(()->{try{coffre.admin();startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE),21);}catch(Exception e){message(e.getMessage());}});}
        @JavascriptInterface public void exportCsv(){runOnUiThread(()->{try{coffre.admin();if(!csvEnAttente.isEmpty())throw new IOException("Terminez l’export en cours.");csvEnAttente=ExportCsv.produire(coffre.charger());Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("text/csv").addCategory(Intent.CATEGORY_OPENABLE);i.putExtra(Intent.EXTRA_TITLE,"Patenteasy-Android-operations.csv");startActivityForResult(i,30);}catch(Exception e){csvEnAttente="";message(e.getMessage());}});}
        @JavascriptInterface public String miseAJourEtat(){return resultat(()->{coffre.exiger();return new JSONObject(updates.etat());});}
        @JavascriptInterface public void verifierMiseAJour(){fond("Vérification terminée.",()->updates.verifier());}
        @JavascriptInterface public void telechargerMiseAJour(){fond("APK vérifiée. Vous pouvez lancer l’installation.",()->updates.telecharger().getName());}
        @JavascriptInterface public void installerMiseAJour(){runOnUiThread(()->{try{coffre.admin();new AlertDialog.Builder(MainActivity.this).setTitle("Installer la mise à jour ?").setMessage("Android vous demandera de confirmer l’installation. Ne désinstallez pas Patenteasy.").setPositiveButton("Installer",(a,b)->{try{updates.installer();}catch(Exception e){message(e.getMessage());}}).setNegativeButton("Annuler",null).show();}catch(Exception e){message(e.getMessage());}});}
        @JavascriptInterface public void partagerPdf() {
            runOnUiThread(()-> {
                Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);
                i.setType("application/pdf");i.addCategory(Intent.CATEGORY_OPENABLE);
                startActivityForResult(i,13);
            });
        }
        @JavascriptInterface public void pdf(String nom,String contenu) {
            runOnUiThread(()-> {
                if(impression!=null){message("Terminez le PDF en cours.");return;}
                impression=new WebView(MainActivity.this);
                impression.getSettings().setJavaScriptEnabled(false);
                impression.getSettings().setBlockNetworkLoads(true);
                impression.getSettings().setAllowFileAccess(false);
                impression.getSettings().setAllowContentAccess(false);
                impression.setWebViewClient(new WebViewClient() {
                    @Override public void onPageFinished(WebView v,String url) {
                        PrintManager manager=(PrintManager)getSystemService(PRINT_SERVICE);
                        try {
                            manager.print(nom,v.createPrintDocumentAdapter(nom),
                                new PrintAttributes.Builder().setMediaSize(PrintAttributes.MediaSize.ISO_A4).build());
                        } catch(Exception e) { message("Création PDF impossible : "+e.getMessage()); }
                        impression=null;
                    }
                });
                impression.loadDataWithBaseURL(null,contenu,"text/html","UTF-8",null);
            });
        }
    }
}
