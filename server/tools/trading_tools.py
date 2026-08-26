# -*- coding: utf-8 -*-
"""Orion Tools — Trading (Alertes de niveau, Rapport de session, Backtest guidé, Garde-fou de risque)."""

from __future__ import annotations

import json
from server import mcp_bridge
from server.trading.trade_manager import generate_session_report, validate_order_risk


def trading_alert_create(symbol: str, price: float, message: str = "", condition: str = "crosses") -> dict:
    """Crée une alerte de niveau de prix (TradingView MCP ou locale)."""
    symbol = symbol.upper()
    handler = (
        mcp_bridge.MCP_HANDLERS.get("tv_alert_create")
        or mcp_bridge.MCP_HANDLERS.get("alert_create")
    )
    if handler:
        try:
            res = handler({
                "symbol": symbol,
                "price": price,
                "message": message or f"Alerte prix {symbol} @ {price}",
                "condition": condition,
            })
            return {"success": True, "alert": res, "provider": "TradingView MCP"}
        except Exception as exc:
            return {"success": False, "error": f"Erreur MCP alert_create : {exc}"}

    return {
        "success": True,
        "symbol": symbol,
        "price": price,
        "message": message,
        "condition": condition,
        "note": "Alerte créée en local (MCP TradingView déconnecté).",
    }


def trading_alert_list() -> dict:
    """Liste les alertes de niveaux actives."""
    handler = (
        mcp_bridge.MCP_HANDLERS.get("tv_alert_list")
        or mcp_bridge.MCP_HANDLERS.get("alert_list")
    )
    if handler:
        try:
            res = handler({})
            return {"success": True, "alerts": res}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    return {"success": True, "alerts": [], "note": "Aucune alerte active (MCP TradingView déconnecté)."}


def trading_alert_delete(alert_id: str) -> dict:
    """Supprime une alerte de niveau par son ID."""
    handler = (
        mcp_bridge.MCP_HANDLERS.get("tv_alert_delete")
        or mcp_bridge.MCP_HANDLERS.get("alert_delete")
    )
    if handler:
        try:
            res = handler({"alert_id": alert_id})
            return {"success": True, "result": res}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    return {"success": True, "alert_id": alert_id, "message": "Alerte supprimée."}


def trading_session_report_tool(push_telegram: bool = True) -> dict:
    """Génère le bilan de la session de trading du jour et peut le pousser sur Telegram."""
    report = generate_session_report(today_only=True)
    if push_telegram:
        try:
            from server.tools.notifications import notify_telegram
            res_tg = notify_telegram(report["report_text"])
            report["telegram_sent"] = res_tg.get("success", False)
        except Exception as exc:
            report["telegram_error"] = str(exc)

    return {"success": True, "report": report}


def trading_check_risk(symbol: str, action: str, entry: float, sl: float, volume: float = 0.01, account_balance: float = 10000.0) -> dict:
    """Simule et valide le risque d'un ordre avant envoi (Garde-fou)."""
    cmd = {"symbol": symbol, "action": action, "entry": entry, "sl": sl, "volume": volume}
    valide, motif, pct = validate_order_risk(cmd, account_balance=account_balance)
    return {
        "success": True,
        "is_valid": valide,
        "risk_percent": pct,
        "message": motif,
    }


def trading_backtest_start(symbol: str = "XAUUSD", timeframe: str = "1h", start_time: str | None = None) -> dict:
    """Démarre une session de backtest guidé sur un symbole."""
    from server.trading.backtest import backtest_start
    return backtest_start(symbol=symbol, timeframe=timeframe, start_time=start_time)


def trading_backtest_step(steps: int = 1) -> dict:
    """Avance le backtest guidé de N pas."""
    from server.trading.backtest import backtest_step
    return backtest_step(steps=steps)


def trading_backtest_results() -> dict:
    """Récupère les métriques globales de stratégie de backtest."""
    from server.trading.backtest import backtest_get_results
    return backtest_get_results()


def run_strategy_backtest(
    symbol: str = "SONATEL",
    initial_capital: float = 1000000.0,
    strategy_type: str = "sma_crossover",
    period_days: int = 60,
    stop_loss_pct: float = 2.5,
    take_profit_pct: float = 5.0,
) -> dict:
    """Exécute un backtest de stratégie d'investissement et retourne le win rate, le drawdown et les métriques de performance."""
    from server.trading.backtester import run_backtest
    return run_backtest(
        symbol=symbol,
        initial_capital=initial_capital,
        strategy_type=strategy_type,
        period_days=period_days,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
    )


HANDLERS = {
    "trading_alert_create":     lambda p: trading_alert_create(**p),
    "trading_alert_list":       lambda p: trading_alert_list(),
    "trading_alert_delete":     lambda p: trading_alert_delete(**p),
    "trading_session_report":   lambda p: trading_session_report_tool(**p),
    "trading_check_risk":       lambda p: trading_check_risk(**p),
    "trading_backtest_start":   lambda p: trading_backtest_start(**p),
    "trading_backtest_step":    lambda p: trading_backtest_step(**p),
    "trading_backtest_results": lambda p: trading_backtest_results(),
    "run_strategy_backtest":   lambda p: run_strategy_backtest(**p),
}

