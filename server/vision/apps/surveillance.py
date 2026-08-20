# -*- coding: utf-8 -*-
"""Surveillance intelligente — alerte intrus.

Détecte une personne (MediaPipe ObjectDetector) dans une zone à surveiller
(boutique, bureau, maison). Dès qu'une personne est présente alors que le
système est « armé », envoie une alerte Telegram (photo) et sauvegarde une
capture dans captures/.

Un délai d'armement au démarrage te laisse le temps de quitter la zone.

Commandes clavier :
    a     -> armer / désarmer la surveillance
    ÉCHAP -> quitter
"""

import sys
import os
import json
import time
import threading

import cv2
import httpx
import mediapipe as mp

from server.vision.core.camera import ouvrir_camera, FluxVideo, nouveau_fichier_capture
from server.vision.core.objects import creer_detecteur_objets, libelle_objet
from server.vision.alerts import AlerteTelegram


def notifier_serveur_orion(chemin_capture, nb_personnes, visages_connus=None):
    """Envoie un événement d'intrusion au serveur Orion WebSocket via POST /api/surveillance_event."""
    def _envoi():
        host = os.environ.get("SERVER_HOST", "127.0.0.1")
        port = os.environ.get("SERVER_PORT", "8765")
        if host in ("0.0.0.0", "::"):
            host = "127.0.0.1"
        url = f"http://{host}:{port}/api/surveillance_event"
        horodatage = time.strftime("%Hh%M")
        personnes_label = visages_connus if visages_connus else []
        payload = {
            "timestamp": horodatage,
            "count": nb_personnes,
            "image_path": str(chemin_capture) if chemin_capture else None,
            "persons": personnes_label,
            "message": f"🚨 Intrusion détectée à {horodatage} ({nb_personnes} personne(s))",
        }
        try:
            httpx.post(url, json=payload, timeout=3.0)
        except Exception:
            pass

    threading.Thread(target=_envoi, daemon=True).start()

# --------------------------------------------------------------------------- #
#  Configuration                                                            #
# --------------------------------------------------------------------------- #
LARGEUR, HAUTEUR = 640, 480
OBJETS_INTERVALLE = 3           # détecter 1 image sur N (perf)
SEUIL = 0.4
MAX_OBJETS = 5

CLASSES_SURVEILLEES = {"person"}   # objets déclenchant une alerte
ARME_AU_DEMARRAGE = True
DELAI_ARMEMENT = 10             # secondes avant armement effectif (pour sortir)
TELEGRAM_COOLDOWN = 60          # secondes minimum entre deux alertes intrus


def dessiner_personnes(img, detections):
    """Cadre rouge + libellé pour chaque objet surveillé détecté."""
    nb = 0
    for d in detections:
        cat = d.categories[0]
        if cat.category_name not in CLASSES_SURVEILLEES:
            continue
        nb += 1
        bb = d.bounding_box
        x1, y1 = bb.origin_x, bb.origin_y
        x2, y2 = x1 + bb.width, y1 + bb.height
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(img, f"{libelle_objet(cat.category_name)} {int(cat.score*100)}%",
                    (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 0, 255), 2)
    return nb


def main():
    print("[INFO] Ouverture de la caméra...", flush=True)
    cap = ouvrir_camera(LARGEUR, HAUTEUR)
    if cap is None:
        print("Échec de la capture vidéo. Vérifiez la caméra.", flush=True)
        return
    flux = FluxVideo(cap).start()

    detecteur = creer_detecteur_objets(SEUIL, MAX_OBJETS)
    if detecteur is None:
        print("[SURVEILLANCE] Détecteur indisponible (modèle manquant).", flush=True)
        flux.stop()
        return

    notifieur = AlerteTelegram(cooldown=TELEGRAM_COOLDOWN)
    arme = ARME_AU_DEMARRAGE

    temps_precedent = time.time()
    temps_demarrage = time.time()
    derniere_capture = 0.0
    compteur = 0
    obj_ts = 0
    dernieres_detections = []

    fenetre = "Surveillance intrus"
    cv2.namedWindow(fenetre, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(fenetre, cv2.WND_PROP_TOPMOST, 1)

    print("Commandes : [a] armer/désarmer  |  [ÉCHAP] quitter", flush=True)

    while True:
        ok, img = flux.lire()
        if not ok or img is None:
            continue
        maintenant = time.time()
        h, w = img.shape[:2]

        # Détection d'objets (frame-skip).
        if compteur % OBJETS_INTERVALLE == 0:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            obj_ts += 1
            dernieres_detections = detecteur.detect_for_video(mp_image, obj_ts).detections

        nb_personnes = dessiner_personnes(img, dernieres_detections)

        # Armement effectif après le délai de sortie.
        temps_restant = DELAI_ARMEMENT - (maintenant - temps_demarrage)
        arme_effectif = arme and temps_restant <= 0
        intrusion = arme_effectif and nb_personnes > 0

        # --- Bandeau d'état ---
        if not arme:
            etat, couleur = "DESARMEE", (0, 255, 0)
        elif temps_restant > 0:
            etat, couleur = f"ARMEMENT DANS {int(temps_restant) + 1}s", (0, 165, 255)
        elif intrusion:
            etat, couleur = "!!! INTRUS !!!", (0, 0, 255)
        else:
            etat, couleur = "ARMEE - surveillance", (0, 255, 255)
        cv2.putText(img, etat, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, couleur, 2)

        if intrusion:
            cv2.rectangle(img, (0, 0), (w - 1, h - 1), (0, 0, 255), 8)

        # --- Alerte : photo annotée sur Telegram + capture locale (anti-spam) + serveur Orion ---
        if intrusion:
            legende = f"🚨 INTRUS détecté ({nb_personnes} personne(s)) !"
            notifieur.envoyer_photo(img, legende, cle="intrus")
            if maintenant - derniere_capture >= TELEGRAM_COOLDOWN:
                chemin = nouveau_fichier_capture("intrus", "png")
                cv2.imwrite(chemin, img)
                derniere_capture = maintenant
                print(f"[INTRUS] Capture enregistrée : {chemin}", flush=True)
                notifier_serveur_orion(chemin, nb_personnes)

        fps = 1 / (maintenant - temps_precedent) if maintenant != temps_precedent else 0
        temps_precedent = maintenant
        cv2.putText(img, f"FPS: {int(fps)}", (w - 130, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.imshow(fenetre, img)

        touche = cv2.waitKey(1) & 0xFF
        if touche == 27:
            break
        elif touche == ord("a"):
            arme = not arme
            temps_demarrage = maintenant   # relance le délai d'armement
            print(f"[SURVEILLANCE] {'Armée' if arme else 'Désarmée'}.", flush=True)

        compteur += 1

    flux.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
