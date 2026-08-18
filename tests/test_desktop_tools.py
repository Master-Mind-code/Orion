"""
Vérifie la cohérence des tools de pilotage du bureau.

Ne déclenche AUCUNE action physique : l'interrupteur est forcé à false et seuls
les chemins de lecture / refus sont exercés.

Lancer : python -m pytest tests/test_desktop_tools.py -v
      ou : python tests/test_desktop_tools.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Doit être posé avant l'import des tools : l'interrupteur est lu à chaque appel,
# mais on veut aussi éviter tout effet de bord à l'import.
os.environ["ORION_AUTOMATION_ENABLED"] = "false"

from server.orchestrator import TOOLS, _DEVICE_BOUND_TOOLS  # noqa: E402
from server.tools import ALL_HANDLERS  # noqa: E402
from server.confirm import DEFAULT_DANGEROUS  # noqa: E402

DESKTOP_TOOLS = {
    "automation_status", "mouse_position", "mouse_move", "mouse_click",
    "mouse_drag", "mouse_scroll", "keyboard_type", "keyboard_press",
    "keyboard_key", "clipboard_get", "clipboard_set",
    "list_windows", "focus_window", "window_control",
}

# Tools qui agissent physiquement : doivent refuser quand l'interrupteur est coupé.
GATED = {
    "mouse_move", "mouse_click", "mouse_drag", "mouse_scroll",
    "keyboard_type", "keyboard_press", "keyboard_key",
    "clipboard_set", "focus_window", "window_control",
}


# Tools traités directement dans l'orchestrateur (avant le lookup ALL_HANDLERS)
# et qui n'ont donc légitimement pas de handler dans server/tools/.
INTERCEPTES = {"list_connected_devices"}


def test_chaque_schema_a_un_handler():
    noms = {t["name"] for t in TOOLS} - INTERCEPTES
    orphelins = sorted(noms - set(ALL_HANDLERS))
    assert not orphelins, f"Schémas sans handler : {orphelins}"


def test_chaque_tool_bureau_est_declare():
    noms = {t["name"] for t in TOOLS}
    manquants = sorted(DESKTOP_TOOLS - noms)
    assert not manquants, f"Tools bureau absents de TOOLS : {manquants}"

    sans_handler = sorted(DESKTOP_TOOLS - set(ALL_HANDLERS))
    assert not sans_handler, f"Tools bureau sans handler : {sans_handler}"


def test_tools_bureau_sont_device_bound():
    """Sinon un 'clique sur mon téléphone' s'exécuterait sur le serveur."""
    manquants = sorted(DESKTOP_TOOLS - _DEVICE_BOUND_TOOLS)
    assert not manquants, f"Tools bureau non routables : {manquants}"


def test_schemas_valides():
    for t in TOOLS:
        assert t.get("description"), f"{t['name']} sans description"
        schema = t["input_schema"]
        assert schema["type"] == "object", f"{t['name']} : type != object"
        for champ in schema.get("required", []):
            assert champ in schema.get("properties", {}), \
                f"{t['name']} : '{champ}' requis mais absent des properties"


def test_actions_physiques_refusees_quand_coupe():
    os.environ["ORION_AUTOMATION_ENABLED"] = "false"
    echantillon = {
        "mouse_move": {"x": 10, "y": 10},
        "mouse_click": {"x": 10, "y": 10},
        "mouse_drag": {"from_x": 0, "from_y": 0, "to_x": 5, "to_y": 5},
        "mouse_scroll": {"amount": 1},
        "keyboard_type": {"text": "x"},
        "keyboard_press": {"keys": "escape"},
        "keyboard_key": {"keys": "escape"},
        "clipboard_set": {"text": "x"},
        "focus_window": {"title_contains": "zzz-inexistant"},
        "window_control": {"title_contains": "zzz-inexistant", "action": "minimize"},
    }
    assert set(echantillon) == GATED, "Échantillon désynchronisé de GATED"
    for nom, params in echantillon.items():
        res = ALL_HANDLERS[nom](params)
        assert res["success"] is False, f"{nom} a agi alors que l'interrupteur est coupé !"
        assert "désactivée" in res["error"] or "installé" in res["error"], \
            f"{nom} : refus inattendu → {res['error']}"


def test_lectures_autorisees_quand_coupe():
    """Ces tools doivent répondre même interrupteur coupé."""
    for nom in ("automation_status", "mouse_position", "list_windows", "clipboard_get"):
        res = ALL_HANDLERS[nom]({})
        assert "success" in res, f"{nom} : réponse malformée"
        if res["success"] is False:
            # Seul motif acceptable : la lib optionnelle n'est pas installée.
            assert "installé" in res["error"], f"{nom} refusé à tort → {res['error']}"


def test_tools_sensibles_dans_confirm():
    for nom in ("mouse_click", "mouse_drag", "keyboard_type", "keyboard_key",
                "window_control"):
        assert nom in DEFAULT_DANGEROUS, f"{nom} absent de DEFAULT_DANGEROUS"


if __name__ == "__main__":
    fails = 0
    for nom, fn in sorted(globals().items()):
        if not nom.startswith("test_"):
            continue
        try:
            fn()
            print(f"  OK   {nom}")
        except AssertionError as exc:
            fails += 1
            print(f"  FAIL {nom}\n       {exc}")
    print("\nTous les tests passent." if not fails else f"\n{fails} test(s) en échec.")
    sys.exit(1 if fails else 0)
