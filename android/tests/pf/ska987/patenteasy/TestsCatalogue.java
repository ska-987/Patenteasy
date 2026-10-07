package pf.ska987.patenteasy;
import java.nio.file.*;import org.json.*;
public class TestsCatalogue {
 public static void main(String[] args)throws Exception{Path d=Paths.get(args[0]);JSONObject catalogue=new JSONObject(Files.readString(d.resolve("catalogue.json")));String cle=Files.readString(d.resolve("publique.txt"));JSONObject versions=Catalogue.versions(catalogue,cle);if(!Catalogue.canon(versions).equals(Files.readString(d.resolve("canonique.txt"))))throw new AssertionError("Canonicalisation différente de Python.");if(Catalogue.comparer("0.3.10","0.3.9")<=0)throw new AssertionError("Version lexicographique");catalogue.getJSONObject("versions").getJSONObject("android").put("taille",1);boolean refus=false;try{Catalogue.versions(catalogue,cle);}catch(Exception e){refus=true;}if(!refus)throw new AssertionError("Signature altérée acceptée");System.out.println("3 contrôles du catalogue réussis : Unicode, versions, signature altérée.");}
}
