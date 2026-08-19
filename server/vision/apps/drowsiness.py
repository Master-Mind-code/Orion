# -*- coding: utf-8 -*-
"""Détecteur de somnolence et de distraction pour conducteur.

Cible : chauffeurs Gbaka, Yango, Sotra, taxis (contexte ivoirien).

    - EAR (Eye Aspect Ratio) : yeux fermés trop longtemps -> SOMNOLENCE.
    - Orientation de la tête (solvePnP) : tête détournée trop longtemps ->
      DISTRACTION (ex. regarde son téléphone).

Déclenche une alarme sonore et une alerte Telegram (photo).

Commandes clavier :
    d     -> activer / désactiver la détection de distraction (tête)
    ÉCHAP -> quitter
"""

import time
import threading

import cv2
import numpy as np
import mediapipe as mp

from server.vision.core.camera import ouvrir_camera, FluxVideo
from server.vision.alerts import AlerteTelegram

try:
    import winsound  # alarme native sous Windows
    _WINSOUND = True
except ImportError:
    _WINSOUND = False

# --------------------------------------------------------------------------- #
#  Configuration (à calibrer selon la personne / la caméra)                 #
# --------------------------------------------------------------------------- #
LARGEUR, HAUTEUR = 640, 480

EAR_SEUIL = 0.23            # en dessous = œil considéré fermé
DUREE_SOMNOLENCE = 1.2      # secondes yeux fermés avant alarme

YAW_SEUIL = 25             # degrés de rotation gauche/droite tolérés
PITCH_SEUIL = 20           # degrés d'inclinaison haut/bas tolérés
DUREE_DISTRACTION = 2.0    # secondes tête détournée avant alarme
DISTRACTION_AU_DEMARRAGE = True

TELEGRAM_COOLDOWN = 30     # secondes minimum entre deux alertes Telegram

# Indices FaceMesh des 6 points de chaque œil (ordre EAR).
OEIL_GAUCHE = [33, 160, 158, 133, 153, 144]
OEIL_DROIT = [362, 385, 387, 263, 373, 380]

# Points utilisés pour l'estimation de pose de la tête (solvePnP).
POINTS_POSE = [1, 152, 33, 263, 61, 291]     # nez, menton, yeux, bouche
MODELE_3D = np.array([
    (0.0, 0.0, 0.0),         # bout du nez
    (0.0, -63.6, -12.5),     # menton
    (-43.3, 32.7, -26.0),    # coin externe œil gauche
    (43.3, 32.7, -26.0),     # coin externe œil droit
    (-28.9, -28.9, -24.1),   # coin gauche de la bouche
    (28.9, -28.9, -24.1),    # coin droit de la bouche
], dtype=np.float64)


# --------------------------------------------------------------------------- #
#  Alarme sonore (thread dédié)                                             #
# --------------------------------------------------------------------------- #
class Alarme:
    def __init__(self):
        self.active = False
        self.stopped = False
        self.thread = threading.Thread(target=self._boucle, daemon=True)
        self.thread.start()

    def _boucle(self):
        while not self.stopped:
            if self.active:
                if _WINSOUND:
                    winsound.Beep(1000, 300)
                else:
                    print("\a", end="", flush=True)
                    time.sleep(0.3)
            else:
                time.sleep(0.05)

    def regler(self, actif):
        self.active = actif

    def stop(self):
        self.stopped = True
        self.active = False


# --------------------------------------------------------------------------- #
#  Calculs                                                                  #
# --------------------------------------------------------------------------- #
def _pt(landmarks, i, w, h):
    return np.array([landmarks[i].x * w, landmarks[i].y * h])


def calcul_ear(landmarks, indices, w, h):
    """Eye Aspect Ratio : (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)."""
    p = [_pt(landmarks, i, w, h) for i in indices]
    vertical = np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])
    horizontal = 2.0 * np.linalg.norm(p[0] - p[3])
    if horizontal == 0:
        return 0.0
    return vertical / horizontal


