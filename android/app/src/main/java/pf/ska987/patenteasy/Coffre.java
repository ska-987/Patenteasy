// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.AtomicFile;
import android.util.Base64;
import org.json.*;
import javax.crypto.*;
import javax.crypto.spec.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;

/** Coffre local AES-GCM. Les mots de passe enveloppent une clé aléatoire commune. */
public final class Coffre {
    private final AtomicFile fichier;
    private final SharedPreferences ancien;
    private JSONObject enveloppe;
    private JSONObject contenu;
    private byte[] cle;
    private String compte="";
    private long derniereAction;
    private int echecs;
    private long attendre;
    private static final int ITERATIONS=600000;
    public Coffre(Context context) throws Exception {
        fichier=new AtomicFile(new File(context.getFilesDir(),"coffre-v1.json"));
        ancien=context.getSharedPreferences("patenteasy_local",Context.MODE_PRIVATE);
        if(fichier.getBaseFile().exists()) enveloppe=new JSONObject(new String(lire(fichier.openRead(),16000000),StandardCharsets.UTF_8));
    }
    static byte[] lire(InputStream in,int maximum) throws IOException {
        try(InputStream source=in;ByteArrayOutputStream out=new ByteArrayOutputStream()){
            byte[] bloc=new byte[65536];int n;
            while((n=source.read(bloc))!=-1){if(out.size()+n>maximum)throw new IOException("Fichier trop volumineux.");out.write(bloc,0,n);}return out.toByteArray();
        }
    }
    static byte[] aleatoire(int taille){byte[] b=new byte[taille];new SecureRandom().nextBytes(b);return b;}
    static String b64(byte[] b){return Base64.encodeToString(b,Base64.NO_WRAP);}
    static byte[] deb64(String s){return Base64.decode(s,Base64.DEFAULT);}
    static byte[] derive(String mot,byte[] sel,int iterations) throws Exception {
        if(iterations<600000||iterations>1200000)throw new SecurityException("Paramètres de clé invalides.");
        PBEKeySpec spec=new PBEKeySpec(mot.toCharArray(),sel,iterations,256);
        try{return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();}finally{spec.clearPassword();}
    }
    static JSONObject chiffrer(byte[] key,byte[] data,String aad) throws Exception {
        byte[] nonce=aleatoire(12);Cipher c=Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE,new SecretKeySpec(key,"AES"),new GCMParameterSpec(128,nonce));c.updateAAD(aad.getBytes(StandardCharsets.UTF_8));
        return new JSONObject().put("nonce",b64(nonce)).put("contenu",b64(c.doFinal(data)));
    }
    static byte[] dechiffrer(byte[] key,JSONObject data,String aad) throws Exception {
        Cipher c=Cipher.getInstance("AES/GCM/NoPadding");c.init(Cipher.DECRYPT_MODE,new SecretKeySpec(key,"AES"),new GCMParameterSpec(128,deb64(data.getString("nonce"))));
        c.updateAAD(aad.getBytes(StandardCharsets.UTF_8));return c.doFinal(deb64(data.getString("contenu")));
    }
    private static JSONObject envelopper(byte[] key,String mot,String aad) throws Exception {
        byte[] sel=aleatoire(32),derivee=derive(mot,sel,ITERATIONS);
        try{return chiffrer(derivee,key,aad).put("sel",b64(sel)).put("iterations",ITERATIONS);}finally{Arrays.fill(derivee,(byte)0);}
    }
    private static byte[] ouvrirCle(JSONObject wrap,String mot,String aad) throws Exception {
        byte[] d=derive(mot,deb64(wrap.getString("sel")),wrap.getInt("iterations"));
        try{return dechiffrer(d,wrap,aad);}finally{Arrays.fill(d,(byte)0);}
    }
    private void ecrire(JSONObject candidat) throws Exception {
        FileOutputStream out=null;try{out=fichier.startWrite();out.write(candidat.toString().getBytes(StandardCharsets.UTF_8));fichier.finishWrite(out);enveloppe=candidat;}catch(Exception e){if(out!=null)fichier.failWrite(out);throw e;}
    }
    private void sauvegarder() throws Exception {
        JSONObject candidat=new JSONObject(enveloppe.toString());
        candidat.put("donnees",chiffrer(cle,contenu.toString().getBytes(StandardCharsets.UTF_8),"Patenteasy Android coffre 1"));ecrire(candidat);
    }
    public synchronized boolean existe(){return enveloppe!=null;}
    private JSONObject comptes() throws Exception{return enveloppe.getJSONObject("comptes");}
    private JSONObject utilisateur() throws Exception{return comptes().getJSONObject(compte);}
    public synchronized void exiger() throws Exception {
        if(cle==null)throw new SecurityException("Session verrouillée.");
        if(System.currentTimeMillis()-derniereAction>utilisateur().optJSONObject("preferences").optInt("verrouillage",15)*60000L){verrouiller();throw new SecurityException("Session verrouillée.");}
    }
    public synchronized void toucher(){if(cle!=null){try{exiger();derniereAction=System.currentTimeMillis();}catch(Exception ignore){}}}
    public synchronized void admin() throws Exception {exiger();if(!"admin".equals(utilisateur().getString("role")))throw new SecurityException("Réservé à l’administrateur.");}
    private static String nom(String id){String n=id.trim().toLowerCase(Locale.ROOT);if(!n.matches("[a-z0-9_.-]{3,40}"))throw new IllegalArgumentException("Identifiant : 3 à 40 lettres, chiffres, points ou tirets.");return n;}
    private static void mot(String mot){if(mot.length()<12||mot.length()>256)throw new IllegalArgumentException("Choisissez un mot de passe de 12 caractères minimum.");}
    private JSONObject nouveau(String id,String password,String role) throws Exception {mot(password);return new JSONObject().put("role",role).put("actif",true).put("cle",envelopper(cle,password,id+":"+role)).put("preferences",new JSONObject().put("theme","clair").put("accent","#285b9b").put("verrouillage",15));}
    public synchronized String creerAdmin(String id,String password) throws Exception {
        if(existe())throw new SecurityException("Le compte administrateur existe déjà.");id=nom(id);mot(password);
        String donnees=ancien.getString("donnees","");if(!donnees.isEmpty())valider(donnees);
        cle=aleatoire(32);compte=id;derniereAction=System.currentTimeMillis();
        contenu=new JSONObject().put("donnees",donnees).put("journal",new JSONArray());
        enveloppe=new JSONObject().put("format",1).put("comptes",new JSONObject());comptes().put(id,nouveau(id,password,"admin"));
        String secours=secours();sauvegarder();
        if(!ancien.edit().remove("donnees").commit())throw new IOException("Coffre créé. Redémarrez pour terminer la migration locale.");
        return secours;
    }
    private String secours() throws Exception {
        String code=b64(aleatoire(32)).replace('+','-').replace('/','_');enveloppe.put("recuperation",envelopper(cle,code,"recuperation"));return code;
    }
    public synchronized void connexion(String id,String password) throws Exception {
        if(System.currentTimeMillis()<attendre)throw new SecurityException("Patientez avant de réessayer.");id=nom(id);
        byte[] candidate=null;
        try{
            JSONObject u=comptes().getJSONObject(id);if(!u.getBoolean("actif"))throw new SecurityException();
            candidate=ouvrirCle(u.getJSONObject("cle"),password,id+":"+u.getString("role"));
            JSONObject data=new JSONObject(new String(dechiffrer(candidate,enveloppe.getJSONObject("donnees"),"Patenteasy Android coffre 1"),StandardCharsets.UTF_8));
            if(!data.getString("donnees").isEmpty())valider(data.getString("donnees"));
            cle=candidate;contenu=data;compte=id;derniereAction=System.currentTimeMillis();echecs=0;attendre=0;
            ancien.edit().remove("donnees").commit();audit("Connexion");
        }catch(Exception e){if(candidate!=null)Arrays.fill(candidate,(byte)0);echecs++;attendre=System.currentTimeMillis()+Math.min(60000,1000L*echecs*echecs);throw new SecurityException("Identifiant ou mot de passe incorrect, ou coffre inaccessible.");}
    }
    public synchronized String recuperer(String code,String password) throws Exception {
        mot(password);byte[] key=ouvrirCle(enveloppe.getJSONObject("recuperation"),code.trim(),"recuperation");
        JSONObject data=new JSONObject(new String(dechiffrer(key,enveloppe.getJSONObject("donnees"),"Patenteasy Android coffre 1"),StandardCharsets.UTF_8));
        String id=null;Iterator<String> it=comptes().keys();while(it.hasNext()){String n=it.next();if("admin".equals(comptes().getJSONObject(n).getString("role"))){id=n;break;}}
        if(id==null)throw new SecurityException("Administrateur absent.");cle=key;contenu=data;compte=id;derniereAction=System.currentTimeMillis();
        utilisateur().put("cle",envelopper(cle,password,id+":admin"));String nouveau=secours();audit("Récupération du compte administrateur");sauvegarder();return nouveau;
    }
    public synchronized void verrouiller(){if(cle!=null)Arrays.fill(cle,(byte)0);cle=null;contenu=null;compte="";}
    public synchronized boolean ouverte(){return cle!=null;}
    public synchronized String session() throws Exception {exiger();return new JSONObject().put("identifiant",compte).put("role",utilisateur().getString("role")).put("preferences",utilisateur().getJSONObject("preferences")).toString();}
    public synchronized String charger() throws Exception {exiger();return contenu.getString("donnees");}
    static JSONObject valider(String s) throws Exception {
        if(s.length()>10000000||s.getBytes(StandardCharsets.UTF_8).length>10000000)throw new IOException("Données trop volumineuses.");JSONObject d=new JSONObject(s);
        if(d.getInt("schema")!=2)throw new SecurityException("Données Android incompatibles.");
        for(String k:new String[]{"clients","articles","devis","factures","journal"}){JSONArray a=d.getJSONArray(k);if(a.length()>50000)throw new IOException("Trop de données.");}
        d.getJSONObject("sequences");return d;
    }
    public synchronized boolean sauver(String s) throws Exception {
        exiger();JSONObject d=valider(s);String avant=contenu.getString("donnees");
        if(!"admin".equals(utilisateur().getString("role")))Droits.valider(avant,d);
        contenu.put("donnees",s);try{sauvegarder();return true;}catch(Exception e){contenu.put("donnees",avant);throw e;}
    }
    public synchronized String listeComptes() throws Exception {
        admin();JSONArray a=new JSONArray();Iterator<String> it=comptes().keys();while(it.hasNext()){String n=it.next();JSONObject u=comptes().getJSONObject(n);a.put(new JSONObject().put("identifiant",n).put("role",u.getString("role")).put("actif",u.getBoolean("actif")));}return a.toString();
    }
    public synchronized void creerUtilisateur(String id,String password) throws Exception {admin();id=nom(id);if(comptes().length()>=200)throw new IllegalArgumentException("Limite de 200 comptes atteinte.");if(comptes().has(id))throw new IllegalArgumentException("Identifiant déjà utilisé.");comptes().put(id,nouveau(id,password,"utilisateur"));audit("Création du compte "+id);sauvegarder();}
    public synchronized void actif(String id,boolean actif) throws Exception {admin();JSONObject u=comptes().getJSONObject(id);if("admin".equals(u.getString("role")))throw new SecurityException("L’administrateur ne peut pas être désactivé.");u.put("actif",actif);audit((actif?"Activation ":"Désactivation ")+id);sauvegarder();}
    public synchronized void preferences(String json) throws Exception {
        exiger();JSONObject p=new JSONObject(json);if(!Arrays.asList("clair","sombre","personnalise").contains(p.getString("theme"))||!p.getString("accent").matches("#[0-9a-fA-F]{6}")||p.getInt("verrouillage")<1||p.getInt("verrouillage")>120)throw new IllegalArgumentException("Réglages invalides.");utilisateur().put("preferences",p);sauvegarder();
    }
    public synchronized void changerMot(String actuel,String nouveau) throws Exception {exiger();mot(nouveau);byte[] key=ouvrirCle(utilisateur().getJSONObject("cle"),actuel,compte+":"+utilisateur().getString("role"));if(!MessageDigest.isEqual(key,cle))throw new SecurityException("Mot de passe incorrect.");Arrays.fill(key,(byte)0);utilisateur().put("cle",envelopper(cle,nouveau,compte+":"+utilisateur().getString("role")));audit("Modification du mot de passe");sauvegarder();}
    public synchronized void audit(String action) throws Exception {
        exiger();JSONArray j=contenu.getJSONArray("journal");j.put(new JSONObject().put("date",System.currentTimeMillis()).put("compte",compte).put("action",action));if(j.length()>500){JSONArray dernier=new JSONArray();for(int i=j.length()-500;i<j.length();i++)dernier.put(j.get(i));contenu.put("journal",dernier);}sauvegarder();
    }
    public synchronized String journal() throws Exception {admin();return contenu.getJSONArray("journal").toString();}
    public synchronized byte[] backup() throws Exception {
        exiger();sauvegarder();JSONObject pack=new JSONObject().put("application","Patenteasy Android").put("format",1).put("date",System.currentTimeMillis()).put("coffre",enveloppe);
        return chiffrer(cle,pack.toString().getBytes(StandardCharsets.UTF_8),"Patenteasy Android sauvegarde 1").put("format","PATENTEASY-ANDROID-BACKUP-1").put("recuperation",enveloppe.getJSONObject("recuperation")).toString().getBytes(StandardCharsets.UTF_8);
    }
    public synchronized String restaurerNouveau(byte[] fichier,String code,String password) throws Exception {
        if(existe()||!ancien.getString("donnees","").isEmpty())throw new SecurityException("Des données locales existent déjà.");
        JSONObject blob=new JSONObject(new String(fichier,StandardCharsets.UTF_8));if(!"PATENTEASY-ANDROID-BACKUP-1".equals(blob.getString("format")))throw new SecurityException("Sauvegarde incompatible.");
        byte[] key=ouvrirCle(blob.getJSONObject("recuperation"),code.trim(),"recuperation");
        JSONObject pack=new JSONObject(new String(dechiffrer(key,blob,"Patenteasy Android sauvegarde 1"),StandardCharsets.UTF_8));JSONObject coffre=pack.getJSONObject("coffre");
        JSONObject data=new JSONObject(new String(dechiffrer(key,coffre.getJSONObject("donnees"),"Patenteasy Android coffre 1"),StandardCharsets.UTF_8));if(!data.getString("donnees").isEmpty())valider(data.getString("donnees"));
        // Tout vérifier avant la première écriture sur le nouveau téléphone.
        byte[] verification=ouvrirCle(coffre.getJSONObject("recuperation"),code.trim(),"recuperation");if(!MessageDigest.isEqual(key,verification))throw new SecurityException("Code incompatible.");Arrays.fill(key,(byte)0);Arrays.fill(verification,(byte)0);mot(password);
        ecrire(coffre);return recuperer(code,password);
    }
    public synchronized void restaurer(byte[] sauvegarde) throws Exception {
        admin();JSONObject blob=new JSONObject(new String(sauvegarde,StandardCharsets.UTF_8));if(!"PATENTEASY-ANDROID-BACKUP-1".equals(blob.getString("format")))throw new SecurityException("Sauvegarde Android chiffrée requise.");
        JSONObject pack=new JSONObject(new String(dechiffrer(cle,blob,"Patenteasy Android sauvegarde 1"),StandardCharsets.UTF_8));JSONObject coffre=pack.getJSONObject("coffre");
        JSONObject data=new JSONObject(new String(dechiffrer(cle,coffre.getJSONObject("donnees"),"Patenteasy Android coffre 1"),StandardCharsets.UTF_8));if(!data.getString("donnees").isEmpty())valider(data.getString("donnees"));
        // La restauration ne doit pas faire disparaître des documents émis ou reculer les compteurs.
        if(!contenu.getString("donnees").isEmpty()&&!data.getString("donnees").isEmpty())Droits.restauration(valider(contenu.getString("donnees")),valider(data.getString("donnees")));
        ecrire(coffre);verrouiller();
    }
}
