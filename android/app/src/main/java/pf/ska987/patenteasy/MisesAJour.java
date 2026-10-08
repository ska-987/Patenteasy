// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import android.content.*;
import android.content.pm.*;
import android.net.Uri;
import org.json.*;
import javax.net.ssl.HttpsURLConnection;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;

/** Catalogue Ed25519, téléchargement vérifié et installation Android avec confirmation. */
final class MisesAJour {
    private final Context contexte;private final Coffre coffre;private final Sauvegardes backups;private final JSONObject editeur;
    private volatile JSONObject etat=new JSONObject();private long derniere;private String empreinteTelechargee="";
    private static final String SERVEUR="https://patenteasy-updates.sav-centreprotech.workers.dev";
    MisesAJour(Context c,Coffre v,Sauvegardes b,JSONObject e){contexte=c;coffre=v;backups=b;editeur=e;}
    private HttpsURLConnection connexion(String lien,int timeout) throws Exception {
        URL u=new URL(lien);if(!"https".equals(u.getProtocol())||u.getUserInfo()!=null||!u.getHost().equals(new URL(SERVEUR).getHost()))throw new SecurityException("Lien de mise à jour non autorisé.");
        HttpsURLConnection c=(HttpsURLConnection)u.openConnection();c.setInstanceFollowRedirects(false);c.setConnectTimeout(timeout);c.setReadTimeout(timeout);c.setRequestProperty("User-Agent","Patenteasy-Android/0.4.1");c.setRequestProperty("Accept","application/json, application/octet-stream");if(c.getResponseCode()!=200){c.disconnect();throw new IOException("Serveur indisponible.");}return c;
    }
    synchronized String verifier() throws Exception {
        coffre.exiger();HttpsURLConnection c=connexion(editeur.getString("catalogue_mises_a_jour"),15000);byte[] raw;try{raw=Coffre.lire(c.getInputStream(),1000000);}finally{c.disconnect();}
        JSONObject catalogue=new JSONObject(new String(raw,StandardCharsets.UTF_8));JSONObject versions=Catalogue.versions(catalogue,editeur.getString("cle_publique_mises_a_jour"));
        JSONObject mobile=versions.getJSONObject("android");String v=mobile.getString("version");Catalogue.comparer(v,"0.4.1");connexionValide(mobile.getString("url"));
        if(!mobile.getString("sha256").matches("[0-9a-fA-F]{64}")||mobile.getLong("taille")<1||mobile.getLong("taille")>500000000||!"apk".equals(mobile.getString("format")))throw new SecurityException("Catalogue invalide.");
        etat=new JSONObject(mobile.toString()).put("nouvelle",Catalogue.comparer(v,"0.4.1")>0).put("erreur","");derniere=System.currentTimeMillis();return etat.toString();
    }
    private void connexionValide(String lien) throws Exception {URL u=new URL(lien);if(!"https".equals(u.getProtocol())||u.getUserInfo()!=null||!u.getHost().equals(new URL(SERVEUR).getHost()))throw new SecurityException("Lien non autorisé.");}
    synchronized void automatique(){if(System.currentTimeMillis()-derniere<3600000)return;try{verifier();}catch(Exception e){try{etat=new JSONObject().put("nouvelle",false).put("erreur","Vérification indisponible. Vos données restent locales.");}catch(Exception ignore){}derniere=System.currentTimeMillis();}}
    String etat(){return etat.toString();}
    private static String hex(byte[] b){StringBuilder s=new StringBuilder();for(byte x:b)s.append(String.format(Locale.ROOT,"%02x",x&255));return s.toString();}
    synchronized File telecharger() throws Exception {
        coffre.admin();JSONObject r=new JSONObject(verifier());if(!r.getBoolean("nouvelle"))throw new IOException("Votre version est à jour.");backups.faire();
        File temp=new File(contexte.getCacheDir(),"mise-a-jour.part"),apk=new File(contexte.getCacheDir(),"patenteasy-update.apk");temp.delete();apk.delete();long taille=0;MessageDigest h=MessageDigest.getInstance("SHA-256");HttpsURLConnection c=connexion(r.getString("url"),30000);
        try(InputStream in=c.getInputStream();OutputStream out=new FileOutputStream(temp)){
            byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1){taille+=n;if(taille>r.getLong("taille"))throw new SecurityException("Taille incorrecte.");h.update(b,0,n);out.write(b,0,n);}
        }catch(Exception e){temp.delete();throw e;}finally{c.disconnect();}
        if(taille!=r.getLong("taille")||!hex(h.digest()).equalsIgnoreCase(r.getString("sha256"))){temp.delete();throw new SecurityException("Fichier non authentique.");}
        PackageManager pm=contexte.getPackageManager();PackageInfo actuel=pm.getPackageInfo(contexte.getPackageName(),PackageManager.GET_SIGNATURES),candidat=pm.getPackageArchiveInfo(temp.getAbsolutePath(),PackageManager.GET_SIGNATURES);
        if(candidat==null||candidat.versionCode<=actuel.versionCode||!contexte.getPackageName().equals(candidat.packageName)||Catalogue.comparer(candidat.versionName,actuel.versionName)<=0||!candidat.versionName.equals(r.getString("version"))||!Arrays.equals(actuel.signatures,candidat.signatures)){temp.delete();throw new SecurityException("Signature ou version Android incorrecte.");}
        if(!temp.renameTo(apk))throw new IOException("Téléchargement non enregistré.");empreinteTelechargee=r.getString("sha256");coffre.audit("Mise à jour vérifiée "+r.getString("version"));return apk;
    }
    void installer() throws Exception {
        coffre.admin();File apk=new File(contexte.getCacheDir(),"patenteasy-update.apk");if(!apk.isFile()||empreinteTelechargee.isEmpty())throw new IOException("Téléchargez d’abord la mise à jour dans cette session.");MessageDigest digest=MessageDigest.getInstance("SHA-256");try(InputStream in=new FileInputStream(apk)){byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)digest.update(b,0,n);}if(!hex(digest.digest()).equalsIgnoreCase(empreinteTelechargee))throw new SecurityException("APK modifiée après vérification.");
        Intent i=new Intent(Intent.ACTION_VIEW).setDataAndType(Uri.parse("content://pf.ska987.patenteasy.local.updates/apk"),"application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_ACTIVITY_NEW_TASK);contexte.startActivity(i);
    }
}
