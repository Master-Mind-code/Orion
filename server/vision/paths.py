# -*- coding: utf-8 -*-
"""Chemins du sous-système vision, ancrés sur Orion.

Le paquet vient d'un projet autonome où la racine était le dossier parent ;
intégré à Orion, les modèles voyagent AVEC le paquet (pour qu'il reste
déplaçable d'un bloc) tandis que les sorties vont dans le `data/` d'Orion,
déjà gitignoré et sauvegardé.
"""

from pathlib import Path

# server/vision/paths.py  ->  parents[2] = racine du projet Orion
PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODELS_DIR = Path(__file__).resolve().parent / "models"
CAPTURES_DIR = PROJECT_ROOT / "data" / "captures"
CONFIG_PATH = PROJECT_ROOT / "config.json"

MODELE_OBJETS = MODELS_DIR / "efficientdet_lite0.tflite"
