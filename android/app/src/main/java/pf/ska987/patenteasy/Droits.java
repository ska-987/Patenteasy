// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import org.json.*;
import java.util.*;
/** Contrôle natif des écritures d'un utilisateur, même sans passer par les boutons. */
final class Droits {
    static String canon(Object o) throws JSONException {
        if(o instanceof JSONObject){JSONObject j=(JSONObject)o;List<String> k=new ArrayList<>();Iterator<String> i=j.keys();while(i.hasNext())k.add(i.next());Collections.sort(k);StringBuilder s=new StringBuilder("{");for(String n:k){if(s.length()>1)s.append(',');s.append(JSONObject.quote(n)).append(':').append(canon(j.get(n)));}return s.append('}').toString();}
        if(o instanceof JSONArray){JSONArray a=(JSONArray)o;StringBuilder s=new StringBuilder("[");for(int i=0;i<a.length();i++){if(i>0)s.append(',');s.append(canon(a.get(i)));}return s.append(']').toString();}
        if(o instanceof String)return JSONObject.quote((String)o);return String.valueOf(o);
    }
    static void egal(Object a,Object b) throws Exception {if(!canon(a).equals(canon(b)))throw new SecurityException("Cette modification nécessite un administrateur.");}
    static Map<String,JSONObject> index(JSONArray a) throws Exception {Map<String,JSONObject> m=new HashMap<>();for(int i=0;i<a.length();i++){JSONObject j=a.getJSONObject(i);String id=j.getString("id");if(m.put(id,j)!=null)throw new SecurityException("Identifiant en double.");}return m;}
    static void valider(String avant,JSONObject apres) throws Exception {
        if(avant.isEmpty())throw new SecurityException("L'administrateur doit configurer l'entreprise.");JSONObject a=new JSONObject(avant);
        egal(a.get("entreprise"),apres.get("entreprise"));egal(a.getJSONObject("sequences").get("av"),apres.getJSONObject("sequences").get("av"));
        Map<String,JSONObject> anciens=index(a.getJSONArray("journal")),nouveaux=index(apres.getJSONArray("journal"));
        for(String id:anciens.keySet()){if(!nouveaux.containsKey(id))throw new SecurityException("Suppression du journal interdite.");egal(anciens.get(id),nouveaux.get(id));}
        Map<String,JSONObject> facts=index(apres.getJSONArray("factures"));
        for(String id:nouveaux.keySet())if(!anciens.containsKey(id)){JSONObject j=nouveaux.get(id);if(!"depense".equals(j.getString("type"))){JSONObject f=facts.get(j.optString("factureId"));boolean lie=false;if(f!=null){JSONArray ps=f.getJSONArray("paiements");for(int i=0;i<ps.length();i++){JSONObject p=ps.getJSONObject(i);if(id.equals(p.getString("journalId"))&&p.getLong("montant")==j.getLong("montant"))lie=true;}}if(!lie)throw new SecurityException("Encaissez depuis la facture.");}}
        Map<String,JSONObject> devis=index(apres.getJSONArray("devis"));JSONArray precedents=a.getJSONArray("devis");for(int i=0;i<precedents.length();i++){JSONObject q=precedents.getJSONObject(i);if(q.has("instantane")){JSONObject n=devis.get(q.getString("id"));if(n==null)throw new SecurityException("Suppression de devis émis interdite.");egal(q.get("instantane"),n.get("instantane"));}}
        Map<String,JSONObject> olds=index(a.getJSONArray("factures"));
        for(String id:olds.keySet()){JSONObject f=facts.get(id),old=olds.get(id);if(f==null)throw new SecurityException("Suppression de facture interdite.");egal(old.get("instantane"),f.get("instantane"));egal(old.get("type"),f.get("type"));JSONArray op=old.getJSONArray("paiements"),np=f.getJSONArray("paiements");if(np.length()<op.length())throw new SecurityException("Suppression de paiement interdite.");for(int i=0;i<op.length();i++)egal(op.get(i),np.get(i));}
        for(String id:facts.keySet())if(!olds.containsKey(id)&&!"facture".equals(facts.get(id).getString("type")))throw new SecurityException("Avoir réservé à l'administrateur.");
    }
    static void restauration(JSONObject avant,JSONObject apres) throws Exception {
        for(String k:new String[]{"dev","fact","av"})if(apres.getJSONObject("sequences").getLong(k)<avant.getJSONObject("sequences").getLong(k))throw new SecurityException("Cette sauvegarde ferait reculer la numérotation. Restauration refusée.");
        for(String k:new String[]{"devis","factures"}){Map<String,JSONObject> candidats=index(apres.getJSONArray(k));JSONArray docs=avant.getJSONArray(k);for(int i=0;i<docs.length();i++){JSONObject d=docs.getJSONObject(i);if(d.has("instantane")){JSONObject c=candidats.get(d.getString("id"));if(c==null)throw new SecurityException("Un document émis serait perdu.");egal(d.get("instantane"),c.get("instantane"));}}}
    }
}
