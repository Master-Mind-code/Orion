"""
Découverte et exposition des tools MCP externes comme tools Orion natifs.

Lit mcp_servers.json à la racine du projet, démarre chaque serveur déclaré,
interroge sa liste de tools, et produit :
  - MCP_TOOLS    : schémas au format attendu par l'orchestrateur
  - MCP_HANDLERS : nom Orion -> callable(params) -> dict
  - MCP_DANGEROUS: nom Orion -> raison, à fusionner dans confirm.DEFAULT_DANGEROUS

Un serveur injoignable ne fait pas tomber Orion : il est signalé dans
MCP_ERRORS et ses tools sont simplement absents.
"""
from __future__ import annotations

import atexit
import fnmatch
import json
import os
import re
import threading
from pathlib import Path

from .client import MCPStdioClient, MCPError

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = ROOT / "mcp_servers.json"

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]")

CLIENTS: dict[str, MCPStdioClient] = {}
MCP_TOOLS: list[dict] = []
MCP_HANDLERS: dict[str, object] = {}
MCP_DANGEROUS: dict[str, str] = {}
MCP_ERRORS: dict[str, str] = {}
_loaded = False
_load_lock = threading.Lock()


def _bridge_enabled() -> bool:
    return os.getenv("ORION_MCP_ENABLED", "false").strip().lower() in (
        "1", "true", "yes", "on", "oui")


def execution_enabled() -> bool:
    """Interrupteur dédié aux tools qui engagent de l'argent réel.

    Séparé de ORION_MCP_ENABLED : on veut pouvoir lire le marché en permanence
    sans jamais risquer qu'un ordre parte.
    """
    return os.getenv("ORION_TRADING_EXECUTION_ENABLED", "false").strip().lower() in (
        "1", "true", "yes", "on", "oui")


def _orion_name(alias: str, tool: str) -> str:
    name = _SAFE_NAME.sub("_", f"{alias}_{tool}")
    return name[:64]


def _selected(tool_name: str, include: list[str], exclude: list[str]) -> bool:
    if exclude and any(fnmatch.fnmatch(tool_name, p) for p in exclude):
        return False
    if include:
        return any(fnmatch.fnmatch(tool_name, p) for p in include)
    return True


def _make_handler(client: MCPStdioClient, remote_name: str, orion_name: str,
                  gated: bool, timeout: float):
    def handler(params: dict) -> dict:
        params = dict(params or {})
        params.pop("target_device", None)  # consommé par l'orchestrateur
        if gated and not execution_enabled():
            return {
                "success": False,
                "error": f"{orion_name} est un tool d'EXÉCUTION (argent réel). "
                         "Bloqué : ORION_TRADING_EXECUTION_ENABLED n'est pas à true. "
                         "Utilise les tools de lecture pour analyser, et demande à "
                         "l'utilisateur d'activer l'exécution s'il veut passer un ordre.",
            }
        try:
            if not client.alive():
                client.start()
            return client.call_tool(remote_name, params, timeout=timeout)
        except MCPError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    return handler


def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        MCP_ERRORS["_config"] = f"mcp_servers.json illisible : {exc}"
        return {}


def load(force: bool = False) -> None:
    """Démarre les serveurs et remplit les registres. Idempotent."""
    global _loaded
    with _load_lock:
        if _loaded and not force:
            return
        if force:
            unload()
        MCP_TOOLS.clear()
        MCP_HANDLERS.clear()
        MCP_DANGEROUS.clear()
        MCP_ERRORS.clear()

        if not _bridge_enabled():
            _loaded = True
            return

        cfg = _load_config()
        for spec in cfg.get("servers", []):
            alias = str(spec.get("alias") or "").strip()
            command = spec.get("command")
            if not alias or not command:
                continue
            if spec.get("enabled") is False:
                continue

            timeout = float(spec.get("timeout", 30))
            client = MCPStdioClient(
                alias=alias, command=command, args=spec.get("args") or [],
                env=spec.get("env") or {}, cwd=spec.get("cwd"), timeout=timeout,
            )
            try:
                client.start()
                tools = client.list_tools()
            except Exception as exc:  # noqa: BLE001
                MCP_ERRORS[alias] = f"{type(exc).__name__}: {exc}"
                client.stop()
                continue

            CLIENTS[alias] = client
            include = spec.get("include") or []
            exclude = spec.get("exclude") or []
            gated_list = spec.get("requires_execution_switch") or []
            prefix = spec.get("description_prefix") or ""

            gardes = 0
            for t in tools:
                remote = t.get("name")
                if not remote or not _selected(remote, include, exclude):
                    continue
                nom = _orion_name(alias, remote)
                gated = any(fnmatch.fnmatch(remote, p) for p in gated_list)
                desc = (t.get("description") or remote).strip()
                if prefix:
                    desc = f"{prefix} {desc}"
                if gated:
                    desc = ("[EXÉCUTION — engage de l'argent réel, demande "
                            "confirmation à l'utilisateur avant d'appeler] ") + desc
                    MCP_DANGEROUS[nom] = f"ordre de marché via {alias} ({remote})"
                    gardes += 1

                schema = t.get("inputSchema") or {"type": "object", "properties": {}}
                schema.setdefault("type", "object")
                schema.setdefault("properties", {})
                MCP_TOOLS.append({
                    "name": nom,
                    "description": desc[:1024],
                    "input_schema": schema,
                })
                MCP_HANDLERS[nom] = _make_handler(client, remote, nom, gated, timeout)

            MCP_ERRORS.pop(alias, None)
            spec["_loaded_tools"] = len(tools)
            spec["_gated"] = gardes

        _loaded = True


def unload() -> None:
    for client in CLIENTS.values():
        client.stop()
    CLIENTS.clear()


# Sans ça, un arrêt d'Orion laisse les process serveurs MCP orphelins : ils
# gardent le terminal MT5 ouvert et s'accumulent à chaque redémarrage.
atexit.register(unload)


def status() -> dict:
    """Diagnostic : serveurs vivants, tools exposés, erreurs, interrupteurs."""
    if not _loaded:
        load()
    return {
        "success": True,
        "bridge_enabled": _bridge_enabled(),
        "execution_enabled": execution_enabled(),
        "config_file": str(CONFIG_FILE),
        "config_present": CONFIG_FILE.exists(),
        "servers": [
            {"alias": a, "alive": c.alive(),
             "server_info": c.server_info,
             "tools": sorted(n for n in MCP_HANDLERS if n.startswith(a + "_"))}
            for a, c in CLIENTS.items()
        ],
        "tool_count": len(MCP_HANDLERS),
        "execution_gated_tools": sorted(MCP_DANGEROUS),
        "errors": dict(MCP_ERRORS),
    }
