# -*- coding: utf-8 -*-
"""Module de dictée vocale directement vers le coffre Obsidian pour Orion.

Transforme une dictée vocale ("Orion, note que...") en une fiche Markdown datée.
"""

import os
import re
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def get_obsidian_vault_path() -> Path:
    """Retourne le chemin du coffre Obsidian depuis l'env ou fallback dans data/obsidian_journal."""
    env_path = os.getenv("ORION_OBSIDIAN_VAULT_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    vault = ROOT_DIR / "data" / "obsidian_journal"
    vault.mkdir(parents=True, exist_ok=True)
    return vault


def voice_dictate_obsidian(text: str, title: str | None = None, category: str = "Notes") -> dict:
    """Enregistre une dictée vocale sous forme de note Markdown datée dans le coffre Obsidian."""
    text = (text or "").strip()
    if not text:
        return {"success": False, "error": "Contenu de la dictée vide."}

    vault = get_obsidian_vault_path()
    category_dir = vault / category
    category_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    date_prefix = now.strftime("%Y-%m-%d_%H%M%S")

    # Si aucun titre n'est spécifié, dériver des premiers mots
    if not title:
        words = re.findall(r"\w+", text)
        short_title = "_".join(words[:6]) if words else "Note_Vocale"
        title = " ".join(words[:6]).capitalize() if words else "Note Vocale"
    else:
        short_title = re.sub(r"[^\w\-]", "_", title).strip("_")

    filename = f"{date_prefix}_{short_title}.md"
    note_path = category_dir / filename

    content = f"""---
date: {now_str}
type: dictation
category: {category}
tags:
  - note-vocale
  - orion-dictee
---

# 🎙️ {title}

{text}

---
*Dictée vocale enregistrée automatiquement par Orion.*
"""

    note_path.write_text(content, encoding="utf-8")
    print(f"[DICTATION OBSIDIAN] Note créée : {note_path}", flush=True)

    return {
        "success": True,
        "title": title,
        "filename": filename,
        "note_path": str(note_path),
        "vocal_response": f"J'ai bien noté dans Obsidian sous le titre '{title}'.",
    }
