"""
Orion Tool — Vision par caméra.

Donne des yeux à Orion : une image prise à la volée, analysée sur place.
S'appuie sur le sous-système `server/vision/` (MediaPipe EfficientDet-Lite pour
les objets, cvzone pour les mains).

Deux familles d'outils, parce que les besoins sont différents :

  - `camera_*`  : ponctuels et rapides. Ils ouvrent la caméra, prennent UNE
    image, la relâchent aussitôt, et rendent la main. C'est ce qu'il faut à un
    assistant qu'on interroge (« qu'est-ce que tu vois ? »).
  - `vision_app_*` : lancent les applications complètes (détection, somnolence,
    surveillance, comptage, domotique) en processus séparé. Ce sont des boucles
    OpenCV bloquantes avec fenêtre et raccourcis clavier : elles ne peuvent pas
    être des outils, seulement être démarrées et arrêtées.

⚠ La caméra a son PROPRE interrupteur, ORION_CAMERA_ENABLED, distinct de
ORION_AUTOMATION_ENABLED. Filmer une pièce et bouger une souris sont deux
pouvoirs différents ; les mettre sous le même verrou obligerait à céder l'un
pour obtenir l'autre.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Les applications lançables, et ce qu'elles font.
APPS = {
    "detection":    "Mains, visages et objets en temps réel (gestes, captures, enregistrement)",
    "drowsiness":   "Somnolence et distraction du conducteur (EAR + orientation de la tête)",
    "surveillance": "Alerte intrus : détecte une personne dans une zone armée",
    "comptage":     "Comptage par franchissement de ligne (personnes, véhicules)",
    "domotique":    "Éco-domotique : coupe les appareils quand la pièce est vide",
}

_processus: dict[str, subprocess.Popen] = {}

AVERTISSEMENT_NOIRE = (
    "Image entièrement noire : cache d'objectif fermé, ou caméra "
    "monopolisée par une autre application."
)


def _camera_active() -> bool:
    return os.getenv("ORION_CAMERA_ENABLED", "false").strip().lower() in (
        "1", "true", "yes", "on", "oui",
    )


def _refus() -> dict:
    return {
        "success": False,
        "error": "Caméra désactivée. Mets ORION_CAMERA_ENABLED=true dans .env "
                 "pour autoriser Orion à filmer. Interrupteur distinct de "
                 "ORION_AUTOMATION_ENABLED, volontairement.",
    }


def _manque(paquet: str) -> dict:
    return {"success": False,
            "error": f"{paquet} n'est pas installé. Installe avec :\n"
                     f"    pip install -r requirements-vision.txt"}


def _prendre_image(chauffe_max_s: float = 3.0):
    """Ouvre la caméra, attend une image réellement exposée, referme.

    Deux pièges mesurés sur cette machine :

    1. Un nombre fixe d'images de chauffe ne suffit pas : 3 images à 60 ms
       donnaient une image 100 % noire.
    2. Surtout, **la cadence de lecture compte plus que le nombre d'images**.
       À 80 ms d'intervalle, DirectShow rend des tampons périmés encore noirs ;
       à 250 ms, la première image sort déjà correctement exposée (luminance
       ~50/255). On espace donc les lectures au lieu de les enchaîner.

    Si tout reste noir jusqu'au bout, on renvoie quand même la dernière image
    en le signalant : c'est souvent un cache d'objectif fermé, pas une panne.
    """
    import cv2
    import numpy as np
    from server.vision.core.camera import ouvrir_camera

    cap = ouvrir_camera()
    if cap is None:
        return None, "Aucune caméra disponible."
    try:
        image = None
        limite = time.time() + max(0.3, float(chauffe_max_s))
        while time.time() < limite:
            ok, frame = cap.read()
            if ok and frame is not None:
                image = frame
                # 25/255 : au-dessus du bruit d'un capteur qui démarre, en
                # dessous d'une pièce faiblement éclairée. À 6, une image
                # quasi noire passait pour valide.
                if float(np.asarray(frame).mean()) > 25.0:
                    return image, None
            time.sleep(0.25)
        if image is None:
            return None, "Caméra ouverte mais aucune image lisible."
        return image, "__noire__"
    finally:
        cap.release()
        cv2.destroyAllWindows()


# ════════════════════════════════════════════════════════════════════════════
# État
# ════════════════════════════════════════════════════════════════════════════

def camera_status() -> dict:
    """Disponibilité de la caméra et état de l'interrupteur. Lecture seule."""
    out: dict = {
        "success": True,
        "enabled": _camera_active(),
        "apps_disponibles": APPS,
        "apps_en_cours": [n for n, p in _processus.items() if p.poll() is None],
    }
    try:
        from server.vision.paths import MODELE_OBJETS
        out["modele_objets"] = MODELE_OBJETS.exists()
    except Exception:
        out["modele_objets"] = False

    for paquet in ("cv2", "mediapipe", "cvzone"):
        try:
            __import__(paquet)
            out[paquet] = True
        except ImportError:
            out[paquet] = False

    if not out["enabled"]:
        out["hint"] = ("Seul camera_status répond quand l'interrupteur est coupé. "
                       "Les prises de vue sont refusées.")
    return out


