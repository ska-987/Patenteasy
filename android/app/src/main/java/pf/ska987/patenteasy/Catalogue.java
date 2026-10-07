// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import org.json.*;import java.util.*;import java.security.*;import java.nio.charset.StandardCharsets;
import net.i2p.crypto.eddsa.*;import net.i2p.crypto.eddsa.spec.*;
/** Validation du catalogue Ed25519 indépendante de l'interface et du réseau. */
final class Catalogue {
    private static String quote(String s){StringBuilder b=new StringBuilder("\"");for(int i=0;i<s.length();i++){char c=s.charAt(i);switch(c){case '"':b.append("\\\"");break;case '\\':b.append("\\\\");break;case '\b':b.append("\\b");break;case '\f':b.append("\\f");break;case '\n':b.append("\\n");break;case '\r':b.append("\\r");break;case '\t':b.append("\\t");break;default:if(c<32)b.append(String.format(Locale.ROOT,"\\u%04x",(int)c));else b.append(c);}}return b.append('"').toString();}
    static String canon(Object o) throws Exception {
        if(o instanceof JSONObject){JSONObject j=(JSONObject)o;List<String> k=new ArrayList<>();Iterator<String> it=j.keys();while(it.hasNext())k.add(it.next());Collections.sort(k);StringBuilder b=new StringBuilder("{");for(String n:k){if(b.length()>1)b.append(',');b.append(quote(n)).append(':').append(canon(j.get(n)));}return b.append('}').toString();}
        if(o instanceof JSONArray){JSONArray j=(JSONArray)o;StringBuilder b=new StringBuilder("[");for(int i=0;i<j.length();i++){if(i>0)b.append(',');b.append(canon(j.get(i)));}return b.append(']').toString();}
        if(o instanceof String)return quote((String)o);if(o instanceof Double||o instanceof Float)throw new SecurityException("Catalogue non entier.");return String.valueOf(o);
    }
    static int comparer(String a,String b){if(!a.matches("[0-9]+\\.[0-9]+\\.[0-9]+")||!b.matches("[0-9]+\\.[0-9]+\\.[0-9]+"))throw new IllegalArgumentException("Version invalide.");String[] x=a.split("\\."),y=b.split("\\.");for(int i=0;i<3;i++){int c=Integer.compare(Integer.parseInt(x[i]),Integer.parseInt(y[i]));if(c!=0)return c;}return 0;}

 static JSONObject versions(JSONObject catalogue,String publique) throws Exception {
   JSONObject versions=catalogue.getJSONObject("versions");
   EdDSAParameterSpec spec=EdDSANamedCurveTable.getByName("Ed25519");
   EdDSAPublicKey key=new EdDSAPublicKey(new EdDSAPublicKeySpec(Base64.getDecoder().decode(publique),spec));
   java.security.Signature verifier=new EdDSAEngine(MessageDigest.getInstance("SHA-512"));verifier.initVerify(key);verifier.update(canon(versions).getBytes(StandardCharsets.UTF_8));
   if(!verifier.verify(Base64.getDecoder().decode(catalogue.getString("signature"))))throw new SecurityException("Catalogue non authentique.");return versions;
 }
}
