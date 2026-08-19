# -*- coding: utf-8 -*-
"""Éco-domotique par présence — coupe les appareils quand la pièce est vide.

Détecte la présence d'une personne (MediaPipe ObjectDetector). Si la pièce
reste vide plus de `DELAI_EXTINCTION` secondes, coupe les appareils (clim,
lumière...) ; les rallume dès qu'une personne réapparaît.

En Afrique, la climatisation représente une grosse part de la facture (CIE) ;
l'automatiser par la vision est un gain direct face au délestage.

Par défaut la commande des appareils est **simulée** (affichage + log + notif
Telegram). Pour piloter du vrai matériel, implémente `Appareils._appliquer`
(exemples MQTT / Home Assistant fournis en commentaire).

Commandes clavier :
    ÉCHAP -> quitter
"""

import time

import cv2
import mediapipe as mp

from server.vision.core.camera import ouvrir_camera, FluxVideo
from server.vision.core.objects import creer_detecteur_objets
from server.vision.alerts import AlerteTelegram

# --------------------------------------------------------------------------- #
#  Configuration                                                            #
# --------------------------------------------------------------------------- #
LARGEUR, HAUTEUR = 640, 480
OBJETS_INTERVALLE = 3           # détecter 1 image sur N
SEUIL = 0.4
MAX_OBJETS = 5

CLASSES_PRESENCE = {"person"}
# Délai de vacance avant coupure. Production : 180 (3 min). Réduit pour tester.
DELAI_EXTINCTION = 15


class Appareils:
    """Pilote les appareils (clim / lumière).

    Par défaut : simulation (log + notification Telegram). Pour du vrai matériel,
    complète `_appliquer()` (voir exemples MQTT / Home Assistant en commentaire).
    """

    def __init__(self, notifieur=None):
        self.allumes = True     # on suppose la pièce occupée au démarrage
        self.notifieur = notifieur

    def allumer(self):
        if not self.allumes:
            self.allumes = True
            self._appliquer(True)

    def eteindre(self):
        if self.allumes:
            self.allumes = False
            self._appliquer(False)

    def _appliquer(self, etat):
        mot = "ALLUMES" if etat else "COUPES"
        print(f"[DOMOTIQUE] Appareils {mot}.", flush=True)
        if self.notifieur:
            self.notifieur.envoyer_message(
                f"{'💡' if etat else '🔌'} Éco-domotique : appareils {mot.lower()}.",
                cle="domotique")

        # --- Intégration matérielle réelle (à décommenter et configurer) ---
        # MQTT (pip install paho-mqtt) :
        #   import paho.mqtt.publish as publish
        #   publish.single("maison/salon/clim", "ON" if etat else "OFF",
        #                  hostname="192.168.1.50")
        #
        # Home Assistant (REST — requests déjà installé) :
        #   import requests
        #   action = "turn_on" if etat else "turn_off"
        #   requests.post(f"{HA_URL}/api/services/switch/{action}",
        #                 headers={"Authorization": f"Bearer {HA_TOKEN}"},
        #                 json={"entity_id": "switch.climatiseur_salon"}, timeout=5)


def presence_detectee(detections):
    """Vrai si au moins un objet des classes de présence est détecté."""
    return any(d.categories[0].category_name in CLASSES_PRESENCE for d in detections)


def main():
    print("[INFO] Ouverture de la caméra...", flush=True)
    cap = ouvrir_camera(LARGEUR, HAUTEUR)
    if cap is None:
        print("Échec de la capture vidéo. Vérifiez la caméra.", flush=True)
        return
    flux = FluxVideo(cap).start()

    detecteur = creer_detecteur_objets(SEUIL, MAX_OBJETS)
    if detecteur is None:
        print("[DOMOTIQUE] Détecteur indisponible (modèle manquant).", flush=True)
        flux.stop()
        return

    notifieur = AlerteTelegram(cooldown=5)
    appareils = Appareils(notifieur)

    temps_precedent = time.time()
    derniere_presence = time.time()
    frame_id = 0
    obj_ts = 0
    present = False

    fenetre = "Eco-domotique par presence"
    cv2.namedWindow(fenetre, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(fenetre, cv2.WND_PROP_TOPMOST, 1)

    print("Commandes : [ÉCHAP] quitter", flush=True)

    while True:
        ok, img = flux.lire()
        if not ok or img is None:
            continue
        maintenant = time.time()
        h, w = img.shape[:2]

        # Détection de présence (frame-skip).
        if frame_id % OBJETS_INTERVALLE == 0:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            obj_ts += 1
            detections = detecteur.detect_for_video(mp_image, obj_ts).detections
            present = presence_detectee(detections)
            if present:
                derniere_presence = maintenant

        # Logique éco : rallumer si présence, couper si vide trop longtemps.
        vide_depuis = maintenant - derniere_presence
        if present:
            appareils.allumer()
        elif vide_depuis >= DELAI_EXTINCTION:
            appareils.eteindre()

        # --- Affichage ---
        if present:
            etat, couleur = "OCCUPEE", (0, 255, 0)
        elif appareils.allumes:
            restant = int(DELAI_EXTINCTION - vide_depuis) + 1
            etat, couleur = f"VIDE - coupure dans {restant}s", (0, 165, 255)
        else:
            etat, couleur = "VIDE - APPAREILS COUPES", (0, 0, 255)
        cv2.putText(img, etat, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, couleur, 2)

        indic = "ALLUMES" if appareils.allumes else "COUPES"
        coul_indic = (0, 255, 0) if appareils.allumes else (120, 120, 120)
        cv2.putText(img, f"Appareils : {indic}", (20, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, coul_indic, 2)

        fps = 1 / (maintenant - temps_precedent) if maintenant != temps_precedent else 0
        temps_precedent = maintenant
        cv2.putText(img, f"FPS: {int(fps)}", (w - 120, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.imshow(fenetre, img)

        if cv2.waitKey(1) & 0xFF == 27:
            break
        frame_id += 1

    flux.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
