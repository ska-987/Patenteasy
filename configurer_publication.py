# SPDX-License-Identifier: GPL-3.0-or-later
"""Configurer les liens publics avant de reconstruire les distributions."""
import json
from pathlib import Path
from editeur import ConfigurationEditeur

def main():
    root=Path(__file__).resolve().parent
    chemin=root/'configuration_editeur.json'
    donnees=json.loads(chemin.read_text(encoding='utf-8'))
    drive=input('Lien public complet du dossier Proton Drive : ').strip()
    donnees['telechargements_url']=ConfigurationEditeur.lien(drive)
    paypal=input('Lien PayPal (Entrée pour conserver celui livré) : ').strip()
    if paypal:donnees['paypal_url']=ConfigurationEditeur.lien(paypal,True)
    texte=json.dumps(donnees,ensure_ascii=False,indent=2)+'\n'
    chemin.write_text(texte,encoding='utf-8')
    (root/'android/app/src/main/assets/editeur.json').write_text(texte,encoding='utf-8')
    print('Liens enregistrés. Reconstruisez les paquets pour intégrer ces valeurs.')

if __name__=='__main__':main()
