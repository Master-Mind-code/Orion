"""
Enregistreur et rejoueur de scénarios d'automatisation RPA sur le bureau Windows.

Permet d'enregistrer des séquences de clics, de saisies de texte et d'actions système,
puis de les réexécuter à la demande.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

MACROS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "rpa_macros.json")


def _load_macros() -> Dict[str, List[Dict[str, Any]]]:
    if not os.path.exists(MACROS_FILE):
        return {}
    try:
        with open(MACROS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_macros(macros: Dict[str, List[Dict[str, Any]]]) -> None:
    os.makedirs(os.path.dirname(MACROS_FILE), exist_ok=True)
    with open(MACROS_FILE, "w", encoding="utf-8") as f:
        json.dump(macros, f, ensure_ascii=False, indent=2)


def add_macro_step(
    macro_name: str,
    action_type: str,
    x: int = None,
    y: int = None,
    text: str = None,
    keys: str = None,
    delay_after: float = 0.5,
) -> Dict[str, Any]:
    """Ajoute une étape à une macro RPA (clic, frappe, raccourci, pause).
    
    macro_name: Nom de la séquence (ex: "ouvrir_calculatrice")
    action_type: 'click', 'double_click', 'type_text', 'hotkey', 'wait'
    """
    macros = _load_macros()
    if macro_name not in macros:
        macros[macro_name] = []

    step = {
        "step_num": len(macros[macro_name]) + 1,
        "action_type": action_type.lower(),
        "x": x,
        "y": y,
        "text": text,
        "keys": keys,
        "delay_after": float(delay_after or 0.5),
        "timestamp": time.time(),
    }
    macros[macro_name].append(step)
    _save_macros(macros)

    return {
        "success": True,
        "macro_name": macro_name,
        "total_steps": len(macros[macro_name]),
        "added_step": step,
    }


def list_macros() -> Dict[str, Any]:
    """Liste toutes les macros RPA enregistrées et leur nombre d'étapes."""
    macros = _load_macros()
    summary = {}
    for name, steps in macros.items():
        summary[name] = {
            "steps_count": len(steps),
            "created_at": steps[0]["timestamp"] if steps else None,
        }
    return {
        "success": True,
        "count": len(summary),
        "macros": summary,
    }


def play_macro(macro_name: str) -> Dict[str, Any]:
    """Exécute une macro RPA étape par étape en contrôlant le bureau."""
    macros = _load_macros()
    if macro_name not in macros or not macros[macro_name]:
        return {"success": False, "error": f"Macro '{macro_name}' introuvable ou vide."}

    steps = macros[macro_name]
    from server.tools.automation import (
        automation_click,
        automation_hotkey,
        automation_type,
    )

    executed = 0
    for step in steps:
        act = step["action_type"]
        if act in ("click", "double_click"):
            if step["x"] is not None and step["y"] is not None:
                automation_click(
                    x=step["x"],
                    y=step["y"],
                    button="left",
                    clicks=2 if act == "double_click" else 1,
                )
        elif act == "type_text" and step["text"]:
            automation_type(text=step["text"])
        elif act == "hotkey" and step["keys"]:
            keys_list = [k.strip() for k in step["keys"].split("+")]
            automation_hotkey(keys=keys_list)
        
        time.sleep(step.get("delay_after", 0.5))
        executed += 1

    return {
        "success": True,
        "macro_name": macro_name,
        "executed_steps": executed,
        "message": f"Macro '{macro_name}' exécutée avec succès.",
    }


def delete_macro(macro_name: str) -> Dict[str, Any]:
    """Supprime une macro RPA enregistrée."""
    macros = _load_macros()
    if macro_name in macros:
        del macros[macro_name]
        _save_macros(macros)
        return {"success": True, "macro_name": macro_name, "message": "Macro supprimée."}
    return {"success": False, "error": f"Macro '{macro_name}' introuvable."}


HANDLERS = {
    "add_macro_step": lambda p: add_macro_step(**p),
    "list_macros":     lambda p: list_macros(),
    "play_macro":      lambda p: play_macro(**p),
    "delete_macro":    lambda p: delete_macro(**p),
}
