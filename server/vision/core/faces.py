# -*- coding: utf-8 -*-
"""Module de reconnaissance de visages connus (100 % local et privé).

Données biométriques enregistrées exclusivement dans `data/known_faces/` (ignoré par git).
Utilise MediaPipe / OpenCV pour la détection et l'extraction d'empreintes faciales.
"""

import json
import os
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent.parent
KNOWN_FACES_DIR = ROOT / "data" / "known_faces"


def _garantir_dossier():
    KNOWN_FACES_DIR.mkdir(parents=True, exist_ok=True)


def _extraire_visages_mediapipe(image_bgr):
    """Détecte les visages et retourne une liste de (crop_bgr, box_dict)."""
    h, w = image_bgr.shape[:2]
    try:
        import mediapipe as mp
        mp_face_detection = mp.solutions.face_detection
        with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as fd:
            rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            results = fd.process(rgb)
            if not results.detections:
                return []
            crops = []
            for det in results.detections:
                bbox = det.location_data.relative_bounding_box
                x1 = max(0, int(bbox.xmin * w))
                y1 = max(0, int(bbox.ymin * h))
                bw = min(w - x1, int(bbox.width * w))
                bh = min(h - y1, int(bbox.height * h))
                if bw > 20 and bh > 20:
                    crop = image_bgr[y1:y1 + bh, x1:x1 + bw]
                    crops.append((crop, {"x": x1, "y": y1, "w": bw, "h": bh}))
            return crops
    except Exception:
        # Fallback OpenCV Haar Cascade si MediaPipe indisponible
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        crops = []
        for (x, y, bw, bh) in faces:
            crop = image_bgr[y:y + bh, x:x + bw]
            crops.append((crop, {"x": int(x), "y": int(y), "w": int(bw), "h": int(bh)}))
        return crops


def _calculer_empreinte(crop_bgr) -> np.ndarray:
    """Calcule une empreinte faciale normalisée (vecteur de caractéristiques local)."""
    resized = cv2.resize(crop_bgr, (128, 128))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    
    # 1. HOG / gradient spatial (32x32)
    gx = cv2.Sobel(equalized, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(equalized, cv2.CV_32F, 0, 1, ksize=3)
    mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)
    mag_small = cv2.resize(mag, (32, 32))
    
    # 2. Histogramme LBP simplifié
    lbp_hist, _ = np.histogram(equalized, bins=32, range=(0, 256))
    
    # Concatenation et normalisation L2
    vec = np.hstack([mag_small.flatten(), lbp_hist.astype(np.float32)])
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def enroll_face(name: str, image_bgr) -> dict:
    """Enregistre un nouveau visage connu sous un nom donné."""
    name = str(name).strip().lower()
    if not name:
        return {"success": False, "error": "Le nom ne peut pas être vide."}

    crops = _extraire_visages_mediapipe(image_bgr)
    if not crops:
        return {"success": False, "error": "Aucun visage détecté sur l'image pour l'enrôlement."}

    # Prendre le plus grand visage détecté
    crop, box = max(crops, key=lambda c: c[1]["w"] * c[1]["h"])
    vec = _calculer_empreinte(crop)

    _garantir_dossier()
    person_dir = KNOWN_FACES_DIR / name
    person_dir.mkdir(parents=True, exist_ok=True)

    # Sauvegarde la photo du visage et l'empreinte biométrique
    cv2.imwrite(str(person_dir / "face.jpg"), crop)
    np.save(str(person_dir / "embedding.npy"), vec)

    info = {"name": name, "enrolled_at": str(Path(person_dir / "face.jpg"))}
    with open(person_dir / "info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    return {"success": True, "name": name, "message": f"Visage de '{name}' enrôlé avec succès (100% local)."}


def delete_face(name: str) -> dict:
    """Supprime les données biométriques locales d'une personne."""
    name = str(name).strip().lower()
    person_dir = KNOWN_FACES_DIR / name
    if not person_dir.exists():
        return {"success": False, "error": f"Aucun visage enregistré pour '{name}'."}

    import shutil
    shutil.rmtree(person_dir)
    return {"success": True, "name": name, "message": f"Données biométriques de '{name}' supprimées."}


def list_faces() -> list[str]:
    """Liste les noms des visages connus enregistrés localement."""
    _garantir_dossier()
    noms = []
    for p in KNOWN_FACES_DIR.iterdir():
        if p.is_dir() and (p / "embedding.npy").exists():
            noms.append(p.name)
    return sorted(noms)


def _charger_base_visages() -> dict[str, np.ndarray]:
    """Charge en mémoire toutes les empreintes enregistrées."""
    _garantir_dossier()
    base = {}
    for p in KNOWN_FACES_DIR.iterdir():
        if p.is_dir():
            emb_file = p / "embedding.npy"
            if emb_file.exists():
                try:
                    vec = np.load(str(emb_file))
                    base[p.name] = vec
                except Exception:
                    pass
    return base


def recognize_faces(image_bgr, seuil_similarite: float = 0.72) -> list[dict]:
    """Détecte et identifie les visages connus sur une image.

    Retourne une liste de dicts :
    [{"name": "untel", "score": 0.85, "box": {"x": 10, "y": 20, "w": 100, "h": 100}}]
    """
    base = _charger_base_visages()
    crops = _extraire_visages_mediapipe(image_bgr)
    if not crops:
        return []

    resultats = []
    for crop, box in crops:
        vec = _calculer_empreinte(crop)
        meilleur_nom = "Inconnu"
        meilleur_score = 0.0

        if base:
            for nom, ref_vec in base.items():
                # Score de similarité cosinus [0..1]
                score = float(np.dot(vec, ref_vec))
                if score > meilleur_score:
                    meilleur_score = score
                    meilleur_nom = nom

        if meilleur_score >= seuil_similarite:
            nom_final = meilleur_nom
        else:
            nom_final = "Inconnu"

        resultats.append({
            "name": nom_final,
            "score": round(meilleur_score, 3),
            "box": box,
        })

    return resultats
