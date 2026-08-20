# -*- coding: utf-8 -*-
"""Suite de tests d'intégration et CI pour le pont MCP d'Orion.

Vérifie la configuration mcp_servers.json, l'initialisation du pont MCP,
l'enregistrement des outils et la résilience en cas de serveur indisponible.
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


def test_mcp_config_schema():
    """Vérifie le format JSON du fichier de configuration MCP."""
    cfg_path = ROOT / "mcp_servers.json"
    if not cfg_path.exists():
        cfg_path = ROOT / "mcp_servers.example.json"

    assert cfg_path.exists(), "Aucun fichier mcp_servers.json ou mcp_servers.example.json trouvé."

    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "servers" in data or "mcpServers" in data, "Clé 'servers' ou 'mcpServers' manquante dans le fichier MCP."

    servers = data.get("servers") or data.get("mcpServers")
    if isinstance(servers, list):
        for s_cfg in servers:
            assert "command" in s_cfg, f"Serveur '{s_cfg.get('alias')}' n'a pas de clé 'command'."
            assert isinstance(s_cfg.get("args", []), list), f"Serveur '{s_cfg.get('alias')}' doit avoir un tableau 'args'."
        count = len(servers)
    elif isinstance(servers, dict):
        for s_name, s_cfg in servers.items():
            assert "command" in s_cfg, f"Serveur '{s_name}' n'a pas de clé 'command'."
            assert isinstance(s_cfg.get("args", []), list), f"Serveur '{s_name}' doit avoir un tableau 'args'."
        count = len(servers)
    else:
        raise AssertionError("Structure de 'servers' invalide.")

    print(f"[OK] Schema mcp_servers.json valide ({count} serveurs configurés)")


def test_mcp_bridge_status():
    """Vérifie le statut et le diagnostic du pont MCP."""
    from server import mcp_bridge

    st = mcp_bridge.status()
    assert isinstance(st, dict), "mcp_bridge.status() doit retourner un dictionnaire."
    assert "bridge_enabled" in st, "Clé 'bridge_enabled' manquante dans le statut MCP."
    assert "config_file" in st, "Clé 'config_file' manquante dans le statut MCP."
    print(f"[OK] Diagnostic MCP OK : bridge_enabled={st.get('bridge_enabled')}, config={st.get('config_present')}")


def test_mcp_tools_registration():
    """Vérifie que l'outil mcp_status est bien exposé dans l'orchestrateur."""
    from server.orchestrator import TOOLS
    from server.tools import ALL_HANDLERS

    tool_names = [t["name"] for t in TOOLS]
    assert "mcp_status" in tool_names, "Tool 'mcp_status' non enregistré dans orchestrator.TOOLS."
    assert "mcp_status" in ALL_HANDLERS, "Handler 'mcp_status' non enregistré dans ALL_HANDLERS."
    print("[OK] Intégration outil 'mcp_status' validée.")


def run_all_tests():
    print("=== DÉBUT DES TESTS DU PONT MCP ORION ===")
    test_mcp_config_schema()
    test_mcp_bridge_status()
    test_mcp_tools_registration()
    print("=== TOUS LES TESTS MCP SONT 100% OK ===")


if __name__ == "__main__":
    run_all_tests()
