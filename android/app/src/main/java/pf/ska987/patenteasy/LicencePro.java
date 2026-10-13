// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import org.json.*;import java.util.*;import java.time.*;import java.security.*;import java.nio.charset.StandardCharsets;
import net.i2p.crypto.eddsa.*;import net.i2p.crypto.eddsa.spec.*;
final class LicencePro {
 static JSONObject verifier(String texte,String publique,String entreprise,long maintenant,long dernier) throws Exception {
  JSONObject r=new JSONObject().put("active",false).put("modules",new JSONArray()).put("message","Licence annuelle requise.");
  if(publique.isEmpty())return r.put("message","Clé publique de ska_987 non configurée. Activation indisponible.");
  if(texte.isEmpty())return r;
  try {
   if(texte.getBytes(StandardCharsets.UTF_8).length>65536)throw new SecurityException("Licence trop volumineuse.");
   JSONObject l=new JSONObject(texte);if(l.length()!=2)throw new SecurityException("Licence invalide.");JSONObject p=l.getJSONObject("payload");
   if(!"ska-license-v1".equals(p.getString("schema"))||!"patenteasy".equals(p.getString("app_id")))throw new SecurityException("Licence destinée à une autre application.");
   String sig=l.getString("signature");if(!sig.matches("[A-Za-z0-9_-]{86}"))throw new SecurityException("Signature invalide.");
   EdDSAParameterSpec spec=EdDSANamedCurveTable.getByName("Ed25519");EdDSAPublicKey key=new EdDSAPublicKey(new EdDSAPublicKeySpec(Base64.getDecoder().decode(publique),spec));
   java.security.Signature v=new EdDSAEngine(MessageDigest.getInstance("SHA-512"));v.initVerify(key);v.update(Catalogue.canon(p).getBytes(StandardCharsets.UTF_8));if(!v.verify(Base64.getUrlDecoder().decode(sig+"==")))throw new SecurityException("Signature invalide.");
   if(p.getString("customer_id").isEmpty()||p.getString("license_id").isEmpty())throw new SecurityException("Licence incomplète.");
   for(String k:new String[]{"employees","sites"}){Object valeur=p.getJSONObject("limits").get(k);if(!(valeur instanceof Integer||valeur instanceof Long)||((Number)valeur).longValue()<1)throw new SecurityException("Limites invalides.");}
   String nom=p.getString("customer_name");if(entreprise.trim().isEmpty()||!nom.trim().replaceAll("\\s+"," ").equalsIgnoreCase(entreprise.trim().replaceAll("\\s+"," ")))throw new SecurityException("Cette licence ne correspond pas au nom de votre entreprise.");
   long debut=Instant.parse(p.getString("not_before")).toEpochMilli(),fin=Instant.parse(p.getString("expires_at")).toEpochMilli(),emission=Instant.parse(p.getString("issued_at")).toEpochMilli();
   if(fin<=debut||emission>fin)throw new SecurityException("Dates de licence invalides.");
   r.put("titulaire",nom).put("expiration",p.getString("expires_at"));
   if(maintenant<dernier-300000)return r.put("message","Horloge reculée. Vérifiez la date de cet appareil.");
   if(maintenant<debut||maintenant<emission)return r.put("message","Licence pas encore active.");
   if(maintenant>=fin)return r.put("message","Licence expirée. La facturation gratuite reste disponible.");
   JSONArray modules=new JSONArray(),features=p.getJSONArray("features");for(int i=0;i<features.length();i++){String f=features.getString(i);if((f.equals("finance_tva")||f.equals("administratif"))&&!modules.toString().contains('"'+f+'"'))modules.put(f);}
   return r.put("active",true).put("modules",modules).put("message","Licence active.");
  } catch(Exception e){return r.put("message",e.getMessage()==null?"Licence invalide.":e.getMessage());}
 }
 static void exiger(JSONObject etat,String module) throws Exception {
  if(!etat.getBoolean("active"))throw new SecurityException(etat.getString("message"));JSONArray ms=etat.getJSONArray("modules");for(int i=0;i<ms.length();i++)if(module.equals(ms.getString(i)))return;
  throw new SecurityException("Licence annuelle requise pour ce module.");
 }
}
