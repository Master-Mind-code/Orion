# -*- coding: utf-8 -*-
"""Détection mains + visages + objets en temps réel.

Comptage de doigts, reconnaissance de gestes, capture d'écran, enregistrement
vidéo et détection d'objets (MediaPipe ObjectDetector, EfficientDet-Lite).

Optimisations : capture threadée, résolution réduite, frame-skip visage/objets.

Commandes clavier :
    s     -> capture d'écran (dossier captures/)
    r     -> démarrer / arrêter l'enregistrement vidéo
    o     -> activer / désactiver la détection d'objets
    ÉCHAP -> quitter
"""

import os
import time

import cv2
import mediapipe as mp
from cvzone.HandTrackingModule import HandDetector

from server.vision.core.camera import ouvrir_camera, FluxVideo, nouveau_fichier_capture
from server.vision.core.gestures import nom_du_geste
from server.vision.core.objects import creer_detecteur_objets, libelle_objet

# --------------------------------------------------------------------------- #
#  Configuration                                                            #
# --------------------------------------------------------------------------- #
LARGEUR, HAUTEUR = 640, 480
MAX_MAINS = 2
MAX_VISAGES = 2
VISAGE_INTERVALLE = 2           # traiter le visage 1 image sur N
OBJETS_INTERVALLE = 3           # traiter les objets 1 image sur N

SEUIL_OBJETS = 0.4
MAX_OBJETS = 5
DETECTER_OBJETS_AU_DEMARRAGE = True


def dessiner_objets(img, detections):
    """Dessine les cadres et libellés des objets détectés."""
    for d in detections:
        bb = d.bounding_box
        x1, y1 = bb.origin_x, bb.origin_y
        x2, y2 = x1 + bb.width, y1 + bb.height
        cat = d.categories[0]
        libelle = libelle_objet(cat.category_name)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 165, 255), 2)
        cv2.putText(img, f"{libelle} {int(cat.score * 100)}%", (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)


def main():
    print("[INFO] Ouverture de la caméra...", flush=True)
    cap = ouvrir_camera(LARGEUR, HAUTEUR)
    if cap is None:
        print("Échec de la capture vidéo. Vérifiez la caméra.", flush=True)
        return
    flux = FluxVideo(cap).start()

    detector = HandDetector(maxHands=MAX_MAINS, detectionCon=0.8)

    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=MAX_VISAGES)
    mp_draw = mp.solutions.drawing_utils
    draw_spec = mp_draw.DrawingSpec(thickness=1, circle_radius=1)

    detecteur_objets = creer_detecteur_objets(SEUIL_OBJETS, MAX_OBJETS)
    detecter_objets = DETECTER_OBJETS_AU_DEMARRAGE and detecteur_objets is not None

    enregistre = False
    video_writer = None

    temps_precedent = time.time()
    compteur = 0
    obj_ts = 0
    dernier_visage = None
    derniers_objets = []

    fenetre = "Détection mains, visages et objets"
    cv2.namedWindow(fenetre, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(fenetre, cv2.WND_PROP_TOPMOST, 1)

    print("Commandes : [s] capture  |  [r] enregistrer  |  [o] objets  |  [ÉCHAP] quitter",
          flush=True)

    while True:
        success, img = flux.lire()
        if not success or img is None:
            continue

        face_du = (compteur % VISAGE_INTERVALLE == 0)
        obj_du = (detecter_objets and compteur % OBJETS_INTERVALLE == 0)
        img_rgb = None
        if face_du or obj_du:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_rgb.flags.writeable = False

        # Mains + comptage des doigts (chaque image).
        hands, img = detector.findHands(img)
        for hand in hands:
            doigts = detector.fingersUp(hand)
            geste = nom_du_geste(doigts)
            x, y, _, _ = hand["bbox"]
            cv2.putText(img, geste, (x, y - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)

        # Visage (frame-skip).
        if face_du:
            dernier_visage = face_mesh.process(img_rgb)
        if dernier_visage and dernier_visage.multi_face_landmarks:
            for face_lms in dernier_visage.multi_face_landmarks:
                mp_draw.draw_landmarks(
                    img, face_lms, mp_face_mesh.FACEMESH_CONTOURS,
                    draw_spec, draw_spec)

        # Objets (frame-skip).
        if obj_du:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
            obj_ts += 1
            resultat = detecteur_objets.detect_for_video(mp_image, obj_ts)
            derniers_objets = resultat.detections
        if detecter_objets:
            dessiner_objets(img, derniers_objets)

        # FPS.
        temps_actuel = time.time()
        fps = 1 / (temps_actuel - temps_precedent) if temps_actuel != temps_precedent else 0
        temps_precedent = temps_actuel
        cv2.putText(img, f"FPS: {int(fps)}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Indicateur d'enregistrement.
        if enregistre and video_writer is not None:
            video_writer.write(img)
            h, w = img.shape[:2]
            cv2.circle(img, (w - 40, 40), 12, (0, 0, 255), cv2.FILLED)
            cv2.putText(img, "REC", (w - 110, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow(fenetre, img)

        touche = cv2.waitKey(1) & 0xFF
        if touche == 27:  # ÉCHAP
            break
        elif touche == ord("s"):
            chemin = nouveau_fichier_capture("capture", "png")
            cv2.imwrite(chemin, img)
            print(f"[CAPTURE] Image enregistrée : {chemin}", flush=True)
        elif touche == ord("o"):
            if detecteur_objets is None:
                print("[OBJETS] Indisponible (modèle manquant).", flush=True)
            else:
                detecter_objets = not detecter_objets
                if not detecter_objets:
                    derniers_objets = []
                print(f"[OBJETS] {'Activée' if detecter_objets else 'Désactivée'}.",
                      flush=True)
        elif touche == ord("r"):
            if not enregistre:
                h, w = img.shape[:2]
                chemin = nouveau_fichier_capture("video", "mp4")
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                video_writer = cv2.VideoWriter(chemin, fourcc, 20.0, (w, h))
                enregistre = True
                print(f"[REC] Enregistrement démarré : {chemin}", flush=True)
            else:
                enregistre = False
                if video_writer is not None:
                    video_writer.release()
                    video_writer = None
                print("[REC] Enregistrement arrêté.", flush=True)

        compteur += 1

    if video_writer is not None:
        video_writer.release()
    flux.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
