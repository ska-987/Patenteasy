// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import org.json.*;import java.util.*;import java.time.LocalDate;import java.math.BigInteger;
/** Calculs natifs entiers : l'interface ne fournit jamais ses propres totaux fiscaux. */
final class FinancesPro {
 static long entier(JSONObject j,String k) throws Exception {Object o=j.get(k);if(!(o instanceof Long||o instanceof Integer)||((Number)o).longValue()<0||((Number)o).longValue()>9000000000000L)throw new IllegalArgumentException("Montant entier invalide.");return ((Number)o).longValue();}
 static String jour(String s){if(!LocalDate.parse(s).toString().equals(s))throw new IllegalArgumentException("Date invalide.");return s;}
 static long proportion(long v,long p,long t){if(t<=0)return 0;return BigInteger.valueOf(v).multiply(BigInteger.valueOf(Math.min(p,t))).add(BigInteger.valueOf(t/2)).divide(BigInteger.valueOf(t)).longValueExact();}
 static JSONArray vide(JSONObject d,String k){JSONArray a=d.optJSONArray(k);return a==null?new JSONArray():a;}
 static JSONObject objet(JSONObject d,String k){JSONObject a=d.optJSONObject(k);return a==null?new JSONObject():a;}
 static long total(JSONArray ls,String k) throws Exception {long n=0;for(int i=0;i<ls.length();i++)n=Math.addExact(n,entier(ls.getJSONObject(i),k));return n;}
 static void valider(JSONObject avant,JSONObject apres) throws Exception {
  JSONArray achats=vide(apres,"achats_pro");if(achats.length()>50000)throw new IllegalArgumentException("Trop d’achats.");
  Map<String,JSONObject> ops=Droits.index(apres.getJSONArray("journal"));Set<String> ids=new HashSet<>(),liens=new HashSet<>();
  for(int i=0;i<achats.length();i++){
   JSONObject a=achats.getJSONObject(i);if(!ids.add(a.getString("id")))throw new SecurityException("Achats en double.");String date=jour(a.getString("date"));
   if(date.compareTo(LocalDate.now().toString())>0||a.getString("fournisseur").trim().isEmpty()||a.getString("reference").trim().isEmpty())throw new IllegalArgumentException("Vérifiez l’achat.");
   JSONArray ls=a.getJSONArray("lignes");if(ls.length()<1||ls.length()>100)throw new IllegalArgumentException("Lignes d’achat invalides.");
   for(int n=0;n<ls.length();n++){
    JSONObject l=ls.getJSONObject(n);long ht=entier(l,"ht"),taux=entier(l,"taux"),tv=entier(l,"tva"),ttc=entier(l,"ttc"),ded=entier(l,"deduction");
    if(taux>10000||ded>10000||Math.abs(tv-proportion(ht,taux,10000))>1||ttc!=ht+tv)throw new IllegalArgumentException("Vérifiez HT / taux / TVA / TTC.");
    String nature=l.getString("nature");if(!Arrays.asList("bien","service","debits").contains(nature))throw new IllegalArgumentException("Nature d’achat invalide.");
    if(nature.equals("bien")&&a.optString("livraison").isEmpty())throw new IllegalArgumentException("Date de livraison nécessaire.");
    if(nature.equals("debits")&&!a.optBoolean("autorisation_debits"))throw new SecurityException("Confirmez l’autorisation pour les débits.");
   }
   if(!a.optString("livraison").isEmpty())jour(a.getString("livraison"));
   long paye=0;JSONArray ps=a.getJSONArray("paiements");for(int n=0;n<ps.length();n++){
    JSONObject p=ps.getJSONObject(n);long m=entier(p,"montant");String pj=jour(p.getString("date"));if(m==0||pj.compareTo(date)<0||pj.compareTo(LocalDate.now().toString())>0)throw new IllegalArgumentException("Règlement fournisseur invalide.");
    String id=p.getString("journalId");JSONObject op=ops.get(id);if(!liens.add(id)||op==null||!a.getString("id").equals(op.optString("achatId"))||!pj.equals(op.getString("date"))||m!=entier(op,"montant")||!"depense".equals(op.getString("type")))throw new SecurityException("Règlement fournisseur absent du journal.");paye=Math.addExact(paye,m);
   }
   if(paye>total(ls,"ttc")||total(ls,"ttc")<=0)throw new IllegalArgumentException("Règlement supérieur au total fournisseur.");
  }
  for(JSONObject a:Droits.index(vide(avant,"achats_pro")).values()){
   JSONObject n=Droits.index(achats).get(a.getString("id"));if(n==null)throw new SecurityException("Suppression d’achat interdite.");
   for(String k:new String[]{"lignes","date","livraison","fournisseur","reference","justificatif"})Droits.egal(a.opt(k),n.opt(k));
   JSONArray ps=a.getJSONArray("paiements"),ns=n.getJSONArray("paiements");if(ns.length()<ps.length())throw new SecurityException("Suppression de règlement fournisseur interdite.");
   for(int i=0;i<ps.length();i++)Droits.egal(ps.get(i),ns.get(i));
  }
  Map<String,JSONObject> oldops=Droits.index(vide(avant,"journal"));for(JSONObject op:oldops.values())if(op.has("achatId")){JSONObject n=ops.get(op.getString("id"));if(n==null)throw new SecurityException("Suppression de règlement interdite.");Droits.egal(op,n);}
  JSONObject qualifications=objet(apres,"qualifications_pro");Iterator<String> it=qualifications.keys();Map<String,JSONObject> facts=Droits.index(apres.getJSONArray("factures"));while(it.hasNext()){
   String id=it.next();JSONObject q=qualifications.getJSONObject(id),f=facts.get(id);if(f==null||!"facture".equals(f.getString("type")))throw new IllegalArgumentException("Facture à qualifier introuvable.");
   JSONArray ns=q.getJSONArray("natures");if(ns.length()!=f.getJSONObject("instantane").getJSONArray("lignes").length())throw new IllegalArgumentException("Qualifiez toutes les lignes.");
   for(int i=0;i<ns.length();i++){String n=ns.getString(i);if(!Arrays.asList("bien","service","debits").contains(n))throw new IllegalArgumentException("Nature invalide.");if(n.equals("debits")&&!q.optBoolean("autorisation_debits"))throw new SecurityException("Confirmez l’autorisation DICP.");if(n.equals("bien"))jour(q.getString("livraison"));}
  }
 }
 static List<JSONObject> evenements(JSONArray lignes,long total,JSONArray paiements,String date,String livraison) throws Exception {
  TreeMap<String,Long> etapes=new TreeMap<>();etapes.put(date,0L);if(!livraison.isEmpty())etapes.put(livraison,0L);
  for(int i=0;i<paiements.length();i++){JSONObject p=paiements.getJSONObject(i);String j=p.getString("date");etapes.put(j,etapes.getOrDefault(j,0L)+p.getLong("montant"));}
  long paye=0;long[][] deja=new long[lignes.length()][3];List<JSONObject> sortie=new ArrayList<>();
  for(Map.Entry<String,Long> e:etapes.entrySet()){paye+=e.getValue();for(int i=0;i<lignes.length();i++){
   JSONObject l=lignes.getJSONObject(i);String nature=l.optString("nature","inconnue");boolean complet=nature.equals("bien")&&!livraison.isEmpty()&&e.getKey().compareTo(livraison)>=0||nature.equals("debits")&&e.getKey().compareTo(date)>=0;
   long ht=complet?l.getLong("ht"):proportion(l.getLong("ht"),paye,total),tv=complet?l.getLong("tva"):proportion(l.getLong("tva"),paye,total);long deduction=proportion(tv,l.optLong("deduction",0),10000);
   if(ht!=deja[i][0]||tv!=deja[i][1])sortie.add(new JSONObject().put("date",e.getKey()).put("ht",ht-deja[i][0]).put("tva",tv-deja[i][1]).put("deduction",deduction-deja[i][2]).put("taux",l.getLong("taux")).put("categorie",l.optString("categorie","autres")));
   deja[i][0]=ht;deja[i][1]=tv;deja[i][2]=deduction;
  }}return sortie;
 }
 static JSONObject groupe(TreeMap<Long,JSONObject> gs,long taux) throws Exception {if(!gs.containsKey(taux)){JSONObject g=new JSONObject().put("taux",taux);for(String k:new String[]{"base_exigible","tva_exigible","tva_percue","base_achats","tva_achats","tva_deductible"})g.put(k,0L);gs.put(taux,g);}return gs.get(taux);}
 static void ajouter(JSONObject g,String k,long v) throws Exception {g.put(k,g.getLong(k)+v);}
 static boolean periode(String j,String debut,String fin){return j.compareTo(debut)>=0&&j.compareTo(fin)<=0;}
 static JSONObject calculer(JSONObject d,String debut,String fin,String regime,long credit) throws Exception {
  jour(debut);jour(fin);if(fin.compareTo(debut)<0||!Arrays.asList("","franchise","reel").contains(regime)||credit<0)throw new IllegalArgumentException("Période / régime / crédit invalide.");
  boolean reel=regime.equals("reel");TreeMap<Long,JSONObject> gs=new TreeMap<>();JSONArray alertes=new JSONArray();long percue=0,exigible=0,deductible=0,immob=0;
  JSONArray facts=d.getJSONArray("factures");JSONObject qualifications=objet(d,"qualifications_pro");
  for(int i=0;i<facts.length();i++){
   JSONObject f=facts.getJSONObject(i),s=f.getJSONObject("instantane");String date=s.getString("date");if(date.compareTo(fin)>0)continue;
   if("avoir".equals(f.getString("type"))){if(periode(date,debut,fin))alertes.put("Avoir "+s.getString("numero")+" : vérifier sa régularisation TVA.");continue;}
   JSONObject q=qualifications.optJSONObject(f.getString("id"));if(q==null)alertes.put("Facture "+s.getString("numero")+" : nature / livraison à confirmer.");
   JSONArray lignes=new JSONArray(),cash=new JSONArray(),original=s.getJSONArray("lignes");
   for(int n=0;n<original.length();n++){
    JSONObject l=original.getJSONObject(n);long ht=proportion(l.getLong("prix"),l.getLong("quantite"),100),taux=l.getLong("taux"),tv="reel".equals(s.getString("regime"))?proportion(ht,taux,10000):0;
    JSONObject v=new JSONObject().put("ht",ht).put("tva",tv).put("taux",taux).put("nature",q==null?"inconnue":q.getJSONArray("natures").getString(n));lignes.put(v);cash.put(new JSONObject(v.toString()).put("nature","service"));
   }
   for(JSONObject e:evenements(lignes,s.getJSONObject("totaux").getLong("ttc"),f.getJSONArray("paiements"),date,q==null?"":q.optString("livraison")))if(periode(e.getString("date"),debut,fin)){
    JSONObject g=groupe(gs,e.getLong("taux"));ajouter(g,"base_exigible",e.getLong("ht"));if(reel){ajouter(g,"tva_exigible",e.getLong("tva"));exigible+=e.getLong("tva");}
   }
   for(JSONObject e:evenements(cash,s.getJSONObject("totaux").getLong("ttc"),f.getJSONArray("paiements"),date,""))if(reel&&periode(e.getString("date"),debut,fin)){ajouter(groupe(gs,e.getLong("taux")),"tva_percue",e.getLong("tva"));percue+=e.getLong("tva");}
  }
  JSONArray achats=vide(d,"achats_pro");Set<String> liens=new HashSet<>();
  for(int i=0;i<achats.length();i++){
   JSONObject a=achats.getJSONObject(i);JSONArray ls=a.getJSONArray("lignes"),ps=a.getJSONArray("paiements");for(int n=0;n<ps.length();n++)liens.add(ps.getJSONObject(n).getString("journalId"));
   if(!a.optBoolean("justificatif"))alertes.put("Achat "+a.getString("reference")+" : justificatif manquant, déduction exclue.");
   for(JSONObject e:evenements(ls,total(ls,"ttc"),ps,a.getString("date"),a.optString("livraison")))if(periode(e.getString("date"),debut,fin)){
    JSONObject g=groupe(gs,e.getLong("taux"));ajouter(g,"base_achats",e.getLong("ht"));ajouter(g,"tva_achats",e.getLong("tva"));long ded=reel&&a.optBoolean("justificatif")?e.getLong("deduction"):0;ajouter(g,"tva_deductible",ded);deductible+=ded;if("immobilisation".equals(e.getString("categorie")))immob+=ded;
   }
  }
  long anciens=0,recettes=0,depenses=0;JSONArray ops=d.getJSONArray("journal");for(int i=0;i<ops.length();i++){JSONObject op=ops.getJSONObject(i);if(!periode(op.getString("date"),debut,fin))continue;if("recette".equals(op.getString("type")))recettes+=op.getLong("montant");else {depenses+=op.getLong("montant");if(!liens.contains(op.getString("id"))&&!op.has("remboursementId"))anciens++;}}
  if(anciens>0)alertes.put(anciens+" dépense(s) sans détail HT / TVA : à rapprocher.");if(regime.isEmpty())alertes.put("Régime TVA de la période à confirmer.");
  long ajust=0;JSONArray corrections=vide(d,"ajustements_pro");for(int i=0;i<corrections.length();i++){JSONObject a=corrections.getJSONObject(i);if(periode(a.getString("date"),debut,fin))ajust+=a.getLong("montant");}
  long net=reel?exigible-deductible-credit+ajust:0;JSONArray taux=new JSONArray();for(JSONObject g:gs.values())taux.put(g);
  return new JSONObject().put("debut",debut).put("fin",fin).put("regime",regime).put("tva_percue",percue).put("tva_exigible",exigible).put("tva_deductible",deductible).put("deduction_immobilisation",immob).put("credit_precedent",reel?credit:0).put("regularisations",reel?ajust:0).put("a_reverser",Math.max(0,net)).put("credit",Math.max(0,-net)).put("taux",taux).put("alertes",alertes).put("recettes_ttc",recettes).put("depenses_ttc",depenses);
 }
}
