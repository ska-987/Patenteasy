// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import org.json.*;import java.math.BigDecimal;
/** Export volontaire des opérations, avec contrôle administrateur dans le pont natif. */
final class ExportCsv {
    private static String cellule(String s){if(s.trim().matches("(?s)^[=+@\\-].*"))s="'"+s;return "\""+s.replace("\"","\"\"")+"\"";}
    static String produire(String donnees)throws Exception{
        JSONObject d=new JSONObject(donnees);JSONArray journal=d.getJSONArray("journal");JSONObject profil=d.optJSONObject("entreprise");int precision=profil==null?2:profil.optInt("decimales",2);if(precision<0||precision>4)throw new IllegalArgumentException("Précision invalide.");String devise=profil==null?"XPF":profil.optString("devise","XPF");StringBuilder s=new StringBuilder("\ufeffDate;Libellé;Type;"+cellule("Montant "+devise)+"\r\n");
        for(int i=0;i<journal.length();i++){JSONObject j=journal.getJSONObject(i);String montant=BigDecimal.valueOf(j.getLong("montant"),precision).toPlainString().replace('.',',');s.append(cellule(j.getString("date"))).append(';').append(cellule(j.getString("libelle"))).append(';').append(cellule(j.getString("type"))).append(';').append(montant).append("\r\n");}return s.toString();
    }
}
