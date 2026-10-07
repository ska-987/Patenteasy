// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import android.content.*;import android.database.*;import android.net.Uri;import android.os.ParcelFileDescriptor;import java.io.*;
/** Accès en lecture à l'unique APK déjà vérifiée, accordé seulement à l'installateur Android. */
public final class UpdateProvider extends ContentProvider {
    public boolean onCreate(){return true;}
    private void verifier(Uri u){if(!"/apk".equals(u.getPath()))throw new SecurityException("Fichier non autorisé.");}
    public String getType(Uri u){verifier(u);return "application/vnd.android.package-archive";}
    public ParcelFileDescriptor openFile(Uri u,String mode) throws FileNotFoundException {verifier(u);if(!"r".equals(mode))throw new SecurityException("Lecture seule.");return ParcelFileDescriptor.open(new File(getContext().getCacheDir(),"patenteasy-update.apk"),ParcelFileDescriptor.MODE_READ_ONLY);}
    public Cursor query(Uri u,String[] projection,String selection,String[] args,String sort){verifier(u);MatrixCursor c=new MatrixCursor(new String[]{"_display_name","_size"});File f=new File(getContext().getCacheDir(),"patenteasy-update.apk");c.addRow(new Object[]{f.getName(),f.length()});return c;}
    public Uri insert(Uri u,ContentValues v){throw new SecurityException();}public int delete(Uri u,String s,String[] a){throw new SecurityException();}public int update(Uri u,ContentValues v,String s,String[] a){throw new SecurityException();}
}
