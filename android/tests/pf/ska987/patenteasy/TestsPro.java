// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import org.json.*;import java.nio.file.*;import java.time.*;import android.content.Context;
public class TestsPro {
 static int n=0;static void ok(boolean v,String message){if(!v)throw new AssertionError(message);n++;}
 interface Action{void run()throws Exception;}static void refuse(Action f)throws Exception{try{f.run();throw new AssertionError("Action acceptée");}catch(SecurityException|IllegalArgumentException e){n++;}}
 public static void main(String[] args)throws Exception {
  JSONObject fixture=new JSONObject(Files.readString(Path.of(args[0])));String pub=fixture.getString("publique"),licence=fixture.getJSONObject("licence").toString();long now=fixture.getLong("now");
  JSONObject s=LicencePro.verifier(licence,pub,"Entreprise",now,0);ok(s.getBoolean("active"),"signature compatible Python / Java");LicencePro.exiger(s,"finance_tva");n++;
  ok(!LicencePro.verifier(licence,"","Entreprise",now,0).getBoolean("active"),"clé manquante");ok(!LicencePro.verifier(licence,pub,"Autre",now,0).getBoolean("active"),"titulaire");
  ok(!LicencePro.verifier(licence,pub,"Entreprise",now+366L*86400000,0).getBoolean("active"),"expiration");ok(!LicencePro.verifier(licence,pub,"Entreprise",now,now+3600000).getBoolean("active"),"horloge");
  JSONObject tamper=new JSONObject(licence);tamper.getJSONObject("payload").put("customer_name","Autre");ok(!LicencePro.verifier(tamper.toString(),pub,"Autre",now,0).getBoolean("active"),"altération");
  JSONObject d=fixture.getJSONObject("donnees"),r=FinancesPro.calculer(d,"2026-10-01","2026-10-31","reel",0);
  ok(r.getLong("tva_percue")==800&&r.getLong("tva_exigible")==800,"services à l'encaissement");ok(r.getLong("tva_deductible")==1600&&r.getLong("credit")==800,"achats et crédit");
  JSONObject franchise=FinancesPro.calculer(d,"2026-10-01","2026-10-31","franchise",0);ok(franchise.getLong("tva_deductible")==0&&franchise.getLong("a_reverser")==0,"franchise sans déduction");
  FinancesPro.valider(new JSONObject().put("journal",new JSONArray()),d);n++;
  JSONObject altered=new JSONObject(d.toString());altered.getJSONArray("journal").getJSONObject(1).put("montant",1);refuse(()->FinancesPro.valider(d,altered));
  Path tmp=Files.createTempDirectory("patenteasy-pro-tests");Coffre c=new Coffre(new Context(tmp.toFile()));c.creerAdmin("admin","Mot de passe test 2026 !");c.sauver(fixture.getJSONObject("vide").toString());
  refuse(()->c.exigerPro("finance_tva"));c.configurerLicence(pub);c.importerLicence(licence);c.exigerPro("finance_tva");n++;
  JSONObject data=new JSONObject(c.charger());data.put("achats_pro",d.getJSONArray("achats_pro"));data.put("journal",d.getJSONArray("journal"));c.sauver(data.toString());n++;
  c.creerUtilisateur("employe","Mot de passe employe test !");c.verrouiller();c.connexion("employe","Mot de passe employe test !");refuse(()->c.licenceEtat());refuse(()->c.importerLicence(licence));refuse(()->c.exigerPro("finance_tva"));
  System.out.println(n+" contrôles natifs du module et des licences réussis.");
 }
}
