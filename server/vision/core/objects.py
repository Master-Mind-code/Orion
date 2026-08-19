# -*- coding: utf-8 -*-
"""Détecteur d'objets MediaPipe (EfficientDet-Lite) — partagé par les apps."""

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from server.vision.paths import MODELE_OBJETS

# Traduction FR de quelques classes COCO courantes (sinon nom anglais conservé).
TRAD_OBJETS = {
    "person": "Personne", "cell phone": "Telephone", "cup": "Tasse",
    "bottle": "Bouteille", "laptop": "Ordinateur", "keyboard": "Clavier",
    "mouse": "Souris", "book": "Livre", "chair": "Chaise", "tv": "Television",
    "remote": "Telecommande", "clock": "Horloge", "scissors": "Ciseaux",
    "backpack": "Sac a dos", "bowl": "Bol", "wine glass": "Verre",
    "banana": "Banane", "apple": "Pomme", "orange": "Orange",
}


def creer_detecteur_objets(seuil=0.4, max_resultats=5):
    """Crée un ObjectDetector MediaPipe (mode VIDEO) ; None si modèle absent.

    Le modèle est chargé en mémoire (model_asset_buffer) car MediaPipe sous
    Windows traite mal les chemins absolus (C:\\...).
    """
    if not MODELE_OBJETS.exists():
        print(f"[OBJETS] Modèle introuvable ({MODELE_OBJETS}) — détection "
              f"d'objets désactivée.", flush=True)
        return None
    with open(MODELE_OBJETS, "rb") as f:
        buffer = f.read()
    options = mp_vision.ObjectDetectorOptions(
        base_options=mp_python.BaseOptions(model_asset_buffer=buffer),
        running_mode=mp_vision.RunningMode.VIDEO,
        max_results=max_resultats,
        score_threshold=seuil,
    )
    return mp_vision.ObjectDetector.create_from_options(options)


def libelle_objet(nom_classe):
    """Nom FR d'une classe COCO, sinon le nom d'origine."""
    return TRAD_OBJETS.get(nom_classe, nom_classe)