# ════════════════════════════════════════════════════════════════════════════
# Prise de vue
# ════════════════════════════════════════════════════════════════════════════

def camera_snapshot(path: str | None = None) -> dict:
    """Prend une photo et l'enregistre. Le chemin rendu est exploitable par
    analyze_image pour une description libre par le modèle de vision."""
    if not _camera_active():
        return _refus()
    try:
        import cv2
    except ImportError:
        return _manque("opencv-python")

    image, err = _prendre_image()
    if image is None:
        return {"success": False, "error": err}

    if path:
        dest = Path(path)
    else:
        from server.vision.paths import CAPTURES_DIR
        dest = CAPTURES_DIR / f"orion_{datetime.now():%Y%m%d_%H%M%S}.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), image)
    h, w = image.shape[:2]
    out = {"success": True, "path": str(dest), "width": int(w), "height": int(h)}
    if err == "__noire__":
        out["avertissement"] = AVERTISSEMENT_NOIRE
    return out


def camera_look(seuil: float = 0.4, max_objets: int = 8,
                save: bool = False) -> dict:
    """Que voit la caméra ? Détection d'objets sur une image prise à l'instant.

    Renvoie les objets reconnus avec leur score et leur position. Pour une
    description libre plutôt qu'une liste de classes, utiliser camera_snapshot
    puis analyze_image."""
    if not _camera_active():
        return _refus()
    try:
        import cv2
        import mediapipe as mp
    except ImportError as exc:
        return _manque(str(exc).split("'")[1] if "'" in str(exc) else "mediapipe")

    from server.vision.core.objects import creer_detecteur_objets, libelle_objet

    detecteur = creer_detecteur_objets(seuil=float(seuil),
                                       max_resultats=int(max_objets))
    if detecteur is None:
        return {"success": False,
                "error": "Modèle de détection introuvable (server/vision/models/)."}

    image, err = _prendre_image()
    if image is None:
        return {"success": False, "error": err}

    try:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        # Le détecteur est en mode VIDEO : il exige un horodatage croissant.
        resultat = detecteur.detect_for_video(mp_image, int(time.time() * 1000))
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        detecteur.close()

    objets = []
    for det in getattr(resultat, "detections", []) or []:
        cat = det.categories[0]
        bb = det.bounding_box
        objets.append({
            "objet": libelle_objet(cat.category_name),
            "classe": cat.category_name,
            "score": round(float(cat.score), 3),
            "boite": {"x": int(bb.origin_x), "y": int(bb.origin_y),
                      "largeur": int(bb.width), "hauteur": int(bb.height)},
        })

    out: dict = {
        "success": True,
        "objets": objets,
        "count": len(objets),
        "resume": ", ".join(o["objet"] for o in objets) or "rien de reconnu",
    }
    if err == "__noire__":
        # Sans ça, « rien de reconnu » sur une image noire ressemble à une
        # pièce vide alors que la caméra ne voit littéralement rien.
        out["avertissement"] = AVERTISSEMENT_NOIRE
        out["resume"] = "image noire — rien à analyser" 
    if save:
        h, w = image.shape[:2]
        from server.vision.paths import CAPTURES_DIR
        dest = CAPTURES_DIR / f"look_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        dest.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(dest), image)
        out["path"] = str(dest)
        out["width"], out["height"] = int(w), int(h)
    return out


