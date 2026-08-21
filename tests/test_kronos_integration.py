"""
Test d'intégration de KronosEngine au sein d'Orion
"""

import sys
import os
from datetime import datetime, timedelta

# Ajouter la racine du projet Orion au PYTHONPATH
orion_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if orion_root not in sys.path:
    sys.path.insert(0, orion_root)

from server.trading.kronos_engine import get_kronos_engine


def test_kronos_engine():
    print("=== TEST INTÉGRATION KRONOS ENGINE ===")
    engine = get_kronos_engine()
    
    # Génération de 50 bougies M5 de test
    now = datetime.now()
    candles = []
    base_price = 2730.0
    for i in range(50):
        t = now - timedelta(minutes=5 * (50 - i))
        o = base_price + (i * 0.1)
        h = o + 1.5
        l = o - 1.2
        c = o + 0.5
        v = 100 + i * 5
        candles.append({"t": int(t.timestamp()), "o": o, "h": h, "l": l, "c": c, "v": v})
        base_price = c

    market_data = {
        "symbol": "XAUUSD",
        "timeframes": {
            "M5": {
                "candles": candles
            }
        }
    }

    print("Lancement de predict_market_data...")
    res = engine.predict_market_data(market_data, pred_len=8)
    
    print("\n=== RÉSULTATS DE LA PRÉDICTION KRONOS ===")
    print("Succès :", res.get("success"))
    if res.get("success"):
        print("Symbole :", res.get("symbol"))
        print("Prix actuel :", res.get("current_close"))
        print("Prix cible prédit :", res.get("predicted_close"))
        print("Variation prédite :", f"{res.get('predicted_change_pct'):+}%")
        print("Biais directionnel :", res.get("directional_bias"))
        print("Score de confiance :", res.get("confidence"))
        print("Extrême High max :", res.get("predicted_high_max"))
        print("Extrême Low min :", res.get("predicted_low_min"))
        print("Nombre de bougies prédites :", len(res.get("predicted_candles", [])))
        print("Deux premières bougies prédites :", res.get("predicted_candles", [])[:2])
    else:
        print("Erreur :", res.get("error"))

    assert res.get("success") == True, f"Échec du test: {res.get('error')}"
    print("\n[OK] TEST KRONOS ENGINE REUSSI AVEC SUCCES !")


if __name__ == "__main__":
    test_kronos_engine()