def pose_tete(landmarks, w, h):
    """Renvoie (pitch, yaw) en degrés via solvePnP, ou None si échec."""
    points_2d = np.array([[landmarks[i].x * w, landmarks[i].y * h]
                          for i in POINTS_POSE], dtype=np.float64)
    focale = w
    matrice_cam = np.array([[focale, 0, w / 2],
                            [0, focale, h / 2],
                            [0, 0, 1]], dtype=np.float64)
    dist = np.zeros((4, 1))
    ok, rvec, _ = cv2.solvePnP(MODELE_3D, points_2d, matrice_cam, dist,
                               flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return None
    rmat, _ = cv2.Rodrigues(rvec)
    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
    pitch, yaw = angles[0], angles[1]
    if pitch > 90:
        pitch -= 180
    elif pitch < -90:
        pitch += 180
    return pitch, yaw


# --------------------------------------------------------------------------- #
#  Programme principal                                                      #
# --------------------------------------------------------------------------- #
def main():
    print("[INFO] Ouverture de la caméra...", flush=True)
    cap = ouvrir_camera(LARGEUR, HAUTEUR)
    if cap is None:
        print("Échec de la capture vidéo. Vérifiez la caméra.", flush=True)
        return
    flux = FluxVideo(cap).start()

    face_mesh = mp.solutions.face_mesh.FaceMesh(
        max_num_faces=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)

    alarme = Alarme()
    notifieur = AlerteTelegram(cooldown=TELEGRAM_COOLDOWN)
    detecter_distraction = DISTRACTION_AU_DEMARRAGE

    fermeture_debut = None
    distraction_debut = None
    temps_precedent = time.time()

    fenetre = "Detecteur de somnolence"
    cv2.namedWindow(fenetre, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(fenetre, cv2.WND_PROP_TOPMOST, 1)

    print("Commandes : [d] distraction on/off  |  [ÉCHAP] quitter", flush=True)

    while True:
        ok, img = flux.lire()
        if not ok or img is None:
            continue
        h, w = img.shape[:2]
        maintenant = time.time()

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        resultat = face_mesh.process(rgb)

        somnolence = False
        distraction = False
        ear = None

        if resultat.multi_face_landmarks:
            lm = resultat.multi_face_landmarks[0].landmark

            ear = (calcul_ear(lm, OEIL_GAUCHE, w, h) +
                   calcul_ear(lm, OEIL_DROIT, w, h)) / 2.0
            if ear < EAR_SEUIL:
                if fermeture_debut is None:
                    fermeture_debut = maintenant
                elif maintenant - fermeture_debut >= DUREE_SOMNOLENCE:
                    somnolence = True
            else:
                fermeture_debut = None

            for idx in OEIL_GAUCHE + OEIL_DROIT:
                x, y = int(lm[idx].x * w), int(lm[idx].y * h)
                cv2.circle(img, (x, y), 2, (0, 255, 0), -1)

            if detecter_distraction:
                pose = pose_tete(lm, w, h)
                if pose is not None:
                    pitch, yaw = pose
                    detourne = abs(yaw) > YAW_SEUIL or abs(pitch) > PITCH_SEUIL
                    if detourne:
                        if distraction_debut is None:
                            distraction_debut = maintenant
                        elif maintenant - distraction_debut >= DUREE_DISTRACTION:
                            distraction = True
                    else:
                        distraction_debut = None
                    cv2.putText(img, f"Tete: yaw {int(yaw)} pitch {int(pitch)}",
                                (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                (200, 200, 200), 1)
        else:
            fermeture_debut = None
            distraction_debut = None

        alerte = somnolence or distraction
        alarme.regler(alerte)

        if ear is not None:
            couleur = (0, 0, 255) if ear < EAR_SEUIL else (0, 255, 0)
            cv2.putText(img, f"EAR: {ear:.2f}", (20, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, couleur, 2)

        etat, couleur_etat = "OK", (0, 255, 0)
        if somnolence:
            etat, couleur_etat = "!!! SOMNOLENCE !!!", (0, 0, 255)
        elif distraction:
            etat, couleur_etat = "!!! DISTRACTION !!!", (0, 128, 255)
        cv2.putText(img, etat, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    couleur_etat, 2)

        if alerte:
            cv2.rectangle(img, (0, 0), (w - 1, h - 1), (0, 0, 255), 8)

        # Alerte Telegram (photo annotée, anti-spam par clé).
        if somnolence:
            notifieur.envoyer_photo(img, "⚠️ SOMNOLENCE détectée au volant !",
                                    cle="somnolence")
        elif distraction:
            notifieur.envoyer_photo(img, "⚠️ DISTRACTION détectée au volant !",
                                    cle="distraction")

        fps = 1 / (maintenant - temps_precedent) if maintenant != temps_precedent else 0
        temps_precedent = maintenant
        cv2.putText(img, f"FPS: {int(fps)}", (w - 130, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.imshow(fenetre, img)

        touche = cv2.waitKey(1) & 0xFF
        if touche == 27:
            break
        elif touche == ord("d"):
            detecter_distraction = not detecter_distraction
            distraction_debut = None
            print(f"[DISTRACTION] {'Activée' if detecter_distraction else 'Désactivée'}.",
                  flush=True)

    alarme.stop()
    flux.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
