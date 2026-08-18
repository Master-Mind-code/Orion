"""
Pont MCP d'Orion — consomme des serveurs MCP externes comme des tools natifs.

Activation : ORION_MCP_ENABLED=true + un mcp_servers.json à la racine.
Les tools d'exécution (ordres de marché) ont leur propre interrupteur,
ORION_TRADING_EXECUTION_ENABLED, volontairement séparé.
"""
from .registry import (  # noqa: F401
    CLIENTS,
    MCP_DANGEROUS,
    MCP_ERRORS,
    MCP_HANDLERS,
    MCP_TOOLS,
    execution_enabled,
    load,
    status,
    unload,
)

HANDLERS = {"mcp_status": lambda p: status()}
