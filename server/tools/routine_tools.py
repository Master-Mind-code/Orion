"""
Gestion des routines automatiques et des tâches récurrentes planifiées d'Orion.

Stocke et gère les tâches périodiques configurées par l'utilisateur.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List

ROUTINES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "routines.json")


def _load_routines() -> List[Dict[str, Any]]:
    if not os.path.exists(ROUTINES_FILE):
        return []
    try:
        with open(ROUTINES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_routines(routines: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(ROUTINES_FILE), exist_ok=True)
    with open(ROUTINES_FILE, "w", encoding="utf-8") as f:
        json.dump(routines, f, ensure_ascii=False, indent=2)


def create_routine(
    name: str,
    schedule_description: str,
    tool_name: str,
    tool_params: Dict[str, Any] | str = None,
) -> Dict[str, Any]:
    """Crée une nouvelle routine automatique planifiée.
    
    name: Nom explicite de la routine (ex: "Scan BRVM Matinal")
    schedule_description: Fréquence (ex: "tous les jours à 08h00", "toutes les 4 heures")
    tool_name: Nom de l'outil Orion à exécuter
    tool_params: Paramètres de l'outil (dictionnaire ou chaîne JSON)
    """
    if isinstance(tool_params, str):
        try:
            tool_params = json.loads(tool_params)
        except Exception:
            tool_params = {}
    elif tool_params is None:
        tool_params = {}

    routines = _load_routines()
    routine_id = f"rt_{uuid.uuid4().hex[:8]}"

    new_rt = {
        "id": routine_id,
        "name": name,
        "schedule": schedule_description,
        "tool_name": tool_name,
        "tool_params": tool_params,
        "created_at": time.time(),
        "last_run": None,
        "run_count": 0,
        "enabled": True,
    }
    routines.append(new_rt)
    _save_routines(routines)

    return {
        "success": True,
        "routine": new_rt,
        "message": f"Routine '{name}' créée avec succès (ID: {routine_id}).",
    }


def list_routines() -> Dict[str, Any]:
    """Liste l'ensemble des routines automatiques enregistrées."""
    routines = _load_routines()
    return {
        "success": True,
        "count": len(routines),
        "routines": routines,
    }


def delete_routine(routine_id: str) -> Dict[str, Any]:
    """Supprime une routine planifiée par son ID."""
    routines = _load_routines()
    filtered = [r for r in routines if r["id"] != routine_id]
    if len(filtered) == len(routines):
        return {"success": False, "error": f"Routine avec ID '{routine_id}' introuvable."}

    _save_routines(filtered)
    return {"success": True, "routine_id": routine_id, "message": "Routine supprimée avec succès."}


def execute_routine(routine_id: str) -> Dict[str, Any]:
    """Exécute manuellement et immédiatement une routine enregistrée."""
    routines = _load_routines()
    target = next((r for r in routines if r["id"] == routine_id), None)
    if not target:
        return {"success": False, "error": f"Routine '{routine_id}' introuvable."}

    # Mise à jour des stats d'exécution
    target["last_run"] = time.time()
    target["run_count"] += 1
    _save_routines(routines)

    return {
        "success": True,
        "routine": target,
        "message": f"Lancement de l'outil '{target['tool_name']}' avec les paramètres : {target['tool_params']}",
    }


HANDLERS = {
    "create_routine":  lambda p: create_routine(**p),
    "list_routines":    lambda p: list_routines(),
    "delete_routine":  lambda p: delete_routine(**p),
    "execute_routine": lambda p: execute_routine(**p),
}
