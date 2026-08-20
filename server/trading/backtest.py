# -*- coding: utf-8 -*-
"""Module de backtest guidé pour Orion Trading.

Interagit avec le serveur MCP TradingView pour le mode Replay (replay_start,
replay_step, replay_stop) et l'extraction des résultats de stratégie.
"""

import json
from server import mcp_bridge

_backtest_state = {
    "active": False,
    "symbol": None,
    "timeframe": None,
    "current_step": 0,
}


def backtest_start(symbol: str = "XAUUSD", timeframe: str = "1h", start_time: str | None = None) -> dict:
    """Démarre une session de backtest guidé / Replay TradingView sur un symbole donné."""
    symbol = symbol.upper()
    handler = mcp_bridge.MCP_HANDLERS.get("tv_replay_start") or mcp_bridge.MCP_HANDLERS.get("replay_start")
    
    res = {}
    if handler:
        try:
            res = handler({"symbol": symbol, "timeframe": timeframe, "startTime": start_time})
        except Exception as exc:
            res = {"error": str(exc)}

    _backtest_state["active"] = True
    _backtest_state["symbol"] = symbol
    _backtest_state["timeframe"] = timeframe
    _backtest_state["current_step"] = 0

    return {
        "success": True,
        "message": f"Session de backtest guidé démarrée sur {symbol} ({timeframe}).",
        "state": _backtest_state,
        "mcp_result": res,
    }


def backtest_step(steps: int = 1) -> dict:
    """Avance la simulation de backtest d'un ou plusieurs pas (chandelles)."""
    if not _backtest_state["active"]:
        return {"success": False, "error": "Aucun backtest actif. Lance d'abord backtest_start."}

    handler = mcp_bridge.MCP_HANDLERS.get("tv_replay_step") or mcp_bridge.MCP_HANDLERS.get("replay_step")
    res = {}
    if handler:
        try:
            res = handler({"steps": steps})
        except Exception as exc:
            res = {"error": str(exc)}

    _backtest_state["current_step"] += steps
    return {
        "success": True,
        "symbol": _backtest_state["symbol"],
        "timeframe": _backtest_state["timeframe"],
        "current_step": _backtest_state["current_step"],
        "mcp_result": res,
    }


def backtest_stop() -> dict:
    """Arrête la session de backtest Replay active."""
    handler = mcp_bridge.MCP_HANDLERS.get("tv_replay_stop") or mcp_bridge.MCP_HANDLERS.get("replay_stop")
    res = {}
    if handler:
        try:
            res = handler({})
        except Exception as exc:
            res = {"error": str(exc)}

    _backtest_state["active"] = False
    return {"success": True, "message": "Backtest arrêté.", "mcp_result": res}


def backtest_get_results() -> dict:
    """Récupère les résultats et métriques de la stratégie TradingView (Winrate, Profit Factor, Max Drawdown)."""
    handler = mcp_bridge.MCP_HANDLERS.get("tv_data_get_strategy_results") or mcp_bridge.MCP_HANDLERS.get("data_get_strategy_results")
    if not handler:
        return {
            "success": False,
            "error": "Le tool data_get_strategy_results n'est pas accessible. Assure-toi que le serveur MCP TradingView est connecté.",
        }

    try:
        res = handler({})
        return {"success": True, "results": res}
    except Exception as exc:
        return {"success": False, "error": f"Erreur récupération résultats stratégie : {exc}"}
