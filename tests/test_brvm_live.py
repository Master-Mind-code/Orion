# -*- coding: utf-8 -*-
"""Tests du collecteur de cote BRVM en temps réel.

Deux familles de tests :
  - hors ligne : parsing, appariement des dividendes, dégradation. Toujours
    exécutés, aucun accès réseau.
  - en ligne   : interrogation réelle des plateformes. Ignorés si le réseau ne
    répond pas, pour qu'une coupure ne fasse pas passer la suite pour cassée.
"""

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from server.trading import brvm_live  # noqa: E402
from server.trading.brvm_engine import BRVMEngine  # noqa: E402


# ════════════════════════════════════════════════════════════════════════════
# Hors ligne
# ════════════════════════════════════════════════════════════════════════════

def test_number_parsing():
    """Les deux sites écrivent les nombres à la française."""
    assert brvm_live._num("36 000") == 36000.0
    assert brvm_live._num("36\xa0000") == 36000.0        # espace insécable
    assert brvm_live._num("1,23") == 1.23                # virgule décimale
    assert brvm_live._num("-6,98%") == -6.98
    assert brvm_live._num("1 358 214 021 FCFA") == 1358214021.0
    assert brvm_live._num("-") is None
    assert brvm_live._num("") is None
    assert brvm_live._num(None) is None


def test_name_normalization():
    """Accents, apostrophes typographiques et insécables ne doivent pas séparer
    deux écritures du même émetteur."""
    assert brvm_live._normalize("SERVAIR ABIDJAN  CÔTE D'IVOIRE") == \
        "SERVAIR ABIDJAN COTE D IVOIRE"
    assert brvm_live._normalize("BANQUE\xa0INTERNATIONALE") == "BANQUE INTERNATIONALE"
    assert brvm_live._normalize("L’INDUSTRIE") == "L INDUSTRIE"


def test_exceptional_dividend_is_detected():
    """Cas réel FILTISAC : 130 FCFA en 2023, puis 1 727 FCFA en 2024.

    Avec seulement deux exercices, la médiane globale (928 FCFA) est tirée vers
    le haut par le versement exceptionnel lui-même et ne le détecte pas : c'est
    pourquoi la comparaison porte sur les exercices antérieurs.
    """
    verdict = brvm_live._assess_dividend({2024: 1727.0, 2023: 130.0})
    assert verdict["dividend_is_exceptional"] is True
    assert verdict["dividend_recurring_xof"] == 130.0, \
        "un revenu ne doit jamais être planifié sur une distribution exceptionnelle"
    assert verdict["dividend_note"]


def test_regular_dividend_is_not_flagged():
    """Un dividende en croissance régulière n'est pas une distribution exceptionnelle."""
    verdict = brvm_live._assess_dividend({2025: 585.0, 2024: 468.0, 2023: 353.0, 2022: 273.0})
    assert verdict["dividend_is_exceptional"] is False
    assert verdict["dividend_recurring_xof"] == 585.0, "on planifie sur le dernier déclaré"


def test_single_year_dividend_is_flagged_as_unverifiable():
    verdict = brvm_live._assess_dividend({2022: 150.0})
    assert verdict["dividend_years_published"] == 1
    assert verdict["dividend_is_exceptional"] is False
    assert "seul exercice" in verdict["dividend_note"]


def test_trend_derivation():
    """La tendance se déduit de la position dans le range 52 semaines."""
    assert brvm_live._derive_trend(95.0, 10.0, 100.0, 0.5) == "BULLISH"
    assert brvm_live._derive_trend(15.0, 10.0, 100.0, 0.5) == "BEARISH"
    assert brvm_live._derive_trend(50.0, 10.0, 100.0, 0.5) == "NEUTRAL"
    # Sans extrêmes 52 semaines, une seule séance ne suffit pas à conclure.
    assert brvm_live._derive_trend(50.0, None, None, 0.4) == "NEUTRAL"


def test_score_tolerates_missing_fundamentals():
    """PER, ROE et marge nette valent None sur les données de marché.

    `stock.get("per", 15.0)` renvoie None quand la clé existe avec cette valeur :
    sans coercion, la comparaison `per <= 0` lèverait un TypeError et toute
    l'analyse tomberait.
    """
    engine = BRVMEngine.__new__(BRVMEngine)  # sans I/O réseau
    score = engine._calculate_orion_score({
        "symbol": "TEST", "dividend_yield_pct": None, "per": None,
        "roe_pct": None, "net_margin_pct": None, "tech_trend": None, "rsi": None,
    }, "balanced")
    assert 10.0 <= score <= 99.9


def test_engine_falls_back_when_sources_are_down(monkeypatch=None):
    """Sources injoignables : on sert la référence, marquée non-live."""
    original = brvm_live.get_snapshot
    brvm_live.get_snapshot = lambda *a, **k: (_ for _ in ()).throw(
        brvm_live.BRVMSourceError("panne réseau simulée"))
    try:
        engine = BRVMEngine.__new__(BRVMEngine)
        data = engine._load_data()
        assert data.get("is_live") is False, "un repli ne doit jamais se dire live"
        assert data.get("stale") is True
        assert data.get("stale_reason")
    finally:
        brvm_live.get_snapshot = original


