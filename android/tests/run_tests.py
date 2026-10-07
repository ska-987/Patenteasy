#!/usr/bin/env python3
"""Tests de chiffrement réel JCA, avec interfaces de stockage Android simulées.
Nécessite JDK 17 et org.json 20240303 fourni en dépendance de test séparée.
Ce n'est pas un test d'installation sur un téléphone.
"""
import os,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
jar=Path(os.environ['PATENTEASY_TEST_JSON_JAR']);classpath=os.pathsep.join(map(str,[jar,root/'libs/eddsa-0.3.0.jar']))
with tempfile.TemporaryDirectory() as d:
 sources=list((root/'tests/stubs').rglob('*.java'))+list((root/'tests/pf').rglob('*.java'))
 sources += [root/'app/src/main/java/pf/ska987/patenteasy'/n for n in ('Coffre.java','Droits.java','Catalogue.java','ExportCsv.java')]
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-classpath',classpath,'-d',d,*map(str,sources)],check=True)
 subprocess.run(['java','-classpath',d+os.pathsep+classpath,'pf.ska987.patenteasy.TestsCoffre'],check=True)

 subprocess.run(['java','-classpath',d+os.pathsep+classpath,'pf.ska987.patenteasy.TestsCatalogue',str(root/'tests/fixtures')],check=True)

 subprocess.run(['java','-classpath',d+os.pathsep+classpath,'pf.ska987.patenteasy.TestsExportCsv'],check=True)
