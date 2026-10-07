# SPDX-License-Identifier: GPL-3.0-or-later
"""Assembler Python embarqué et wheels Windows déjà téléchargés, sans exécuter Windows."""
from pathlib import Path
import shutil,zipfile,argparse
p=argparse.ArgumentParser();p.add_argument('python_embarque');p.add_argument('wheels');p.add_argument('sortie');a=p.parse_args()
root=Path(__file__).resolve().parents[1];sortie=Path(a.sortie);runtime=sortie/'programme/runtime';app=sortie/'programme/app';runtime.mkdir(parents=True,exist_ok=True);app.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(a.python_embarque) as z:z.extractall(runtime)
site=runtime/'Lib/site-packages';site.mkdir(parents=True,exist_ok=True)
for wheel in Path(a.wheels).glob('*.whl'):
 # Widgets natifs uniquement : aucun module WebEngine / Addons n'est livré.
 if wheel.name.lower().startswith('pyside6_addons'):continue
 with zipfile.ZipFile(wheel) as z:
  for nom in z.namelist():
   if nom.endswith('/'):continue
   rel=Path(nom)
   if len(rel.parts)>2 and rel.parts[0].endswith('.data'):
    if rel.parts[1] not in ('purelib','platlib'):continue
    rel=Path(*rel.parts[2:])
   cible=site/rel;cible.parent.mkdir(parents=True,exist_ok=True);cible.write_bytes(z.read(nom))
for fichier in runtime.glob('*._pth'):fichier.write_text('python313.zip\n.\nLib/site-packages\n../app\nimport site\n')
for f in root.glob('*.py'):shutil.copy2(f,app/f.name)
for dossier in ('templates','static'):shutil.copytree(root/dossier,app/dossier,dirs_exist_ok=True)
for nom in ('LICENSE','NOTICE','README.md','configuration_editeur.json'):shutil.copy2(root/nom,app/nom)
shutil.copy2(root/'docs'/'INSTALLATION.md',app/'INSTALLATION.md')
for nom in ('installer.ps1','INSTALLER_WINDOWS.cmd'):shutil.copy2(root/'distribution/windows'/nom,sortie/nom)
for nom in ('Patenteasy.cmd',):shutil.copy2(root/'distribution/windows'/nom,sortie/'programme'/nom)
shutil.copy2(root/'docs'/'INSTALLATION.md',sortie/'LIRE_AVANT_INSTALLATION.md')
print('Paquet Windows assemblé :',sortie)
