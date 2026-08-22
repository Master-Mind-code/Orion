"""
Orion Tools — Module d'Analyse Fondamentale & Choix d'Actions BRVM
Contient les handlers utilisables par l'orchestrateur d'Orion.
"""

from server.trading.brvm_engine import get_brvm_engine


def brvm_stock_picker_tool(input_dict: dict) -> dict:
    """
    Sélecteur d'Actions IA BRVM : recherche et classe les meilleures actions à acheter.

    Params:
        profile: 'dividend' | 'growth' | 'value' | 'balanced' (défaut: 'balanced')
        sector:  Optionnel (ex: 'Finances / Banque', 'Télécommunications', 'Agriculture')
        top_n:   Nombre de recommandations (1 à 10, défaut: 5)
    """
    profile = input_dict.get("profile", "balanced")
    sector = input_dict.get("sector")
    top_n = int(input_dict.get("top_n", 5))

    engine = get_brvm_engine()
    return engine.pick_stocks(profile=profile, sector=sector, top_n=top_n)


def brvm_stock_analysis_tool(input_dict: dict) -> dict:
    """
    Analyse financière complète (Fondamentale + Technique) d'une action de la BRVM.

    Params:
        symbol: Code/Ticker de l'action (ex: 'SNTS', 'ORAC', 'SGBIC', 'CBI', 'PALC')
    """
    symbol = input_dict.get("symbol", "SNTS")
    engine = get_brvm_engine()
    return engine.analyze_stock(symbol)


def brvm_market_overview_tool(input_dict: dict) -> dict:
    """
    Affiche la vue d'ensemble du marché de la BRVM (BRVM Composite, tops dividendes, etc.).
    """
    engine = get_brvm_engine()
    return engine.get_market_overview()


def brvm_income_portfolio_tool(input_dict: dict) -> dict:
    """
    Construit un portefeuille BRVM sur-mesure pour atteindre un objectif de revenu mensuel
    (ex: 150.000 FCFA / mois).

    Params:
        target_monthly_income_xof: Revenu mensuel visé en FCFA (défaut: 150000.0)
    """
    target = float(input_dict.get("target_monthly_income_xof", 150000.0))
    engine = get_brvm_engine()
    return engine.build_income_portfolio(target_monthly_income_xof=target)


def brvm_kronos_predict_tool(input_dict: dict) -> dict:
    """
    Exécute la prédiction prédictive par modèle neuronal Kronos PyTorch sur une action BRVM.

    Params:
        symbol: Code/Ticker de l'action BRVM (ex: 'SNTS', 'SGBIC', 'PALC')
        pred_len: Nombre de séances futures à prédire (défaut: 12)
    """
    symbol = input_dict.get("symbol", "SNTS")
    pred_len = int(input_dict.get("pred_len", 12))
    engine = get_brvm_engine()
    return engine.run_kronos_forecast_for_stock(symbol, pred_len=pred_len)


