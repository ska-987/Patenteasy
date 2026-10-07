#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compilation légère : JDK17, SDK35/build-tools35, signature de production requise.
Aucune clé de remplacement n'est générée. Le mot de passe reste dans une variable
locale et n'est pas placé dans la ligne de commande.
"""
import os,subprocess,zipfile,shutil,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parent
sdk=Path(os.environ['ANDROID_SDK_ROOT']);bt=sdk/'build-tools/35.0.0';jar=sdk/'platforms/android-35/android.jar'
key=Path(os.environ['PATENTEASY_KEYSTORE']);alias=os.environ['PATENTEASY_KEY_ALIAS'];password=os.environ.get('PATENTEASY_KEY_PASSWORD')
if not key.is_file() or not password:raise SystemExit('Clé privée de production et mot de passe nécessaires. Ne publiez jamais la clé.')
manifest=root/'app/src/main/AndroidManifest.xml';numero=ET.parse(manifest).getroot().attrib['{http://schemas.android.com/apk/res/android}versionName']
build=root/'build';shutil.rmtree(build,ignore_errors=True);build.mkdir();classes=build/'classes';classes.mkdir();dex=build/'dex';dex.mkdir()
windows=os.name=='nt'
def outil(n):return bt/(n+('.bat' if windows and n in ('d8','apksigner') else '.exe' if windows else ''))
def run(*args):subprocess.run([str(a) for a in args],check=True)
run(outil('aapt'),'package','-f','-M',manifest,'-A',root/'app/src/main/assets','-S',root/'app/src/main/res','-I',jar,'-F',build/'unsigned.apk')
libs=list((root/'libs').glob('*.jar'));classpath=os.pathsep.join(map(str,[jar,*libs]));javac=['javac']
if os.environ.get('PATENTEASY_JDK'):javac=[str(Path(os.environ['PATENTEASY_JDK'])/'bin'/('javac.exe' if windows else 'javac'))]
elif not shutil.which('javac'):javac=['java','-m','jdk.compiler/com.sun.tools.javac.Main']
run(*javac,'-encoding','UTF-8','-source','8','-target','8','-classpath',classpath,'-d',classes,*list((root/'app/src/main/java').rglob('*.java')))
run(outil('d8'),'--lib',jar,'--min-api','26','--output',dex,*classes.rglob('*.class'),*libs)
with zipfile.ZipFile(build/'unsigned.apk','a',zipfile.ZIP_DEFLATED) as z:
 for p in dex.glob('*.dex'):z.write(p,p.name)
run(outil('zipalign'),'-f','4',build/'unsigned.apk',build/'aligned.apk')
sortie=build/('Patenteasy-Android-'+numero+'.apk')
run(outil('apksigner'),'sign','--ks',key,'--ks-key-alias',alias,'--ks-pass','env:PATENTEASY_KEY_PASSWORD','--out',sortie,build/'aligned.apk')
verification=subprocess.check_output([str(outil('apksigner')),'verify','--verbose','--print-certs',str(sortie)],text=True)
print(verification)
if 'cfc8d95ee97be9a7a80eca28de72178d7e9cd01236dc8187c69ba1c60ff7c119' not in verification:
 sortie.unlink(missing_ok=True)
 raise SystemExit('Certificat différent de la signature officielle. APK supprimée : ne changez pas de clé.')
print(sortie)
