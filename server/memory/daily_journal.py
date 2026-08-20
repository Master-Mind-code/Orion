# -*- coding: utf-8 -*-
"""Module de journal de bord quotidien automatique pour Orion.

Synthétise chaque soir l'ensemble des activités de la journée à partir des logs d'audit,
des opportunités/trades, des alertes vision et des dictées vocales dans une note Obsidian.
"""

import os
import time
from datetime import datetime, timedelta
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


def generate_daily_journal(today_only: bool = True, push_obsidian: bool = True) -> dict:
    """Génère le journal de bord quotidien basé sur le registre d'audit d'Orion."""
    now = datetime.now()
    if today_only:
        start_dt = datetime(now.year, now.month, now.day, 0, 0, 0)
    else:
        start_dt = now - timedelta(days=1)

    since_ts = start_dt.timestamp()
    date_str = start_dt.strftime("%Y-%m-%d")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Extraction audit
    events = []
    stats = {}
    try:
        from server import audit
        events = audit.get_recent(limit=1000, since_ts=since_ts)
        stats = audit.get_stats(since_ts=since_ts)
    except Exception as exc:
        print(f"[DAILY JOURNAL] Erreur audit : {exc}")

    total_ops = stats.get("total", len(events))
    success_ops = stats.get("success", len([e for e in events if e.get("success")]))
    failed_ops = stats.get("failed", len([e for e in events if not e.get("success")]))
    top_tools = stats.get("top_tools", [])

    top_tools_str = "\n".join([f"  - `{t['tool']}` : {t['count']} appel(s)" for t in top_tools]) if top_tools else "  - Aucune opération répertoriée"

    # 2. Reconstitution du fil d'activités
    log_rows = []
    for ev in reversed(events[:30]):
        ts_str = datetime.fromtimestamp(ev["ts"]).strftime("%H:%M:%S")
        status = "✅" if ev.get("success") else "❌"
        tool = ev.get("tool_name")
        preview = ev.get("input_preview", "")
        log_rows.append(f"- `{ts_str}` {status} **{tool}** : {preview}")

    logs_text = "\n".join(log_rows) if log_rows else "*Aucune activité enregistrée aujourd'hui.*"

    content = f"""---
date: {now_str}
journal_date: {date_str}
type: daily_journal
tags:
  - journal-de-bord
  - OrionBrain
---

# 📓 Journal de Bord — {date_str}

- **Généré le** : {now_str}
- **Volume d'opérations** : {total_ops} actions ({success_ops} succès, {failed_ops} échecs)

---

## 📊 Outils les plus sollicités
{top_tools_str}

---

## ⏱️ Chronologie des Opérations Majeures
{logs_text}

---
*Journal de bord généré automatiquement par Orion.*
"""

    note_path_str = None
    if push_obsidian:
        vault = get_obsidian_vault_path()
        journal_dir = vault / "Journal"
        journal_dir.mkdir(parents=True, exist_ok=True)
        note_path = journal_dir / f"{date_str}_Journal.md"
        note_path.write_text(content, encoding="utf-8")
        note_path_str = str(note_path)
        print(f"[DAILY JOURNAL] Note créée : {note_path}", flush=True)

    return {
        "success": True,
        "date": date_str,
        "total_operations": total_ops,
        "success_operations": success_ops,
        "failed_operations": failed_ops,
        "note_path": note_path_str,
        "content_preview": content[:600],
    }
