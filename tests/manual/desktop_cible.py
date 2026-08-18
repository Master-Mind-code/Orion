"""Fenêtre jetable servant de cible au test de pilotage du bureau.

Enregistre dans un JSON tout ce qu'elle reçoit : clics (avec coordonnées écran),
touches, et contenu du champ texte. Permet de vérifier qu'un clic a bien atterri
où on le voulait, sans toucher à la moindre donnée de l'utilisateur.
"""
import ctypes
import json
import sys

# Doit précéder l'import de tkinter : sinon Tk raisonne en pixels logiques et
# rapporte des coordonnées divisées par le facteur d'échelle Windows (x1.5 à
# 150 %), alors qu'Orion travaille en pixels physiques.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

import tkinter as tk

RESULT = sys.argv[1]
TITRE = "ORION TEST CIBLE JETABLE"

etat = {"clicks": [], "keys": [], "text": "", "scrolls": []}

root = tk.Tk()
root.title(TITRE)
root.geometry("900x520+400+300")
root.attributes("-topmost", True)

txt = tk.Text(root, font=("Consolas", 14), bg="#101820", fg="#7ee787",
              insertbackground="#7ee787")
txt.pack(fill="both", expand=True)


def on_click(e):
    etat["clicks"].append({"x_ecran": e.x_root, "y_ecran": e.y_root,
                           "x_fenetre": e.x, "y_fenetre": e.y})


def on_key(e):
    etat["keys"].append(e.keysym)


def on_wheel(e):
    etat["scrolls"].append(e.delta)


txt.bind("<Button-1>", on_click, add="+")
root.bind("<Key>", on_key, add="+")
root.bind("<MouseWheel>", on_wheel, add="+")


def dump():
    etat["text"] = txt.get("1.0", "end-1c")
    try:
        with open(RESULT, "w", encoding="utf-8") as fh:
            json.dump(etat, fh, ensure_ascii=False)
    except Exception:
        pass
    root.after(200, dump)


root.after(200, dump)
root.mainloop()
