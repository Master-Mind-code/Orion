"""
Test unitaire et d'intégration du moteur BRVM d'Orion
"""

import sys
import os

orion_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if orion_root not in sys.path:
    sys.path.insert(0, orion_root)

from server.trading.brvm_engine import get_brvm_engine
from server.tools.brvm_tools import brvm_stock_picker_tool, brvm_stock_analysis_tool, brvm_market_overview_tool
from server.tools import ALL_HANDLERS


def test_brvm_engine_and_tools():
    print("=== TEST MOTEUR & TOOLS BRVM ORION ===")

    # 1. Vérification enregistrement des handlers
    print("\n1. Enregistrement des handlers BRVM dans ALL_HANDLERS...")
    assert "brvm_stock_picker" in ALL_HANDLERS, "brvm_stock_picker manquant dans ALL_HANDLERS"
    assert "brvm_stock_analysis" in ALL_HANDLERS, "brvm_stock_analysis manquant dans ALL_HANDLERS"
    assert "brvm_market_overview" in ALL_HANDLERS, "brvm_market_overview manquant dans ALL_HANDLERS"
    print("   [OK] Handlers enregistrés avec succès dans ALL_HANDLERS !")

    # 2. Test vue d'ensemble marché BRVM
    print("\n2. Test de la vue d'ensemble marché BRVM (Market Overview)...")
    overview = brvm_market_overview_tool({})
    print("   Marché :", overview.get("market"))
    print("   Indice BRVM Composite :", overview.get("index", {}).get("value"))
    print("   Nombre d'actions répertoriées :", overview.get("total_listed_stocks"))
    assert overview.get("total_listed_stocks", 0) >= 10

    # 3. Test du Sélecteur d'Actions IA (Stock Picker - Profil Dividende)
    print("\n3. Test du Sélecteur d'Actions IA (Profil Dividende)...")
    picks_div = brvm_stock_picker_tool({"profile": "dividend", "top_n": 3})
    assert picks_div.get("success") == True
    print(f"   Top {len(picks_div.get('picks', []))} actions BRVM (Profil Dividende) :")
    for pick in picks_div.get("picks", []):
        print(f"   - #{pick['rank']} {pick['symbol']} ({pick['name']}) | Score: {pick['orion_score']} | Rendement: {pick['dividend_yield_pct']}% | PER: {pick['per']}x")

    # 4. Test d'Analyse Fondamentale et Technique sur Sonatel (SNTS) et SGBCI (SGBIC)
    print("\n4. Test d'Analyse Fondamentale & Technique détaillée sur Sonatel (SNTS)...")
    analysis_snts = brvm_stock_analysis_tool({"symbol": "SNTS"})
    assert analysis_snts.get("success") == True
    print("   Symbole :", analysis_snts.get("symbol"))
    print("   Recommandation Orion :", analysis_snts.get("recommendation"))
    print("   Orion Score :", analysis_snts.get("orion_score"))
    print("   Rendement Dividende % :", analysis_snts.get("fundamental_analysis", {}).get("dividend_yield_pct"))
    # 5. Test du Portefeuille de Revenu Cible (Mission Survie 150.000 FCFA / mois)
    print("\n5. Test de la Mission de Survie BRVM (Portefeuille 150.000 FCFA / mois)...")
    from server.tools.brvm_tools import brvm_income_portfolio_tool
    assert "brvm_income_portfolio" in ALL_HANDLERS, "brvm_income_portfolio manquant dans ALL_HANDLERS"
    
    income_res = brvm_income_portfolio_tool({"target_monthly_income_xof": 150000.0})
    assert income_res.get("success") == True
    print("   Objectif Mensuel :", income_res.get("target_monthly_income_xof"), "FCFA")
    print("   Revenu Mensuel Estimé :", income_res.get("achieved_monthly_income_xof"), "FCFA")
    print("   Capital Total Requis :", income_res.get("total_capital_required_xof"), "FCFA")
    print("   Rendement Annuel Moyen :", income_res.get("portfolio_average_yield_pct"), "%")
    print(f"   Allocation proposée ({len(income_res.get('allocation', []))} actions) :")
    for item in income_res.get("allocation", []):
        print(f"   - {item['symbol']} ({item['name']}): {item['shares_to_buy']} actions ({item['capital_required_xof']:,.0f} FCFA) -> {item['annual_dividend_expected_xof']:,.0f} FCFA/an")

    # 6. Test de Prédiction Neuronal Kronos adaptative sur une action BRVM (ex: SGBCI / SGBIC)
    print("\n6. Test d'Inférence Neuronal Kronos PyTorch adaptative sur SGBCI (SGBIC)...")
    from server.tools.brvm_tools import brvm_kronos_predict_tool
    assert "brvm_kronos_predict" in ALL_HANDLERS, "brvm_kronos_predict manquant dans ALL_HANDLERS"

    kronos_brvm = brvm_kronos_predict_tool({"symbol": "SGBIC", "pred_len": 12})
    assert kronos_brvm.get("success") == True
    print("   Symbole :", kronos_brvm.get("symbol"))
    print("   Modèle Neural :", kronos_brvm.get("kronos_model"))
    print("   Prix Actuel :", kronos_brvm.get("current_price_xof"), "FCFA")
    print("   Objectif Prédit Kronos :", kronos_brvm.get("kronos_predicted_target_xof"), "FCFA")
    print("   Variation Prédite :", kronos_brvm.get("kronos_predicted_change_pct"), "%")
    print("   Tendance Neuronal :", kronos_brvm.get("kronos_trend_forecast"))
    print("   Score de Confiance Kronos :", kronos_brvm.get("kronos_confidence_score"), "%")
    print("   Recommandation Confluence :", kronos_brvm.get("kronos_recommendation"))

    print("\n[OK] TOUS LES TESTS DE L'INTÉGRATION BRVM + KRONOS NEURAL ENGINE SONT VALIDES ET OPÉRATIONNELS !")


if __name__ == "__main__":
    test_brvm_engine_and_tools()
