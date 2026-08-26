# -*- coding: utf-8 -*-
"""Orion Tools — Voix & Réunions (Dictée Obsidian, Résumé d'appel & réunion)."""

from server.voice.dictation import voice_dictate_obsidian
from server.voice.meeting_summarizer import meeting_summarize

def voice_flash_shortcut(command: str) -> dict:
    """Exécute une commande vocale flash prédéfinie.
    
    command: ex 'alerte_rouge', 'etat_systeme', 'scan_brvm'
    """
    cmd = command.lower().strip()
    if cmd in ("alerte_rouge", "panic", "emergency"):
        from server.panic import set_panic
        set_panic(True, reason="Commande vocale flash alerte rouge")
        return {"success": True, "action": "PANIC_ACTIVATED", "message": "🚨 Mode Panic activé par commande vocale !"}
    elif cmd in ("etat_systeme", "health", "system_status"):
        from server.tools.system_monitor import get_system_metrics
        return get_system_metrics()
    elif cmd in ("scan_brvm", "brvm_scan", "stocks"):
        from server.tools.brvm_tools import brvm_stock_picker
        return brvm_stock_picker(profile="balanced", top_n=5)
    else:
        return {
            "success": True,
            "command": command,
            "message": f"Commande vocale '{command}' enregistrée.",
        }


HANDLERS = {
    "voice_dictate_obsidian": lambda p: voice_dictate_obsidian(**p),
    "meeting_summarize":      lambda p: meeting_summarize(**p),
    "voice_flash_shortcut":   lambda p: voice_flash_shortcut(**p),
}