def camera_gesture() -> dict:
    """Lit le geste de la main devant la caméra (poing, victoire, pouce levé...)."""
    if not _camera_active():
        return _refus()
    try:
        import cv2  # noqa: F401
        from cvzone.HandTrackingModule import HandDetector
    except ImportError:
        return _manque("cvzone")

    from server.vision.core.gestures import nom_du_geste

    image, err = _prendre_image()
    if image is None:
        return {"success": False, "error": err}

    try:
        detecteur = HandDetector(maxHands=2, detectionCon=0.7)
        mains, _ = detecteur.findHands(image, draw=False)
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    if not mains:
        return {"success": True, "mains": [], "count": 0,
                "resume": "image noire — rien à analyser" if err == "__noire__"
                          else "aucune main visible",
                **({"avertissement": AVERTISSEMENT_NOIRE} if err == "__noire__" else {})}

    lues = []
    for main in mains:
        doigts = detecteur.fingersUp(main)
        lues.append({
            "cote": main.get("type", "?"),
            "doigts_leves": int(sum(doigts)),
            "motif": list(doigts),
            "geste": nom_du_geste(doigts),
        })
    return {"success": True, "mains": lues, "count": len(lues),
            "resume": ", ".join(m["geste"] for m in lues)}


# ════════════════════════════════════════════════════════════════════════════
# Applications complètes
# ════════════════════════════════════════════════════════════════════════════

def vision_app_start(app: str) -> dict:
    """Lance une application de vision dans sa propre fenêtre.

    Ce sont des boucles bloquantes pilotées au clavier : elles tournent à côté
    d'Orion, pas dedans."""
    if not _camera_active():
        return _refus()
    app = str(app).strip().lower()
    if app not in APPS:
        return {"success": False,
                "error": f"Application inconnue : {app!r}. Disponibles : "
                         f"{', '.join(sorted(APPS))}."}

    en_cours = _processus.get(app)
    if en_cours is not None and en_cours.poll() is None:
        return {"success": False, "error": f"{app} tourne déjà (PID {en_cours.pid})."}

    proc = subprocess.Popen(
        [sys.executable, "-m", f"server.vision.apps.{app}"],
        cwd=str(ROOT),
    )
    _processus[app] = proc
    time.sleep(1.0)
    if proc.poll() is not None:
        return {"success": False,
                "error": f"{app} s'est arrêté immédiatement (code {proc.returncode}). "
                         "Caméra occupée par une autre application ?"}
    return {"success": True, "app": app, "pid": proc.pid,
            "description": APPS[app],
            "note": "Fenêtre OpenCV séparée. ÉCHAP la ferme, ou vision_app_stop."}


def vision_app_stop(app: str | None = None) -> dict:
    """Arrête une application de vision, ou toutes si app est omis."""
    cibles = [app] if app else list(_processus)
    arretes = []
    for nom in cibles:
        proc = _processus.get(str(nom))
        if proc is None or proc.poll() is not None:
            continue
        proc.terminate()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()
        arretes.append(nom)
        _processus.pop(str(nom), None)
    return {"success": True, "arretes": arretes,
            "encore_en_cours": [n for n, p in _processus.items() if p.poll() is None]}


HANDLERS = {
    "camera_status":    lambda p: camera_status(),
    "camera_snapshot":  lambda p: camera_snapshot(**p),
    "camera_look":      lambda p: camera_look(**p),
    "camera_gesture":   lambda p: camera_gesture(),
    "vision_app_start": lambda p: vision_app_start(**p),
    "vision_app_stop":  lambda p: vision_app_stop(**p),
}
