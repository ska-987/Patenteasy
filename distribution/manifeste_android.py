# SPDX-License-Identifier: GPL-3.0-or-later
"""Attestation de construction de l’APK à signer, liée au commit contrôlé."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from version import VERSION_ANDROID
root=Path(__file__).resolve().parents[1]
dossier=root/'android/build'
apk=dossier/f'Patenteasy-Android-{VERSION_ANDROID}-A-SIGNER.apk'
jar=dossier/'apksigner.jar'
bt=Path(os.environ['ANDROID_SDK_ROOT'])/'build-tools/35.0.0'
badging=subprocess.check_output([str(bt/'aapt'),'dump','badging',str(apk)],text=True)
if f"versionName='{VERSION_ANDROID}'" not in badging or "name='pf.ska987.patenteasy.local'" not in badging or "versionCode='10'" not in badging:
    raise SystemExit('Identité Android incorrecte.')
manifeste={'version':VERSION_ANDROID,'versionCode':10,'package':'pf.ska987.patenteasy.local',
           'source':os.environ.get('GITHUB_SHA',''), 'signature':'requise',
           'taille':apk.stat().st_size,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),
           'apksigner_sha256':hashlib.sha256(jar.read_bytes()).hexdigest()}
(dossier/'android-verifie.json').write_text(json.dumps(manifeste,indent=2)+'\n')
