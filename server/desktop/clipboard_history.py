# -*- coding: utf-8 -*-
"""Module d'historisation du presse-papier pour Orion.

Conserve jusqu'à 50 entrées uniques horodatées dans `data/clipboard_history.json`.
"""

import json
from datetime import datetime
from pathlib import Path
from threading import Lock

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
CLIPBOARD_FILE = DATA_DIR / "clipboard_history.json"

_lock = Lock()
MAX_ENTRIES = 50


def _load_history() -> list[dict]:
    if CLIPBOARD_FILE.exists():
        try:
            return json.loads(CLIPBOARD_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_history(data: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CLIPBOARD_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def push_clipboard_history(text: str) -> bool:
    """Ajoute une entrée dans l'historique du presse-papier s'il s'agit d'un nouveau texte non-vide."""
    text = (text or "").strip()
    if not text:
        return False

    with _lock:
        history = _load_history()
        # Évite les doublons consécutifs identiques
        if history and history[0].get("text") == text:
            return False

        # Retire une ancienne occurrence identique pour la remonter en haut
        history = [item for item in history if item.get("text") != text]

        new_item = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "text": text,
            "length": len(text),
        }
        history.insert(0, new_item)
        if len(history) > MAX_ENTRIES:
            history = history[:MAX_ENTRIES]

        _save_history(history)
        return True


def clipboard_history_get(limit: int = 20, search: str | None = None) -> dict:
    """Récupère l'historique du presse-papier, filtré optionnellement par recherche."""
    with _lock:
        history = _load_history()

    if search:
        needle = search.lower()
        history = [item for item in history if needle in item.get("text", "").lower()]

    limit = max(1, min(MAX_ENTRIES, int(limit)))
    results = history[:limit]

    return {
        "success": True,
        "count": len(results),
        "total_stored": len(history),
        "search": search,
        "items": results,
    }


def clipboard_history_clear() -> dict:
    """Efface l'historique du presse-papier."""
    with _lock:
        _save_history([])
    return {"success": True, "message": "Historique du presse-papier effacé."}
