# -*- coding: utf-8 -*-
"""Module de transcription et de résumé automatique de réunions/appels pour Orion.

Analyse des fichiers audio ou des retranscriptions textuelles (ex: Reunion.txt),
génère un résumé structuré avec décisions & plan d'action, et l'enregistre dans Obsidian.
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


def meeting_summarize(
    file_path: str,
    title: str | None = None,
    push_telegram: bool = False,
    push_obsidian: bool = True,
) -> dict:
    """Transcrit et résume un fichier de réunion/appel (texte .txt/.md ou audio .wav/.mp3/.m4a)."""
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        return {"success": False, "error": f"Fichier introuvable : {file_path}"}

    ext = path.suffix.lower()
    transcript_text = ""

    # 1. Lecture du texte ou transcription audio
    if ext in (".txt", ".md", ".log", ".json"):
        try:
            transcript_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            transcript_text = path.read_text(encoding="latin-1")
    elif ext in (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".webm"):
        try:
            from server.transcribe import transcribe_blob
            blob = path.read_bytes()
            transcript_text = transcribe_blob(blob, suffix=ext)
        except Exception as exc:
            return {"success": False, "error": f"Échec transcription audio : {exc}"}
    else:
        return {"success": False, "error": f"Format de fichier non pris en charge : {ext}"}

    transcript_text = (transcript_text or "").strip()
    if not transcript_text:
        return {"success": False, "error": "Le fichier ne contient aucun texte à analyser."}

    # 2. Déduction du titre
    if not title:
        title = path.stem.replace("_", " ").replace("-", " ").capitalize()

    # 3. Synthèse via LLM (fallback heuristique léger si besoin)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_prefix = datetime.now().strftime("%Y-%m-%d")

    summary_text = _generate_summary(title, transcript_text)

    # 4. Sauvegarde Obsidian
    vault_path = None
    note_path_str = None
    if push_obsidian:
        vault = get_obsidian_vault_path()
        reunions_dir = vault / "Reunions"
        reunions_dir.mkdir(parents=True, exist_ok=True)
        safe_title = re.sub(r"[^\w\-]", "_", title).strip("_")
        filename = f"{date_prefix}_{safe_title}.md"
        note_path = reunions_dir / filename

        note_content = f"""---
date: {now_str}
type: meeting_summary
source: "{path.name}"
tags:
  - reunion
  - resume-appel
  - OrionVoice
---

# 📝 Compte-rendu : {title}

- **Fichier source** : `{path.name}`
- **Date d'analyse** : {now_str}

---

{summary_text}

---

## 📜 Retranscription Brute
<details>
<summary>Cliquez pour dérouler le texte brut</summary>

{transcript_text}

</details>
"""
        note_path.write_text(note_content, encoding="utf-8")
        vault_path = str(vault)
        note_path_str = str(note_path)

    # 5. Push Telegram optionnel
    telegram_sent = False
    if push_telegram:
        try:
            from server.tools.notifications import notify_telegram
            tg_text = f"📝 *Résumé de Réunion — {title}*\n\n" + summary_text[:1200]
            res_tg = notify_telegram(tg_text)
            telegram_sent = res_tg.get("success", False)
        except Exception as exc:
            print(f"[REUNION!] Telegram error: {exc}")

    return {
        "success": True,
        "title": title,
        "source_file": str(path),
        "transcript_length": len(transcript_text),
        "obsidian_note": note_path_str,
        "telegram_sent": telegram_sent,
        "summary": summary_text,
    }


def _generate_summary(title: str, transcript: str) -> str:
    """Génère le résumé structuré de la réunion à partir de la retranscription."""
    try:
        from server.orchestrator import _get_provider
        provider = _get_provider()
        prompt = (
            f"Tu es Orion, l'assistant IA exécutif. Voici la retranscription d'une réunion ou d'un appel intitulé '{title}'.\n"
            f"Analyse ce texte et génère un compte-rendu clair et structuré en Markdown avec les 4 sections exactes suivantes :\n\n"
            f"## 📌 Contexte & Ordre du jour\n"
            f"(Court résumé du sujet principal)\n\n"
            f"## 🎯 Points clés & Décisions prises\n"
            f"(3 à 5 puces décrivant ce qui a été décidé)\n\n"
            f"## 📋 Plan d'action & Tâches à réaliser\n"
            f"(- [ ] Tâche 1 (Qui ? Pour quand ?))\n\n"
            f"## 💡 Remarques complémentaires\n"
            f"(Notes additionnelles si nécessaires)\n\n"
            f"Voici le texte de la réunion :\n"
            f"{transcript[:15000]}"
        )
        res = provider.call(
            system="Tu es Orion, l'assistant IA exécutif.",
            tools=[],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
        )
        if isinstance(res.content, list):
            texts = [item.get("text", "") for item in res.content if item.get("type") == "text"]
            return "\n".join(texts).strip()
        return str(res.content).strip()
    except Exception as exc:
        print(f"[REUNION!] Fallback synthèse locale due à : {exc}")
        # Secours en cas d'absence d'API key ou hors-ligne
        lines = [line.strip() for line in transcript.split("\n") if line.strip()]
        preview = "\n".join(f"- {line}" for line in lines[:5])
        return f"""## 📌 Contexte & Ordre du jour
Compte-rendu généré automatiquement pour '{title}'.

## 🎯 Points clés & Aperçu
{preview}

## 📋 Plan d'action & Tâches à réaliser
- [ ] Vérifier et valider les points abordés dans la retranscription.
"""
