# -*- coding: utf-8 -*-
"""Gestion de la caméra : ouverture robuste, capture en thread, captures fichier.

Code partagé par toutes les applications de vision (évite la duplication).
"""

import os
import threading
from datetime import datetime

import cv2

from server.vision.paths import CAPTURES_DIR


def ouvrir_camera(largeur=None, hauteur=None):
    """Ouvre la première caméra disponible (essaie DirectShow puis le défaut).

    Renvoie l'objet VideoCapture (déjà configuré) ou None si aucune caméra.
    """
    for index in (0, 1, 2):
        for backend in (cv2.CAP_DSHOW, cv2.CAP_ANY):
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                ok, _ = cap.read()
                if ok:
                    nom = "DSHOW" if backend == cv2.CAP_DSHOW else "ANY"
                    print(f"[CAMERA] Ouverte sur index {index} ({nom}).", flush=True)
                    if largeur:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, largeur)
                    if hauteur:
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, hauteur)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # latence minimale
                    return cap
            cap.release()
    return None


class FluxVideo:
    """Lit la caméra en continu dans un thread ; le thread principal récupère
    toujours la dernière image disponible (réduit la latence, augmente les FPS
    réellement traités)."""

    def __init__(self, cap):
        self.cap = cap
        self.lock = threading.Lock()
        self.ret, self.frame = cap.read()
        self.stopped = False
        self.thread = threading.Thread(target=self._boucle, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def _boucle(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.ret, self.frame = ret, frame

    def lire(self):
        with self.lock:
            if self.frame is None:
                return False, None
            return self.ret, self.frame.copy()

    def stop(self):
        self.stopped = True
        self.thread.join(timeout=1)
        self.cap.release()


def nouveau_fichier_capture(prefixe, extension):
    """Génère un chemin de fichier horodaté dans le dossier `captures/`."""
    os.makedirs(CAPTURES_DIR, exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(CAPTURES_DIR / f"{prefixe}_{horodatage}.{extension}")
