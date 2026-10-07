package android.content;
import java.io.File;import java.util.*;
public class Context {
 public static final int MODE_PRIVATE=0;private final File dossier;private final Map<String,SharedPreferences> prefs=new HashMap<>();
 public Context(File d){dossier=d;d.mkdirs();}public File getFilesDir(){return dossier;}public SharedPreferences getSharedPreferences(String n,int mode){return prefs.computeIfAbsent(n,k->new Mem());}
 static class Mem implements SharedPreferences{Map<String,String> data=new HashMap<>();public String getString(String k,String v){return data.getOrDefault(k,v);}public Editor edit(){return new Ed();}class Ed implements Editor{Map<String,String> nouveaux=new HashMap<>();public Editor putString(String k,String v){nouveaux.put(k,v);return this;}public Editor remove(String k){nouveaux.put(k,null);return this;}public boolean commit(){for(String k:nouveaux.keySet()){if(nouveaux.get(k)==null)data.remove(k);else data.put(k,nouveaux.get(k));}return true;}}}
}
