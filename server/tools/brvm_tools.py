"""
Orion Tools — Module d'Analyse Fondamentale & Choix d'Actions BRVM
Contient les handlers utilisables par l'orchestrateur d'Orion.
"""

from server.trading.brvm_engine import get_brvm_engine
from server.trading import brvm_live


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


def brvm_live_quote_tool(input_dict: dict) -> dict:
    """
    Cote en direct d'une ou plusieurs valeurs de la BRVM (cours, variation, volume).

    Réponse légère, sans scoring ni prédiction : à utiliser pour répondre à
    « combien vaut X ? » sans déclencher l'analyse complète.

    Params:
        symbols: Liste de codes ou chaîne séparée par des virgules (ex: 'SNTS,ORAC').
                 Vide = toute la cote.
    """
    raw = input_dict.get("symbols") or []
    if isinstance(raw, str):
        raw = [s for s in raw.replace(";", ",").split(",") if s.strip()]
    wanted = {s.strip().upper() for s in raw}

    engine = get_brvm_engine()
    stocks = engine.data.get("stocks", [])
    if wanted:
        stocks = [s for s in stocks if s.get("symbol", "").upper() in wanted]

    quotes = [{
        "symbol": s.get("symbol"),
        "name": s.get("name"),
        "price_xof": s.get("price_xof"),
        "change_pct": s.get("change_pct"),
        "previous_close_xof": s.get("previous_close_xof"),
        "open_xof": s.get("open_xof"),
        "volume": s.get("volume"),
        "volume_xof": s.get("volume_xof"),
        "market_cap_xof": s.get("market_cap_xof"),
        "sector": s.get("sector"),
        "country": s.get("country"),
    } for s in stocks]

    unknown = sorted(wanted - {q["symbol"] for q in quotes}) if wanted else []

    return {
        "success": bool(quotes),
        "currency": "XOF",
        "quotes_count": len(quotes),
        "quotes": quotes,
        "unknown_symbols": unknown,
        "index": engine.data.get("index", {}),
        "data_provenance": engine._provenance(),
        "error": f"Aucune valeur trouvée pour : {', '.join(unknown)}" if not quotes else None,
    }


def brvm_market_refresh_tool(input_dict: dict) -> dict:
    """
    Force la récupération de la cote BRVM et rapporte l'état de chaque source.

    Params:
        check_sources: Tester chaque plateforme une à une et rapporter son état
                       (défaut: False — plus lent, une requête par source).
    """
    check_sources = bool(input_dict.get("check_sources", False))

    engine = get_brvm_engine()
    try:
        engine.refresh(force=True)
        refreshed = True
        error = None
    except Exception as exc:
        refreshed = False
        error = f"{type(exc).__name__}: {exc}"

    result = {
        "success": refreshed,
        "error": error,
        "stocks_loaded": len(engine.data.get("stocks", [])),
        "index": engine.data.get("index", {}),
        "sources_used": engine.data.get("sources", {}),
        "data_provenance": engine._provenance(),
    }
    if check_sources:
        result["source_health"] = brvm_live.source_health()
    return result


