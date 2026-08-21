"""
Orion Trading — Kronos Neural Engine
Intégration du Foundation Model Kronos (Tokenizer BSQuantizer + Transformer Autorégressif)
pour la prédiction de chandeliers K-lines (OHLCV) dans l'assistant Orion.
"""

import sys
import os
import time
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import torch

# Log Configuration
logger = logging.getLogger("orion.kronos")

# Ajout dynamique du chemin du dépôt Kronos si disponible
KRONOS_REPO_PATH = r"C:\Users\ebahn\Documents\Projets\Kronos"
if os.path.exists(KRONOS_REPO_PATH) and KRONOS_REPO_PATH not in sys.path:
    sys.path.insert(0, KRONOS_REPO_PATH)

# Tentative d'importation des classes Kronos
KRONOS_MODULES_AVAILABLE = False
try:
    from model.kronos import KronosTokenizer, Kronos, KronosPredictor
    KRONOS_MODULES_AVAILABLE = True
    logger.info("[KronosEngine] Les modules Kronos PyTorch ont été chargés avec succès.")
except Exception as e:
    logger.warning(f"[KronosEngine] Impossible de charger le module model.kronos: {e}")


class KronosEngine:
    """
    Gestionnaire Singleton d'inférence Kronos pour Orion.
    Gère le chargement paresseux (lazy loading), les prédictions unitaires,
    les simulations Monte-Carlo et l'analyse de confiance.
    """
    _instance: Optional["KronosEngine"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: str = "NeoQuasar/Kronos-mini", tokenizer_name: str = "NeoQuasar/Kronos-Tokenizer-base"):
        self.model_name = model_name
        self.tokenizer_name = tokenizer_name
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        
        self.tokenizer = None
        self.model = None
        self.predictor = None
        
        self.is_loaded = False
        self.loading_error = None
        self._load_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "KronosEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def load_model_if_needed(self) -> bool:
        """
        Charge les poids des modèles Kronos depuis HuggingFace Hub si non chargés.
        """
        if self.is_loaded:
            return True
        
        if not KRONOS_MODULES_AVAILABLE:
            self.loading_error = "Les modules Python Kronos ne sont pas installés/disponibles dans le chemin."
            return False

        with self._load_lock:
            if self.is_loaded:
                return True
            
            try:
                logger.info(f"[KronosEngine] Chargement de KronosTokenizer ({self.tokenizer_name}) et Predictor ({self.model_name}) sur {self.device}...")
                
                # Chargement du Tokenizer et du Modèle
                self.tokenizer = KronosTokenizer.from_pretrained(self.tokenizer_name)
                self.model = Kronos.from_pretrained(self.model_name)
                
                self.tokenizer.eval()
                self.model.eval()

                # Instanciation de l'enrobeur KronosPredictor
                self.predictor = KronosPredictor(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=self.device,
                    max_context=512,
                    clip=5.0
                )

                self.is_loaded = True
                self.loading_error = None
                logger.info("[KronosEngine] Modèles Kronos chargés et prêts pour l'inférence !")
                return True

            except Exception as e:
                self.loading_error = f"Erreur lors du chargement des poids Kronos: {str(e)}"
                logger.error(f"[KronosEngine] {self.loading_error}")
                return False

    def extract_candles_df(self, market_data: Dict[str, Any], default_tf: str = "M5") -> Optional[tuple[pd.DataFrame, pd.DatetimeIndex, str]]:
        """
        Extrait et formate un DataFrame nettoyé depuis le payload market_data d'Orion.
        """
        tfs = market_data.get("timeframes", {})
        candles_list = []
        selected_tf = default_tf

        if selected_tf in tfs and len(tfs[selected_tf].get("candles", [])) >= 30:
            candles_list = tfs[selected_tf]["candles"]
        elif "candles" in market_data and len(market_data["candles"]) >= 30:
            candles_list = market_data["candles"]
            selected_tf = market_data.get("timeframe", default_tf)
        else:
            # Recherche du premier timeframe disponible avec assez de bougies
            for tf_key, tf_val in tfs.items():
                if len(tf_val.get("candles", [])) >= 30:
                    candles_list = tf_val["candles"]
                    selected_tf = tf_key
                    break

        if not candles_list:
            return None

        # Transformation en DataFrame pandas
        records = []
        for c in candles_list:
            ts = c.get("t")
            if isinstance(ts, (int, float)):
                dt = datetime.fromtimestamp(ts)
            elif isinstance(ts, str):
                try:
                    dt = pd.to_datetime(ts)
                except Exception:
                    dt = datetime.now()
            else:
                dt = datetime.now()

            o = float(c.get("o", 0.0))
            h = float(c.get("h", o))
            l = float(c.get("l", o))
            close = float(c.get("c", o))
            vol = float(c.get("v", 0.0))
            amt = float(c.get("amt", vol * close))

            records.append({
                "timestamps": dt,
                "open": o,
                "high": h,
                "low": l,
                "close": close,
                "volume": vol,
                "amount": amt
            })

        df = pd.DataFrame(records)
        df = df.sort_values("timestamps").reset_index(drop=True)
        timestamps = pd.DatetimeIndex(df["timestamps"])

        return df, timestamps, selected_tf

    def predict_market_data(
        self,
        market_data: Dict[str, Any],
        pred_len: int = 12,
        T: float = 1.0,
        top_k: int = 1,
        top_p: float = 0.9,
        sample_count: int = 1
    ) -> Dict[str, Any]:
        """
        Exécute la prédiction neuronale Kronos sur le payload market_data d'Orion.
        """
        if not self.load_model_if_needed():
            return {
                "success": False,
                "error": self.loading_error or "Kronos non disponible",
                "bias": "NEUTRAL",
                "confidence": 0.0
            }

        extracted = self.extract_candles_df(market_data)
        if not extracted:
            return {
                "success": False,
                "error": "Historique de bougies insuffisant (< 30 bougies) dans market_data.",
                "bias": "NEUTRAL",
                "confidence": 0.0
            }

        df, timestamps, timeframe = extracted

        # Transformation en pandas Series pour compatibilité avec Kronos.calc_time_stamps (.dt accessor)
        x_timestamp_series = pd.Series(pd.to_datetime(df["timestamps"]))

        if len(x_timestamp_series) > 1:
            time_diff = x_timestamp_series.iloc[-1] - x_timestamp_series.iloc[-2]
        else:
            time_diff = timedelta(minutes=5)

        last_time = x_timestamp_series.iloc[-1]
        future_times = [last_time + (i + 1) * time_diff for i in range(pred_len)]
        y_timestamp_series = pd.Series(future_times)

        try:
            with torch.no_grad():
                pred_df = self.predictor.predict(
                    df=df[['open', 'high', 'low', 'close', 'volume', 'amount']],
                    x_timestamp=x_timestamp_series,
                    y_timestamp=y_timestamp_series,
                    pred_len=pred_len,
                    T=T,
                    top_k=top_k,
                    top_p=top_p,
                    sample_count=sample_count,
                    verbose=False
                )


            current_close = float(df["close"].iloc[-1])
            pred_closes = pred_df["close"].values
            pred_highs = pred_df["high"].values
            pred_lows = pred_df["low"].values
            
            final_pred_close = float(pred_closes[-1])
            pred_max_high = float(np.max(pred_highs))
            pred_min_low = float(np.min(pred_lows))

            change_pct = ((final_pred_close - current_close) / current_close) * 100.0

            # Biais directionnel avec seuil à ±0.12%
            if change_pct > 0.12:
                bias = "BULLISH"
            elif change_pct < -0.12:
                bias = "BEARISH"
            else:
                bias = "NEUTRAL"

            # Score de confiance basé sur la cohérence de tendance et la régularité
            trend_consistency = np.mean(np.diff(pred_closes) > 0) if bias == "BULLISH" else np.mean(np.diff(pred_closes) < 0)
            confidence = min(0.95, max(0.55, 0.50 + abs(change_pct) * 0.15 + float(trend_consistency) * 0.25))

            # Formattage des bougies prédites
            predicted_candles = []
            for idx, row in pred_df.iterrows():
                predicted_candles.append({
                    "timestamp": idx.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": round(float(row["open"]), 5),
                    "high": round(float(row["high"]), 5),
                    "low": round(float(row["low"]), 5),
                    "close": round(float(row["close"]), 5),
                    "volume": round(float(row["volume"]), 2)
                })

            return {
                "success": True,
                "symbol": market_data.get("symbol", "UNKNOWN"),
                "timeframe": timeframe,
                "current_close": round(current_close, 5),
                "predicted_close": round(final_pred_close, 5),
                "predicted_change_pct": round(change_pct, 3),
                "predicted_high_max": round(pred_max_high, 5),
                "predicted_low_min": round(pred_min_low, 5),
                "directional_bias": bias,
                "confidence": round(confidence, 2),
                "pred_len": pred_len,
                "predicted_candles": predicted_candles,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"[KronosEngine] Erreur pendant l'inférence: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erreur lors de l'inférence Kronos: {str(e)}",
                "bias": "NEUTRAL",
                "confidence": 0.0
            }

    def run_monte_carlo_simulations(
        self,
        market_data: Dict[str, Any],
        pred_len: int = 12,
        n_samples: int = 10
    ) -> Dict[str, Any]:
        """
        Exécute N simulations Monte-Carlo (échantillonnage stochastique T=1.0, top_p=0.9)
        pour obtenir le cône de probabilité (percentiles 10%, 50%, 90%).
        """
        results = []
        for _ in range(n_samples):
            res = self.predict_market_data(market_data, pred_len=pred_len, T=1.0, top_k=0, top_p=0.9)
            if res.get("success") and "predicted_candles" in res:
                results.append([c["close"] for c in res["predicted_candles"]])

        if not results:
            return {"success": False, "error": "Échec des simulations Monte-Carlo"}

        arr = np.array(results) # Shape: (n_samples, pred_len)
        p10 = np.percentile(arr, 10, axis=0).tolist()
        p50 = np.percentile(arr, 50, axis=0).tolist()
        p90 = np.percentile(arr, 90, axis=0).tolist()

        return {
            "success": True,
            "n_samples": n_samples,
            "pred_len": pred_len,
            "p10_lower_bound": [round(x, 5) for x in p10],
            "p50_median": [round(x, 5) for x in p50],
            "p90_upper_bound": [round(x, 5) for x in p90],
        }


# Global helper function for quick access
def get_kronos_engine() -> KronosEngine:
    return KronosEngine.get_instance()
