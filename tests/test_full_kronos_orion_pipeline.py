"""
Test global de validation de l'intégration Kronos + Orion (Full Pipeline)
"""

import sys
import os
from datetime import datetime, timedelta

orion_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if orion_root not in sys.path:
    sys.path.insert(0, orion_root)

from server.tools import ALL_HANDLERS
from server.trading.analyzer import build_analysis_prompt
from server.tools.kronos_tools import kronos_predict_candles, kronos_model_status


def test_full_pipeline():
    print("=== TEST PIPELINE COMPLET ORION + KRONOS ===")

    # 1. Vérification de l'enregistrement des handlers dans ALL_HANDLERS
    print("\n1. Enregistrement des handlers dans server/tools...")
    assert "kronos_predict_candles" in ALL_HANDLERS, "kronos_predict_candles manquant dans ALL_HANDLERS"
    assert "kronos_model_status" in ALL_HANDLERS, "kronos_model_status manquant dans ALL_HANDLERS"
    print("   [OK] Handlers enregistrés avec succès dans ALL_HANDLERS !")

    # 2. Test du handler kronos_model_status
    print("\n2. Test du statut du modèle Kronos...")
    status = kronos_model_status()
    print("   Statut :", status)
    assert status.get("success") == True

    # 3. Test du handler kronos_predict_candles
    print("\n3. Test d'inférence de l'outil kronos_predict_candles...")
    pred_tool_res = kronos_predict_candles(symbol="EURUSD", pred_len=8)
    print("   Résultat de l'outil :", pred_tool_res.get("success"))
    assert pred_tool_res.get("success") == True

    # 4. Test d'intégration du prompt de l'analyseur IA (Claude + Kronos)
    print("\n4. Test de synthèse de l'analyseur IA Orion (Prompt Claude avec Kronos)...")
    now = datetime.now()
    candles = []
    base_price = 1.0850
    for i in range(40):
        t = now - timedelta(minutes=5 * (40 - i))
        c = base_price + (i * 0.0001)
        candles.append({"t": int(t.timestamp()), "o": c-0.0001, "h": c+0.0003, "l": c-0.0002, "c": c, "v": 500})

    market_data = {
        "symbol": "EURUSD",
        "bid": 1.0890,
        "ask": 1.0892,
        "spread": 2,
        "timeframes": {
            "M5": {
                "candles": candles,
                "atr": 0.0008,
                "swing_high": 1.0895,
                "swing_low": 1.0840
            }
        }
    }

    prompt = build_analysis_prompt(market_data)
    print("   Contient la section KRONOS NEURAL FOUNDATION FORECAST :", "KRONOS NEURAL FOUNDATION FORECAST" in prompt)
    assert "KRONOS NEURAL FOUNDATION FORECAST" in prompt, "Section Kronos manquante dans le prompt d'analyse"

    print("\n[OK] TOUS LES TESTS DE L'INTÉGRATION ORION + KRONOS SONT VALIDES ET OPÉRATIONNELS !")


if __name__ == "__main__":
    test_full_pipeline()
