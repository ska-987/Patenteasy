package android.content;
public interface SharedPreferences {long getLong(String key,long value);String getString(String key,String value);Editor edit();interface Editor{Editor putLong(String key,long value);Editor putString(String key,String value);Editor remove(String key);boolean commit();}}
