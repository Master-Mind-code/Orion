# -*- coding: utf-8 -*-
"""Comptage par franchissement de ligne (personnes / véhicules).

Détecte les objets (MediaPipe ObjectDetector), leur attribue un identifiant
stable (Tracker maison, IoU), et compte ceux qui franchissent une ligne
virtuelle — dans chaque sens.

Cas d'usage : clients entrant/sortant d'une boutique, véhicules à un carrefour.

Commandes clavier :
    r     -> remettre les compteurs à zéro
    ÉCHAP -> quitter
"""

import time

import cv2
import mediapipe as mp

from server.vision.core.camera import ouvrir_camera, FluxVideo
from server.vision.core.objects import creer_detecteur_objets, libelle_objet
from server.vision.core.tracking import Tracker, CompteurLigne

# --------------------------------------------------------------------------- #
#  Configuration                                                            #
# --------------------------------------------------------------------------- #
LARGEUR, HAUTEUR = 640, 480
OBJETS_INTERVALLE = 2           # détecter 1 image sur N
SEUIL = 0.4
MAX_OBJETS = 10                 # compter plusieurs objets à la fois

# Classes à suivre. Personnes par défaut ; décommente les véhicules pour le trafic.
CLASSES_SUIVIES = {"person"}
# CLASSES_SUIVIES = {"car", "truck", "bus", "motorcycle", "bicycle"}

# Ligne de comptage (horizontale, au milieu par défaut).
LIGNE_P1 = (0, HAUTEUR // 2)
LIGNE_P2 = (LARGEUR, HAUTEUR // 2)


def boxes_des_classes(detections):
    """Extrait les boîtes (x1,y1,x2,y2) des détections dont la classe est suivie."""
    boxes = []
    for d in detections:
        cat = d.categories[0]
        if cat.category_name not in CLASSES_SUIVIES:
            continue
        bb = d.bounding_box
        boxes.append((bb.origin_x, bb.origin_y,
                      bb.origin_x + bb.width, bb.origin_y + bb.height))
    return boxes


def main():
    print("[INFO] Ouverture de la caméra...", flush=True)
    cap = ouvrir_camera(LARGEUR, HAUTEUR)
    if cap is None:
        print("Échec de la capture vidéo. Vérifiez la caméra.", flush=True)
        return
    flux = FluxVideo(cap).start()

    detecteur = creer_detecteur_objets(SEUIL, MAX_OBJETS)
    if detecteur is None:
        print("[COMPTAGE] Détecteur indisponible (modèle manquant).", flush=True)
        flux.stop()
        return

    tracker = Tracker(iou_min=0.3, max_perdu=15)
    compteur = CompteurLigne(LIGNE_P1, LIGNE_P2)

    temps_precedent = time.time()
    frame_id = 0
    obj_ts = 0
    pistes = []

    fenetre = "Comptage par franchissement de ligne"
    cv2.namedWindow(fenetre, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(fenetre, cv2.WND_PROP_TOPMOST, 1)

    print("Commandes : [r] remise à zéro  |  [ÉCHAP] quitter", flush=True)

    while True:
        ok, img = flux.lire()
        if not ok or img is None:
            continue
        maintenant = time.time()
        h, w = img.shape[:2]

        # Détection + suivi (frame-skip).
        if frame_id % OBJETS_INTERVALLE == 0:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            obj_ts += 1
            detections = detecteur.detect_for_video(mp_image, obj_ts).detections
            pistes = tracker.update(boxes_des_classes(detections))
            for tid, _, centroid in pistes:
                compteur.maj(tid, centroid)

        # Dessin des pistes (id + centre).
        for tid, bbox, centroid in pistes:
            x1, y1, x2, y2 = bbox
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(img, centroid, 4, (0, 255, 0), -1)
            cv2.putText(img, f"#{tid}", (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Ligne de comptage.
        cv2.line(img, LIGNE_P1, LIGNE_P2, (255, 255, 0), 2)

        # Bandeau compteurs.
        total = compteur.sens_a + compteur.sens_b
        cv2.rectangle(img, (0, 0), (w, 34), (0, 0, 0), cv2.FILLED)
        cv2.putText(img, f"Sens A: {compteur.sens_a}   Sens B: {compteur.sens_b}"
                         f"   Total: {total}   Pistes: {len(pistes)}",
                    (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        fps = 1 / (maintenant - temps_precedent) if maintenant != temps_precedent else 0
        temps_precedent = maintenant
        cv2.putText(img, f"FPS: {int(fps)}", (w - 120, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.imshow(fenetre, img)

        touche = cv2.waitKey(1) & 0xFF
        if touche == 27:
            break
        elif touche == ord("r"):
            compteur.reset()
            print("[COMPTAGE] Compteurs remis à zéro.", flush=True)

        frame_id += 1

    flux.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
