// SPDX-License-Identifier: GPL-3.0-or-later
package pf.ska987.patenteasy;
import android.graphics.*;
import android.graphics.pdf.PdfDocument;
import android.os.Build;
import android.text.*;
import android.text.style.StyleSpan;
import org.json.*;
import java.io.*;
import java.math.BigDecimal;
import java.util.*;

/** PDF vectoriel : texte Unicode, tableau paginé et conditions au bas du document. */
final class DocumentPdf {
    private static String date(String iso){return iso.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}")?iso.substring(8)+"/"+iso.substring(5,7)+"/"+iso.substring(2,4):iso;}
    private static String monnaie(long n,JSONObject e){int p=e.optInt("decimales",2);if(p<0||p>4)throw new IllegalArgumentException("Précision invalide.");return BigDecimal.valueOf(n,p).setScale(p).toPlainString().replace('.',',')+" "+e.optString("devise","XPF");}
    private static String nombre(long n){return BigDecimal.valueOf(n,2).stripTrailingZeros().toPlainString().replace('.',',');}
    private static StaticLayout texte(CharSequence s,int largeur,int taille,boolean gras){
        TextPaint p=new TextPaint(Paint.ANTI_ALIAS_FLAG);p.setColor(Color.rgb(23,37,54));p.setTextSize(taille);p.setTypeface(gras?Typeface.DEFAULT_BOLD:Typeface.DEFAULT);
        StaticLayout.Builder b=StaticLayout.Builder.obtain(s,0,s.length(),p,largeur).setAlignment(Layout.Alignment.ALIGN_NORMAL)
            .setTextDirection(TextDirectionHeuristics.FIRSTSTRONG_LTR).setIncludePad(false).setLineSpacing(2,1);
        if(Build.VERSION.SDK_INT>=28)b.setUseLineSpacingFromFallbacks(true);return b.build();
    }
    static void produire(String donnees,OutputStream flux)throws Exception {
        JSONObject enveloppe=new JSONObject(donnees),s=enveloppe.getJSONObject("document"),e=s.getJSONObject("entreprise"),c=s.getJSONObject("client");
        String type=enveloppe.getString("type"),numero=s.getString("numero");if(!Arrays.asList("Devis","Facture","Avoir").contains(type))throw new IOException("Type de document invalide.");
        try(Pages p=new Pages(type+" "+numero)){
            p.bloc(type+" "+numero,20,true,false);p.bloc(e.getString("nom"),13,true,false);
            String societe=e.optString("adresse","");
            if(!e.optString("tahiti","").isEmpty())societe+="\n"+e.optString("identifiantLibelle","Identifiant")+" : "+e.getString("tahiti");
            if(!e.optString("rcs","").isEmpty())societe+="\n"+e.getString("rcs");
            if(!e.optString("telephone","").isEmpty())societe+="\n"+e.getString("telephone");
            if(!e.optString("email","").isEmpty())societe+="\n"+e.getString("email");
            p.bloc(societe.trim(),10,false,false);p.y+=8;p.bloc(c.getString("nom"),12,true,false);
            p.bloc((c.optString("adresse","")+"\n"+c.optString("email","")).trim(),10,false,false);
            String dates="Date : "+date(s.getString("date"));if(s.has("echeance"))dates+=" · Échéance : "+date(s.getString("echeance"));
            if("Devis".equals(type))dates+=" · Validité : "+s.optInt("validite",30)+" jours";p.bloc(dates,10,false,false);
            if(s.has("numeroDevis"))p.bloc("Devis : "+s.getString("numeroDevis"),10,false,false);
            if(s.has("numeroFacture"))p.bloc("Facture corrigée : "+s.getString("numeroFacture"),10,false,false);
            p.bloc(s.optString("objet",""),12,true,false);p.y+=8;
            String taxe=e.optString("taxeLibelle","TVA");String[] entetes={"Référence","Désignation","Qté","PU HT",taxe};p.entete(entetes);
            JSONArray lignes=s.getJSONArray("lignes");if(lignes.length()>300)throw new IOException("Trop de lignes.");
            for(int i=0;i<lignes.length();i++){
                JSONObject l=lignes.getJSONObject(i);p.ligne(new String[]{l.optString("reference",""),l.getString("designation"),nombre(l.getLong("quantite"))+" "+l.optString("unite",""),monnaie(l.getLong("prix"),e),"reel".equals(s.optString("regime"))?nombre(l.getLong("taux"))+" %":"—"},entetes);
            }
            JSONObject t=s.getJSONObject("totaux");p.y+=12;if(p.y+70>Pages.BAS)p.nouvelle();
            p.bloc("HT : "+monnaie(t.getLong("ht"),e),11,false,false);p.bloc(taxe+" : "+monnaie(t.getLong("tva"),e),11,false,false);
            p.bloc(("Avoir".equals(type)?"Total à créditer : ":"Total : ")+monnaie(t.getLong("ttc"),e),14,true,false);
            JSONObject conditions=enveloppe.optJSONObject("conditions");if(conditions!=null){
                SpannableStringBuilder contenu=new SpannableStringBuilder();String[] cles={"vente","reglement","mention"},titres={"Conditions de vente","Conditions de règlement","Informations complémentaires"};
                for(int i=0;i<cles.length;i++){
                    String v=conditions.optString(cles[i],"").trim();if(v.isEmpty())continue;if(v.length()>10000)throw new IOException("Conditions trop longues.");
                    if(contenu.length()>0)contenu.append("\n\n");int debut=contenu.length();contenu.append(titres[i]);contenu.setSpan(new StyleSpan(Typeface.BOLD),debut,contenu.length(),Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);contenu.append("\n").append(v);
                }
                if(contenu.length()>0){p.y+=16;p.bloc(contenu,9,false,true);}
            }
            p.finir();p.document.writeTo(flux);
        }
    }
    private static final class Pages implements AutoCloseable {
        static final int GAUCHE=34,LARGEUR=527,BAS=790;
        final PdfDocument document=new PdfDocument();final String titre;PdfDocument.Page page;Canvas canvas;int y=34,numero=0;
        final int[] colonnes={74,207,64,92,90};
        Pages(String t)throws IOException{titre=t;nouvelle();}
        void nouvelle()throws IOException {
            if(Thread.currentThread().isInterrupted())throw new IOException("Export annulé.");finir();if(++numero>1000)throw new IOException("Document trop volumineux.");
            page=document.startPage(new PdfDocument.PageInfo.Builder(595,842,numero).create());canvas=page.getCanvas();canvas.drawColor(Color.WHITE);y=34;
            if(numero>1){bloc(titre+" · suite",10,true,false);y+=8;}
        }
        void finir(){if(page!=null){Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);p.setTextSize(8);p.setColor(Color.GRAY);canvas.drawText("Patenteasy · ska_987 · page "+numero,GAUCHE,824,p);document.finishPage(page);page=null;}}
        void dessiner(StaticLayout l,int x,int ligne,int hauteur){canvas.save();canvas.clipRect(x,y,x+l.getWidth(),y+hauteur);canvas.translate(x,y-l.getLineTop(ligne));l.draw(canvas);canvas.restore();}
        void bloc(CharSequence s,int taille,boolean gras,boolean bas)throws IOException {
            if(s.length()==0)return;StaticLayout l=texte(s,LARGEUR,taille,gras);int ligne=0;
            while(ligne<l.getLineCount()){
                if(Thread.currentThread().isInterrupted())throw new IOException("Export annulé.");int debut=l.getLineTop(ligne),fin=ligne;
                while(fin<l.getLineCount()&&l.getLineBottom(fin)-debut<=BAS-y)fin++;
                if(fin==ligne){nouvelle();continue;}int hauteur=l.getLineBottom(fin-1)-debut;
                if(bas&&fin==l.getLineCount())y=Math.max(y,BAS-hauteur);dessiner(l,GAUCHE,ligne,hauteur);y+=hauteur+5;ligne=fin;
                if(ligne<l.getLineCount())nouvelle();
            }
        }
        void entete(String[] titres)throws IOException {
            if(y+35>BAS)nouvelle();int x=GAUCHE,hauteur=24;StaticLayout[] ls=new StaticLayout[titres.length];
            for(int i=0;i<titres.length;i++){ls[i]=texte(titres[i],colonnes[i]-10,9,true);hauteur=Math.max(hauteur,ls[i].getHeight()+8);}
            if(hauteur>200)throw new IOException("Libellé de taxe trop long.");if(y+hauteur>BAS)nouvelle();Paint fond=new Paint();fond.setColor(Color.rgb(237,242,247));canvas.drawRect(GAUCHE,y,GAUCHE+LARGEUR,y+hauteur,fond);
            int origine=y;y+=4;for(int i=0;i<ls.length;i++){dessiner(ls[i],x+5,0,hauteur-8);x+=colonnes[i];}y=origine+hauteur;
        }
        void ligne(String[] cellules,String[] titres)throws IOException {
            StaticLayout[] ls=new StaticLayout[cellules.length];int max=1;for(int i=0;i<ls.length;i++){ls[i]=texte(cellules[i],colonnes[i]-10,9,false);max=Math.max(max,ls[i].getLineCount());}int ligne=0;
            while(ligne<max){
                if(BAS-y<24){nouvelle();entete(titres);}int fin=ligne,hauteur=0;
                while(fin<max){int h=0;for(StaticLayout l:ls)if(fin<l.getLineCount())h=Math.max(h,l.getLineBottom(fin)-l.getLineTop(Math.min(ligne,l.getLineCount()-1)));if(h+8>BAS-y)break;hauteur=Math.max(hauteur,h);fin++;}
                if(fin==ligne){nouvelle();entete(titres);continue;}y+=4;int x=GAUCHE;
                for(int i=0;i<ls.length;i++){if(ligne<ls[i].getLineCount())dessiner(ls[i],x+5,ligne,hauteur);x+=colonnes[i];}
                y+=hauteur+4;Paint bord=new Paint();bord.setColor(Color.LTGRAY);canvas.drawLine(GAUCHE,y,GAUCHE+LARGEUR,y,bord);ligne=fin;if(ligne<max){nouvelle();entete(titres);}
            }
        }
        @Override public void close(){finir();document.close();}
    }
}
