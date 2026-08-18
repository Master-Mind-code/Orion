"""Test bout en bout du pilotage du bureau par Orion.

⚠ MANUEL — prend physiquement le contrôle de la souris et du clavier pendant
une dizaine de secondes. Ne pas lancer dans une suite automatique.

    python tests/manual/desktop_e2e.py

Cible : une fenêtre Tk jetable (desktop_cible.py) lancée pour l'occasion, qui
journalise les clics avec leurs coordonnées écran, les touches et la molette.
Aucune application de l'utilisateur n'est touchée — c'est délibéré : une version
antérieure visait le Bloc-notes et est tombée sur un fichier non enregistré.

Nécessite ORION_AUTOMATION_ENABLED=true dans .env.
Panic button : souris dans le coin haut-gauche de l'écran.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(ICI))
TMP = tempfile.gettempdir()
RESULT = os.path.join(TMP, "orion_cible.json")
CIBLE = os.path.join(ICI, "desktop_cible.py")

sys.path.insert(0, PROJ)
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJ, ".env"))
from server.tools import ALL_HANDLERS as H

TITRE = "ORION TEST CIBLE JETABLE"
TEXTE = "Orion pilote le bureau — accents : éàîçù"
echecs = []


def verifie(nom, condition, detail=""):
    print(f"   {'OK  ' if condition else 'ECHEC'} {nom} {detail}")
    if not condition:
        echecs.append(nom)


def lire():
    for _ in range(15):
        try:
            with open(RESULT, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            time.sleep(0.2)
    return {}


if os.path.exists(RESULT):
    os.remove(RESULT)

print("[1] automation_status")
st = H["automation_status"]({})
print("   enabled:", st.get("enabled"), "| bureau:", st.get("virtual_desktop"))
if not st.get("enabled"):
    sys.exit("ABANDON : interrupteur coupé.")

print("\n[2] lancement de la fenêtre cible")
proc = subprocess.Popen([sys.executable, CIBLE, RESULT])
time.sleep(2.5)

print("\n[3] list_windows -> repérage")
wins = H["list_windows"]({}).get("windows", [])
cible = next((w for w in wins if TITRE.lower() in w["title"].lower()), None)
if cible is None:
    proc.kill()
    sys.exit("ABANDON : fenêtre cible introuvable.")
# Garde-fou : on refuse de continuer si le titre n'est pas exactement le nôtre.
assert TITRE.lower() in cible["title"].lower(), "Mauvaise fenêtre !"
print("  ", cible)

print("\n[4] focus_window (avec vérification réelle du premier plan)")
f = H["focus_window"]({"title_contains": TITRE})
print("  ", {k: v for k, v in f.items() if k != "window"})
verifie("focus effectif", f.get("focused") is True)
if not f.get("focused"):
    proc.kill()
    sys.exit("ABANDON : pas de focus, on ne tape pas à l'aveugle.")

print("\n[5] VRAI CLIC à un point choisi")
cx = cible["x"] + 300
cy = cible["y"] + 200
print("   clic demandé en:", (cx, cy))
print("  ", H["mouse_click"]({"x": cx, "y": cy}))
time.sleep(0.6)
d = lire()
clics = d.get("clicks", [])
verifie("clic reçu par la fenêtre", len(clics) >= 1, f"({len(clics)} clic(s))")
if clics:
    c = clics[-1]
    dx, dy = abs(c["x_ecran"] - cx), abs(c["y_ecran"] - cy)
    print(f"   reçu en ({c['x_ecran']},{c['y_ecran']}) -> écart ({dx},{dy}) px")
    verifie("clic au bon pixel", dx <= 1 and dy <= 1)

print("\n[6] clipboard_set + keyboard_key('ctrl+v')")
print("  ", H["clipboard_set"]({"text": TEXTE}))
print("  ", H["keyboard_key"]({"keys": "ctrl+v"}))
time.sleep(0.8)
d = lire()
recu = d.get("text", "")
print("   attendu:", repr(TEXTE))
print("   reçu   :", repr(recu))
verifie("texte collé identique (accents compris)", recu == TEXTE)

print("\n[7] keyboard_type (frappe directe)")
print("  ", H["keyboard_key"]({"keys": "enter"}))
print("  ", H["keyboard_type"]({"text": "ligne tapee au clavier"}))
time.sleep(0.8)
d = lire()
verifie("frappe clavier reçue", "ligne tapee au clavier" in d.get("text", ""))

print("\n[8] mouse_scroll")
print("  ", H["mouse_scroll"]({"x": cx, "y": cy, "amount": 2, "direction": "down"}))
time.sleep(0.5)
d = lire()
verifie("molette reçue", len(d.get("scrolls", [])) >= 1, f"({d.get('scrolls')})")

print("\n[9] mouse_drag (sélection à la souris)")
print("  ", H["mouse_drag"]({"from_x": cible["x"] + 60, "from_y": cible["y"] + 60,
                             "to_x": cx, "to_y": cy, "duration": 0.4}))
time.sleep(0.4)
d = lire()
verifie("drag reçu comme clic initial", len(d.get("clicks", [])) >= 2,
        f"({len(d.get('clicks', []))} clics au total)")

print("\n[10] screenshot de la fenêtre")
shot = H["screenshot"]({
    "region": {"x": cible["x"], "y": cible["y"],
               "width": cible["width"], "height": cible["height"]},
    "path": os.path.join(TMP, "orion_e2e.png"),
})
print("  ", {k: v for k, v in shot.items() if k != "base64"})
verifie("capture écrite", shot.get("success") is True)

print("\n[11] window_control minimize puis restore")
print("  ", H["window_control"]({"title_contains": TITRE, "action": "minimize"}).get("success"))
time.sleep(0.6)
print("  ", H["window_control"]({"title_contains": TITRE, "action": "restore"}).get("success"))
time.sleep(0.6)
wins = H["list_windows"]({}).get("windows", [])
w2 = next((w for w in wins if TITRE.lower() in w["title"].lower()), {})
verifie("fenêtre restaurée", "minimized" not in w2.get("state", []), str(w2.get("state")))

print("\n[12] fermeture de la fenêtre cible")
r = H["window_control"]({"title_contains": TITRE, "action": "close"})
print("  ", r)
time.sleep(1.0)
if proc.poll() is None:
    proc.kill()
    print("   (process tué en secours)")
verifie("fenêtre fermée par window_control", r.get("success") is True)

print("\n==== RÉSULTAT :", "SUCCÈS COMPLET" if not echecs else f"ÉCHECS : {echecs}", "====")
sys.exit(1 if echecs else 0)
