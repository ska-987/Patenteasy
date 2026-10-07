package pf.ska987.patenteasy;
public class TestsExportCsv {
 public static void main(String[] args)throws Exception {
  String s=ExportCsv.produire("{\"journal\":[{\"date\":\"2026-10-01\",\"libelle\":\"=SUM(1)\\nligne\",\"type\":\"depense\",\"montant\":12345}]}");
  if(!s.startsWith("\ufeffDate;")||!s.contains("123,45")||!s.contains("'=SUM(1)"))throw new AssertionError(s);
  System.out.println("Export CSV : montant exact, UTF-8 et formule neutralisée vérifiés.");
 }
}