# ════════════════════════════════════════════════════════════════════════════
# En ligne
# ════════════════════════════════════════════════════════════════════════════

def _online() -> bool:
    try:
        brvm_live._soup(brvm_live.BRVM_QUOTES_URL)
        return True
    except Exception:
        return False


def test_live_quotes_are_plausible():
    """La cote réelle doit couvrir toute la place et donner des cours cohérents."""
    if not _online():
        print("       (ignoré : brvm.org injoignable)")
        return

    payload = brvm_live.fetch_brvm_quotes()
    quotes = payload["quotes"]
    assert len(quotes) >= 40, f"seulement {len(quotes)} valeurs lues, la cote en compte 47"

    for symbol, quote in quotes.items():
        assert quote["price_xof"] and quote["price_xof"] > 0, f"{symbol} sans cours"
        assert -100 < quote["change_pct"] < 100, f"{symbol} : variation aberrante"

    assert payload["session"]["session_status"] in ("OUVERTE", "FERMÉE", "INCONNU")


def test_live_dividends_map_one_to_one():
    """Les libellés tronqués du tableau des dividendes sont rapprochés par
    préfixe : deux valeurs ne doivent jamais tomber sur la même ligne.

    Le risque est concret — six entités « BANK OF AFRICA » sont cotées.
    """
    if not _online():
        print("       (ignoré : sources injoignables)")
        return

    dividends = brvm_live.fetch_sika_dividends()
    directory = brvm_live.fetch_sika_directory()

    claimed: dict = {}
    for symbol, info in directory.items():
        matched = brvm_live._match_dividend(info["name"], dividends)
        if not matched:
            continue
        key = (matched["dividend_year"], matched["dividend_per_share_xof"], info["name"][:4])
        assert key not in claimed, f"{symbol} et {claimed[key]} pointent la même ligne"
        claimed[key] = symbol


def test_live_snapshot_shape():
    """L'instantané doit être directement consommable par BRVMEngine."""
    if not _online():
        print("       (ignoré : sources injoignables)")
        return

    snapshot = brvm_live.build_snapshot()
    assert snapshot["is_live"] is True
    assert len(snapshot["stocks"]) >= 40
    assert snapshot["index"]["value"], "indice BRVM Composite absent"

    for stock in snapshot["stocks"]:
        for field in ("symbol", "name", "price_xof", "sector", "country"):
            assert field in stock, f"{stock.get('symbol')} : champ {field} manquant"
        # Un rendement à trois chiffres signale un dividende mal apparié.
        yield_pct = stock.get("dividend_yield_pct")
        if yield_pct is not None:
            assert yield_pct < 100, f"{stock['symbol']} : rendement {yield_pct}% invraisemblable"


def test_live_history_is_real_ohlcv():
    """L'historique doit être de vraies séances, en ordre chronologique.

    Kronos s'alimentait auparavant de 40 bougies reconstruites par interpolation
    entre la MM50 et le cours du jour : la « prévision neuronale » n'était alors
    qu'une fonction de la tendance affichée.
    """
    if not _online():
        print("       (ignoré : sikafinance injoignable)")
        return

    candles = brvm_live.fetch_sika_history("SNTS.sn")
    assert len(candles) >= 20, f"seulement {len(candles)} séances récupérées"

    timestamps = [c["t"] for c in candles]
    assert timestamps == sorted(timestamps), "séances non triées chronologiquement"

    for candle in candles:
        assert candle["l"] <= candle["c"] <= candle["h"], \
            f"{candle['date']} : clôture hors du range bas/haut"
        assert candle["l"] <= candle["o"] <= candle["h"], \
            f"{candle['date']} : ouverture hors du range bas/haut"
        assert candle["c"] > 0

    # Une interpolation linéaire donnerait des écarts rigoureusement constants.
    deltas = {round(b["c"] - a["c"], 4) for a, b in zip(candles, candles[1:])}
    assert len(deltas) > 3, "variations trop régulières pour être un historique réel"


def test_kronos_reads_the_engine_contract():
    """Le moteur Kronos renvoie `predicted_close` et une confiance entre 0 et 1.

    Lire `pred_close` retombait sur le défaut — le cours actuel — et produisait
    une variation de 0,00 % à chaque appel, sans que rien ne le signale.
    """
    import inspect
    from server.trading import kronos_engine

    source = inspect.getsource(kronos_engine.KronosEngine.predict_market_data)
    assert '"predicted_close"' in source, \
        "le contrat du moteur Kronos a changé : réaligner brvm_engine"
    assert '"pred_close"' not in source

    from server.trading.brvm_engine import BRVMEngine
    caller = inspect.getsource(BRVMEngine.run_kronos_forecast_for_stock)
    assert 'res["predicted_close"]' in caller, \
        "brvm_engine doit lire predicted_close, pas pred_close"
    assert "* 100" in caller, \
        "la confiance Kronos est une fraction 0-1 : elle doit être convertie en %"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  OK   {name}")
        except AssertionError as exc:
            failures += 1
            print(f" FAIL  {name}\n       {exc}")
        except Exception as exc:
            failures += 1
            print(f" ERR   {name}\n       {type(exc).__name__}: {exc}")
    print(f"\n{failures} échec(s)" if failures else "\nTous les tests passent.")
