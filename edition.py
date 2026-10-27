# SPDX-License-Identifier: GPL-3.0-or-later
"""Sépare l'édition de test à partir d'un marqueur embarqué."""
import os
from pathlib import Path

DEVELOPPEMENT = (Path(__file__).parent/'edition-dev.json').is_file()

def repertoire():
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / ('PatenteasyLocal-DEV' if DEVELOPPEMENT else 'PatenteasyLocal')
