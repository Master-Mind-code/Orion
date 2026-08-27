# -*- coding: utf-8 -*-
"""Tests de cohérence du registre d'outils d'Orion.

Un outil n'est réellement utilisable que si DEUX conditions sont réunies :
  1. son schéma est présent dans orchestrator.TOOLS  → le LLM sait qu'il existe ;
  2. son handler est présent dans tools.ALL_HANDLERS → l'appel trouve du code.

Un handler sans schéma est du code mort (le LLM ne l'appellera jamais) ; un
schéma sans handler produit une erreur d'exécution. Ces tests verrouillent la
parité entre les deux, pour qu'un nouveau module ajouté à ALL_HANDLERS sans
schéma casse la CI au lieu de passer inaperçu.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Force UTF-8 sur stdout pour la console Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from server import orchestrator  # noqa: E402
from server.tools import ALL_HANDLERS  # noqa: E402

# Outils traités en dur dans execute_tool() : ils ont un schéma mais pas
# d'entrée dans ALL_HANDLERS, c'est voulu.
SERVER_SIDE_TOOLS = {"list_connected_devices"}


def _schema_names() -> set[str]:
    return {t["name"] for t in orchestrator.TOOLS}


def test_no_duplicate_tool_names():
    """Deux schémas du même nom : le second masque silencieusement le premier."""
    names = [t["name"] for t in orchestrator.TOOLS]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    assert not duplicates, f"Noms d'outils dupliqués dans TOOLS : {duplicates}"


def test_every_handler_has_a_schema():
    """Aucun handler ne doit rester invisible pour le LLM."""
    orphans = sorted(set(ALL_HANDLERS) - _schema_names())
    assert not orphans, (
        f"{len(orphans)} handler(s) sans schéma dans orchestrator.TOOLS — "
        f"le LLM ne pourra jamais les appeler : {orphans}"
    )


def test_every_schema_has_a_handler():
    """Aucun schéma ne doit pointer dans le vide."""
    dangling = sorted(_schema_names() - set(ALL_HANDLERS) - SERVER_SIDE_TOOLS)
    assert not dangling, (
        f"{len(dangling)} schéma(s) sans handler — tout appel échouera : {dangling}"
    )


def test_schemas_are_valid_json_schema_objects():
    """Chaque schéma doit être sérialisable et déclarer des 'required' réels."""
    for tool in orchestrator.TOOLS:
        name = tool["name"]
        assert tool.get("description"), f"'{name}' n'a pas de description."

        schema = tool["input_schema"]
        assert schema.get("type") == "object", f"'{name}' : input_schema.type != 'object'."

        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            assert required in properties, (
                f"'{name}' : le paramètre requis '{required}' n'est pas déclaré "
                f"dans properties."
            )

        # Le schéma part tel quel dans la requête API : il doit être sérialisable.
        json.dumps(schema)


def test_device_bound_tools_exist():
    """_DEVICE_BOUND_TOOLS ne doit pas référencer d'outils disparus."""
    unknown = sorted(orchestrator._DEVICE_BOUND_TOOLS - _schema_names())
    assert not unknown, (
        f"_DEVICE_BOUND_TOOLS cite des outils absents de TOOLS : {unknown}"
    )


if __name__ == "__main__":
    for fn_name, fn in sorted(list(globals().items())):
        if fn_name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  OK   {fn_name}")
            except AssertionError as exc:
                print(f" FAIL  {fn_name}\n       {exc}")
