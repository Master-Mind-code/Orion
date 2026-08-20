# -*- coding: utf-8 -*-
"""Module de gestion et de relecture des macros bureau pour Orion.

Enregistre et rejoue des séquences d'actions (clics souris, frappes clavier, délais).
Stockage dans `data/macros/<nom>.json`.
"""

import json
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
MACROS_DIR = ROOT_DIR / "data" / "macros"

_recording_state = {
    "active": False,
    "name": None,
    "actions": [],
    "last_ts": None,
}


def _garantir_dossier():
    MACROS_DIR.mkdir(parents=True, exist_ok=True)


def macro_record_start(name: str) -> dict:
    """Démarre l'enregistrement d'une séquence macro sous un nom donné."""
    name = str(name).strip().lower()
    if not name:
        return {"success": False, "error": "Nom de macro requis."}

    _recording_state["active"] = True
    _recording_state["name"] = name
    _recording_state["actions"] = []
    _recording_state["last_ts"] = time.time()

    return {
        "success": True,
        "name": name,
        "message": f"Enregistrement de la macro '{name}' démarré. Ajoute des actions ou appelle macro_record_stop.",
    }


def macro_action_add(action_type: str, params: dict | None = None) -> dict:
    """Ajoute manuellement une action à la macro en cours d'enregistrement."""
    if not _recording_state["active"]:
        return {"success": False, "error": "Aucun enregistrement de macro en cours."}

    now = time.time()
    delay = round(now - (_recording_state["last_ts"] or now), 3)
    _recording_state["last_ts"] = now

    action = {
        "type": action_type,
        "params": params or {},
        "delay_before_sec": delay,
    }
    _recording_state["actions"].append(action)

    return {
        "success": True,
        "macro": _recording_state["name"],
        "count": len(_recording_state["actions"]),
        "action": action,
    }


def macro_record_stop() -> dict:
    """Arrête l'enregistrement courant et sauvegarde la macro dans data/macros/."""
    if not _recording_state["active"]:
        return {"success": False, "error": "Aucun enregistrement de macro actif."}

    name = _recording_state["name"]
    actions = _recording_state["actions"]

    _garantir_dossier()
    macro_file = MACROS_DIR / f"{name}.json"
    data = {
        "name": name,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "actions_count": len(actions),
        "actions": actions,
    }
    macro_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    _recording_state["active"] = False
    _recording_state["name"] = None
    _recording_state["actions"] = []

    return {
        "success": True,
        "name": name,
        "file": str(macro_file),
        "actions_count": len(actions),
        "message": f"Macro '{name}' sauvegardée avec {len(actions)} action(s).",
    }


def macro_list() -> dict:
    """Liste les macros enregistrées."""
    _garantir_dossier()
    macros = []
    for p in MACROS_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            macros.append({
                "name": d.get("name", p.stem),
                "created_at": d.get("created_at"),
                "actions_count": d.get("actions_count", 0),
            })
        except Exception:
            pass
    return {"success": True, "count": len(macros), "macros": sorted(macros, key=lambda x: x["name"])}


def macro_delete(name: str) -> dict:
    """Supprime une macro enregistrée."""
    name = str(name).strip().lower()
    _garantir_dossier()
    macro_file = MACROS_DIR / f"{name}.json"
    if not macro_file.exists():
        return {"success": False, "error": f"Macro '{name}' introuvable."}

    macro_file.unlink()
    return {"success": True, "name": name, "message": f"Macro '{name}' supprimée."}


def macro_play(name: str, speed: float = 1.0, repetitions: int = 1) -> dict:
    """Rejoue une macro enregistrée par son nom."""
    name = str(name).strip().lower()
    _garantir_dossier()
    macro_file = MACROS_DIR / f"{name}.json"
    if not macro_file.exists():
        return {"success": False, "error": f"Macro '{name}' introuvable."}

    try:
        data = json.loads(macro_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"success": False, "error": f"Lecture macro impossible : {exc}"}

    actions = data.get("actions", [])
    speed_factor = max(0.1, min(10.0, float(speed)))
    reps = max(1, min(100, int(repetitions)))

    from server.tools.automation import (
        mouse_click, mouse_move, mouse_drag, mouse_scroll,
        keyboard_type, keyboard_press, keyboard_key,
    )

    executed_count = 0
    for r in range(reps):
        for act in actions:
            delay = act.get("delay_before_sec", 0.1) / speed_factor
            if delay > 0:
                time.sleep(delay)

            act_type = act.get("type")
            params = act.get("params", {})

            if act_type == "mouse_click":
                mouse_click(**params)
            elif act_type == "mouse_move":
                mouse_move(**params)
            elif act_type == "mouse_drag":
                mouse_drag(**params)
            elif act_type == "mouse_scroll":
                mouse_scroll(**params)
            elif act_type == "keyboard_type":
                keyboard_type(**params)
            elif act_type == "keyboard_press":
                keyboard_press(**params)
            elif act_type == "keyboard_key":
                keyboard_key(**params)
            elif act_type == "delay":
                time.sleep(float(params.get("duration", 0.5)) / speed_factor)

            executed_count += 1

    return {
        "success": True,
        "name": name,
        "repetitions": reps,
        "speed": speed_factor,
        "actions_played": executed_count,
        "message": f"Macro '{name}' rejouée {reps} fois avec succès.",
    }


HANDLERS = {
    "macro_record_start": lambda p: macro_record_start(**p),
    "macro_record_stop":  lambda p: macro_record_stop(),
    "macro_action_add":   lambda p: macro_action_add(**p),
    "macro_play":         lambda p: macro_play(**p),
    "macro_list":         lambda p: macro_list(),
    "macro_delete":       lambda p: macro_delete(**p),
}
