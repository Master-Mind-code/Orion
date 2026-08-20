# -*- coding: utf-8 -*-
"""Module de journalisation automatique de trades pour Obsidian.

Écrit les trades ouverts/fermés avec métadonnées YAML et capture d'écran
TradingView dans le coffre Obsidian de l'utilisateur.
"""

import json
import os
import shutil
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


def log_trade_journal(trade_data: dict, screenshot_path: str | None = None) -> dict:
    """Génère une note Markdown détaillée dans le coffre Obsidian pour un trade."""
    vault = get_obsidian_vault_path()
    trades_dir = vault / "Trades"
    attachments_dir = vault / "attachments"
    trades_dir.mkdir(parents=True, exist_ok=True)
    attachments_dir.mkdir(parents=True, exist_ok=True)

    ticket = trade_data.get("ticket") or trade_data.get("id") or int(datetime.now().timestamp())
    symbol = str(trade_data.get("symbol", "XAUUSD")).upper()
    action = str(trade_data.get("action") or trade_data.get("type", "BUY")).upper()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_filename = datetime.now().strftime("%Y-%m-%d")

    entry = trade_data.get("entry") or trade_data.get("price") or 0.0
    sl = trade_data.get("sl") or 0.0
    tp = trade_data.get("tp") or 0.0
    profit = trade_data.get("profit", 0.0)
    volume = trade_data.get("volume") or trade_data.get("lots") or 0.01
    comment = trade_data.get("comment", "Trade Orion")

    # Copie de la capture d'écran si fournie
    img_markdown = "*Aucune capture jointe*"
    if screenshot_path:
        src = Path(screenshot_path).expanduser()
        if src.exists():
            dest_img = attachments_dir / f"trade_{ticket}_{src.name}"
            try:
                shutil.copy(src, dest_img)
                img_markdown = f"![Capture TradingView](attachments/{dest_img.name})"
            except Exception as exc:
                img_markdown = f"*Erreur copie capture : {exc}*"

    filename = f"{date_filename}_{symbol}_{action}_ticket{ticket}.md"
    note_path = trades_dir / filename

    content = f"""---
date: {now_str}
ticket: {ticket}
symbol: {symbol}
action: {action}
volume: {volume}
entry: {entry}
sl: {sl}
tp: {tp}
profit: {profit}
comment: "{comment}"
tags:
  - trade-journal
  - OrionTrading
---

# 📊 Trade #{ticket} — {symbol} ({action})

- **Date & Heure** : {now_str}
- **Action** : `{action}` | **Volume** : `{volume}` lots
- **Entrée** : `{entry}` | **SL** : `{sl}` | **TP** : `{tp}`
- **PnL Résultat** : `{profit:+.2f} $`
- **Commentaire** : {comment}

---

## 📈 Graphique TradingView
{img_markdown}

---
*Note générée automatiquement par Orion Trading Journal.*
"""

    note_path.write_text(content, encoding="utf-8")
    print(f"[JOURNAL OBSIDIAN] Note créée : {note_path}", flush=True)

    return {
        "success": True,
        "vault_path": str(vault),
        "note_path": str(note_path),
        "filename": filename,
    }
