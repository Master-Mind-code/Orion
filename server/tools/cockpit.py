"""
Orion Tool — Pilotage du cockpit par Orion lui-même.

Un outil d'INTENTION d'interface : il ne fait rien côté serveur, il signale au
cockpit quel mode afficher. Le résultat voyage par le message `tool_action` que
l'interface reçoit déjà pour chaque exécution d'outil — pas besoin d'un canal
supplémentaire.

Sert à ce que l'écran suive la conversation : quand on demande une analyse de
marché, le poste de trading doit apparaître sans qu'on ait à cliquer.
"""
from __future__ import annotations

MODES = {
    "voice":   "Conversation orale — le réacteur occupe tout l'écran",
    "trading": "Poste de trading — performance, positions, signal IA",
    "desktop": "Poste de bureau — écran en direct, fenêtres, presse-papier",
    "system":  "Poste système — services, pont MCP, audit, coupe-circuit",
}


def cockpit_set_mode(mode: str) -> dict:
    """Bascule le cockpit sur un mode. Purement visuel, aucun effet de bord."""
    m = str(mode).strip().lower()
    if m not in MODES:
        return {"success": False,
                "error": f"Mode inconnu : {mode!r}. Disponibles : "
                         f"{', '.join(sorted(MODES))}."}
    return {"success": True, "mode": m, "description": MODES[m]}


def cockpit_modes() -> dict:
    """Liste les modes du cockpit et ce qu'ils affichent."""
    return {"success": True, "modes": MODES}


HANDLERS = {
    "cockpit_set_mode": lambda p: cockpit_set_mode(**p),
    "cockpit_modes":    lambda p: cockpit_modes(),
}
