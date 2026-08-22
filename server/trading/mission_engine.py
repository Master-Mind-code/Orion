"""
Orion Trading — Mission Engine (100.000 / jour)
Gère l'état de la mission haute performance d'Orion :
- Objectif quotidien (défaut: 100.000)
- Suivi du PnL quotidien cumulé
- Score de Santé & Survie du Capital (Health Score)
- Limites de Drawdown quotidien et bascule en Cooldown d'urgence
"""

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
MISSION_STATE_FILE = DATA_DIR / "mission_state.json"

_lock = Lock()

DEFAULT_STATE: Dict[str, Any] = {
    "daily_target": 100000.0,
    "currency": "USD",
    "current_daily_pnl": 0.0,
    "brvm_monthly_target_xof": 150000.0,
    "brvm_current_monthly_pnl_xof": 0.0,
    "survival_mode": True,
    "max_daily_drawdown_percent": 2.0,
    "cooldown_active": False,
    "cooldown_until": None,
    "health_score": 100.0,
    "trades_today": 0,
    "wins_today": 0,
    "losses_today": 0,
    "best_trade_pnl": 0.0,
    "kronos_signals_scanned": 0,
    "last_reset_date": datetime.now().strftime("%Y-%m-%d"),
    "history_daily": []
}


class MissionEngine:
    _instance = None
    _instance_lock = Lock()

    def __init__(self):
        self.state = self._load_state()
        self._check_daily_reset()

    @classmethod
    def get_instance(cls) -> "MissionEngine":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load_state(self) -> Dict[str, Any]:
        with _lock:
            if MISSION_STATE_FILE.exists():
                try:
                    data = json.loads(MISSION_STATE_FILE.read_text(encoding="utf-8"))
                    merged = dict(DEFAULT_STATE)
                    merged.update(data)
                    return merged
                except Exception:
                    pass
            return dict(DEFAULT_STATE)

    def _save_state(self):
        with _lock:
            MISSION_STATE_FILE.write_text(
                json.dumps(self.state, indent=2, default=str), encoding="utf-8"
            )

    def _check_daily_reset(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.get("last_reset_date") != today:
            # Archiver la journée précédente
            prev_entry = {
                "date": self.state.get("last_reset_date"),
                "pnl": self.state.get("current_daily_pnl", 0.0),
                "target": self.state.get("daily_target", 100000.0),
                "trades": self.state.get("trades_today", 0),
                "wins": self.state.get("wins_today", 0),
            }
            history = self.state.get("history_daily", [])
            history.append(prev_entry)
            # Conserver max 30 jours dans l'historique
            self.state["history_daily"] = history[-30:]

            # Réinitialiser les compteurs du jour
            self.state["last_reset_date"] = today
            self.state["current_daily_pnl"] = 0.0
            self.state["trades_today"] = 0
            self.state["wins_today"] = 0
            self.state["losses_today"] = 0
            self.state["cooldown_active"] = False
            self.state["cooldown_until"] = None
            self.state["best_trade_pnl"] = 0.0
            self._save_state()

    def get_status(self) -> Dict[str, Any]:
        self._check_daily_reset()
        target = self.state.get("daily_target", 100000.0)
        pnl = self.state.get("current_daily_pnl", 0.0)
        progress_pct = round(min(100.0, max(0.0, (pnl / target) * 100.0)), 2) if target > 0 else 0.0

        brvm_target = self.state.get("brvm_monthly_target_xof", 150000.0)
        brvm_pnl = self.state.get("brvm_current_monthly_pnl_xof", 0.0)
        brvm_progress_pct = round(min(100.0, max(0.0, (brvm_pnl / brvm_target) * 100.0)), 2) if brvm_target > 0 else 0.0

        return {
            "daily_target": target,
            "currency": self.state.get("currency", "USD"),
            "current_daily_pnl": round(pnl, 2),
            "progress_percent": progress_pct,
            "brvm_monthly_target_xof": brvm_target,
            "brvm_yearly_target_xof": brvm_target * 12,
            "brvm_current_monthly_pnl_xof": round(brvm_pnl, 2),
            "brvm_monthly_progress_percent": brvm_progress_pct,
            "survival_mode": self.state.get("survival_mode", True),
            "health_score": round(self.state.get("health_score", 100.0), 1),
            "cooldown_active": self.state.get("cooldown_active", False),
            "max_daily_drawdown_percent": self.state.get("max_daily_drawdown_percent", 2.0),
            "trades_today": self.state.get("trades_today", 0),
            "wins_today": self.state.get("wins_today", 0),
            "losses_today": self.state.get("losses_today", 0),
            "win_rate": round(
                (self.state.get("wins_today", 0) / self.state.get("trades_today", 1)) * 100, 1
            ) if self.state.get("trades_today", 0) > 0 else 0.0,
            "best_trade_pnl": round(self.state.get("best_trade_pnl", 0.0), 2),
            "kronos_signals_scanned": self.state.get("kronos_signals_scanned", 0),
            "last_reset_date": self.state.get("last_reset_date")
        }

    def update_config(self, daily_target: float = None, currency: str = None, max_drawdown: float = None, brvm_monthly_target_xof: float = None) -> Dict[str, Any]:
        if daily_target is not None and daily_target > 0:
            self.state["daily_target"] = float(daily_target)
        if currency is not None:
            self.state["currency"] = str(currency).upper()
        if max_drawdown is not None and 0.1 <= max_drawdown <= 20.0:
            self.state["max_daily_drawdown_percent"] = float(max_drawdown)
        if brvm_monthly_target_xof is not None and brvm_monthly_target_xof > 0:
            self.state["brvm_monthly_target_xof"] = float(brvm_monthly_target_xof)
        self._save_state()
        return self.get_status()

    def record_trade(self, pnl: float, symbol: str = "XAUUSD", is_win: bool = None) -> Dict[str, Any]:
        self._check_daily_reset()
        pnl = float(pnl)
        self.state["current_daily_pnl"] += pnl
        self.state["trades_today"] += 1

        if is_win is None:
            is_win = pnl > 0

        if is_win:
            self.state["wins_today"] += 1
            if pnl > self.state.get("best_trade_pnl", 0.0):
                self.state["best_trade_pnl"] = pnl
        else:
            self.state["losses_today"] += 1

        # Mettre à jour le Health Score (santé du capital)
        target = self.state.get("daily_target", 100000.0)
        if pnl < 0:
            drop = min(20.0, (abs(pnl) / (target * 0.05)) * 10)
            self.state["health_score"] = max(10.0, self.state["health_score"] - drop)
        else:
            gain = min(15.0, (pnl / (target * 0.05)) * 5)
            self.state["health_score"] = min(100.0, self.state["health_score"] + gain)

        self._save_state()
        return self.get_status()

    def increment_kronos_scans(self, count: int = 1):
        self.state["kronos_signals_scanned"] = self.state.get("kronos_signals_scanned", 0) + count
        self._save_state()


def get_mission_engine() -> MissionEngine:
    return MissionEngine.get_instance()
