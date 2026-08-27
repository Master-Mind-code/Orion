"""
Orion Trading — BRVM Engine (Bourse Régionale des Valeurs Mobilières UEMOA)
Moteur d'Analyse Fondamentale, Technique & Sélecteur d'Actions IA.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from threading import Lock

from server.trading import brvm_live

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
BRVM_DATA_FILE = DATA_DIR / "brvm_stocks.json"

_lock = Lock()


class BRVMEngine:
    _instance = None
    _instance_lock = Lock()

    def __init__(self):
        self.data = self._load_data()

    @classmethod
    def get_instance(cls) -> "BRVMEngine":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Charge la cote : marché réel d'abord, fichier de référence en secours.

        Le fichier data/brvm_stocks.json ne couvre que 12 des 47 valeurs et ses
        cours ont plusieurs mois de retard. Il ne sert donc que de filet quand
        aucune source n'est joignable, et l'instantané est alors explicitement
        marqué `is_live: False` pour que rien ne le présente comme du marché.
        """
        try:
            snapshot = brvm_live.get_snapshot(force=force_refresh)
            if snapshot.get("stocks"):
                return snapshot
        except Exception as e:
            print(f"[BRVMEngine] Données live indisponibles ({e}) — repli sur le fichier de référence.")

        with _lock:
            if BRVM_DATA_FILE.exists():
                try:
                    fallback = json.loads(BRVM_DATA_FILE.read_text(encoding="utf-8"))
                    fallback["is_live"] = False
                    fallback["stale"] = True
                    fallback["stale_reason"] = (
                        "Aucune source de marché joignable. Cours de référence figés au "
                        f"{fallback.get('updated_at', 'inconnu')}, sur 12 valeurs seulement."
                    )
                    return fallback
                except Exception as e:
                    print(f"[BRVMEngine] Erreur chargement JSON: {e}")
            return {"stocks": [], "index": {}, "is_live": False}

    def refresh(self, force: bool = True):
        self.data = self._load_data(force_refresh=force)
        return self.data

    def _provenance(self) -> Dict[str, Any]:
        """Origine et fraîcheur des données, à joindre à toute sortie du moteur.

        Sans ça, rien ne distingue un cours relevé il y a deux minutes d'un cours
        de référence vieux de plusieurs mois.
        """
        return {
            "is_live": self.data.get("is_live", False),
            "stale": self.data.get("stale", True),
            "market_timestamp": self.data.get("market_timestamp"),
            "session_status": self.data.get("session_status"),
            "delayed_15min": self.data.get("delayed_15min", False),
            "age_seconds": self.data.get("age_seconds"),
            "notice": self.data.get("notice") or self.data.get("stale_reason"),
        }

    def _calculate_orion_score(self, stock: Dict[str, Any], profile: str = "balanced") -> float:
        """
        Calcule le Orion Score BRVM (0-100) en croisant analyse fondamentale et technique.
        """
        # Les données de marché laissent ces champs à None quand la source ne
        # les publie pas (PER, ROE et marge nette ne sont publiés nulle part) :
        # `.get(clé, défaut)` renverrait None, pas le défaut, et la comparaison
        # `per <= 0` lèverait un TypeError. D'où la coercion explicite.
        def _val(key: str, default: float) -> float:
            raw = stock.get(key)
            return default if raw is None else float(raw)

        div_yield = _val("dividend_yield_pct", 0.0)
        per = _val("per", 15.0)
        roe = _val("roe_pct", 10.0)
        net_margin = _val("net_margin_pct", 10.0)
        trend = stock.get("tech_trend") or "NEUTRAL"
        rsi = _val("rsi", 50.0)

        # 1. Score Dividende (0-30)
        # Un rendement > 8% sur la BRVM est excellent
        div_score = min(30.0, (div_yield / 10.0) * 25.0)

        # 2. Score Valorisation PER (0-25)
        # PER < 8 est une opportunité de valeur sur la BRVM
        if per <= 0:
            per_score = 5.0
        elif per < 7.0:
            per_score = 25.0
        elif per < 10.0:
            per_score = 20.0
        elif per < 14.0:
            per_score = 14.0
        else:
            per_score = max(5.0, 25.0 - (per - 14.0) * 1.5)

        # 3. Score Rentabilité (ROE + Marge) (0-25)
        roe_score = min(15.0, (roe / 25.0) * 15.0)
        margin_score = min(10.0, (net_margin / 30.0) * 10.0)
        profitability_score = roe_score + margin_score

        # 4. Score Technique & Momentum (0-20)
        tech_score = 10.0
        if trend == "BULLISH":
            tech_score += 7.0
        elif trend == "BEARISH":
            tech_score -= 5.0

        if 40.0 <= rsi <= 65.0:
            tech_score += 3.0
        elif rsi > 70.0:  # Surachat
            tech_score -= 2.0

        # Pondération selon le profil d'investissement
        if profile == "dividend":
            total = (div_score * 1.6) + (per_score * 0.9) + (profitability_score * 0.7) + (tech_score * 0.5)
        elif profile == "growth":
            total = (profitability_score * 1.5) + (tech_score * 1.2) + (per_score * 0.8) + (div_score * 0.5)
        elif profile == "value":
            total = (per_score * 1.6) + (div_score * 1.0) + (profitability_score * 0.9) + (tech_score * 0.5)
        else:  # balanced
            total = (div_score * 1.1) + (per_score * 1.0) + (profitability_score * 1.0) + (tech_score * 0.9)

        return round(min(99.9, max(10.0, total)), 1)

    def get_market_overview(self) -> Dict[str, Any]:
        stocks = self.data.get("stocks", [])
        index = self.data.get("index", {})

        top_yielders = sorted(
            stocks, key=lambda s: s.get("dividend_yield_pct") or 0.0, reverse=True
        )[:5]
        top_scores = sorted(
            stocks, key=lambda s: self._calculate_orion_score(s, "balanced"), reverse=True
        )[:5]

        sectors = {}
        for s in stocks:
            sec = s.get("sector", "Autre")
            sectors[sec] = sectors.get(sec, 0) + 1

        return {
            "success": bool(stocks),
            "market": self.data.get("market"),
            "currency": self.data.get("currency", "XOF"),
            "updated_at": self.data.get("updated_at"),
            "data_provenance": self._provenance(),
            "index": index,
            "all_indices": self.data.get("indices", {}),
            "total_listed_stocks": len(stocks),
            "sectors_count": sectors,
            "top_dividend_yielders": [
                {
                    "symbol": s["symbol"],
                    "name": s["name"],
                    "price_xof": s["price_xof"],
                    "dividend_yield_pct": s["dividend_yield_pct"],
                    "dividend_per_share_xof": s.get("dividend_per_share_xof")
                } for s in top_yielders
            ],
            "top_orion_picks": [
                {
                    "symbol": s["symbol"],
                    "name": s["name"],
                    "price_xof": s["price_xof"],
                    "orion_score": self._calculate_orion_score(s, "balanced"),
                    "tech_trend": s.get("tech_trend")
                } for s in top_scores
            ]
        }

    def _load_price_history(self, stock: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Séances quotidiennes réelles d'une valeur, mises en cache sur l'instantané.

        Une requête réseau par valeur : on la garde sur le dict de la valeur pour
        qu'une analyse suivie d'une prédiction ne la refasse pas.
        """
        cached = stock.get("price_history")
        if cached:
            return cached

        slug = stock.get("sika_slug")
        if not slug:
            return []
        try:
            candles = brvm_live.fetch_sika_history(slug)
        except Exception as e:
            print(f"[BRVMEngine] Historique {stock.get('symbol')} indisponible : {e}")
            return []

        stock["price_history"] = candles
        return candles

    def run_kronos_forecast_for_stock(self, symbol: str, pred_len: int = 12) -> Dict[str, Any]:
        """
        Exécute l'inférence du modèle neuronal Kronos PyTorch (NeoQuasar/Kronos-mini)
        sur les chandeliers K-lines d'une action BRVM pour prédire la trajectoire du cours.
        """
        symbol_upper = symbol.strip().upper()
        stocks = self.data.get("stocks", [])
        stock = next((s for s in stocks if s.get("symbol").upper() == symbol_upper), None)
        if not stock:
            return {"success": False, "error": f"Symbole '{symbol}' non trouvé dans la côte BRVM."}

        price = float(stock.get("price_xof") or 0) or None
        if not price:
            return {"success": False, "symbol": symbol_upper,
                    "error": "Cours indisponible : prédiction impossible."}

        # Vraies séances quotidiennes. Sans historique réel, il n'y a pas de
        # prédiction possible : la version précédente reconstruisait 40 bougies
        # par interpolation entre la MM50 et le cours du jour, ce qui faisait de
        # la « prévision neuronale » une simple fonction de la tendance affichée.
        candles = self._load_price_history(stock)
        if len(candles) < 20:
            return {
                "success": False,
                "symbol": stock["symbol"],
                "error": (f"Historique insuffisant ({len(candles)} séances) pour une "
                          f"inférence Kronos. Minimum requis : 20 séances réelles."),
                "data_provenance": self._provenance(),
            }

        closes = [c["c"] for c in candles]
        highs = [c["h"] for c in candles]
        lows = [c["l"] for c in candles]
        true_ranges = [h - l for h, l in zip(highs, lows)]
        atr = sum(true_ranges[-14:]) / min(14, len(true_ranges))

        market_data = {
            "symbol": stock["symbol"],
            "bid": price,
            "ask": price * 1.002,
            "spread": 2,
            "timeframes": {
                "D1": {
                    "candles": candles,
                    "atr": atr,
                    "swing_high": max(highs[-60:]),
                    "swing_low": min(lows[-60:]),
                }
            }
        }

        try:
            from server.trading.kronos_engine import get_kronos_engine
            kronos = get_kronos_engine()
            res = kronos.predict_market_data(market_data, pred_len=pred_len)

            if not res.get("success"):
                return {
                    "success": False,
                    "symbol": stock["symbol"],
                    "error": res.get("error", "Inférence Kronos en échec."),
                }

            # Le moteur renvoie `predicted_close` : lire `pred_close` retombait
            # systématiquement sur le cours actuel, donc une variation de 0,00 %
            # à chaque appel — la prédiction était silencieusement jetée.
            pred_close = float(res["predicted_close"])
            change_pct = round(((pred_close - price) / price) * 100, 2)
            k_trend = "BULLISH" if change_pct > 0.5 else ("BEARISH" if change_pct < -0.5 else "NEUTRAL")
            # `confidence` est une fraction 0-1 côté moteur ; le seuil de
            # recommandation ci-dessous raisonne en pourcentage.
            conf = round(float(res.get("confidence", 0.0)) * 100, 1)

            return {
                "success": True,
                "symbol": stock["symbol"],
                "name": stock["name"],
                "kronos_model": kronos.model_name,
                "current_price_xof": price,
                "kronos_predicted_target_xof": round(pred_close, 2),
                "kronos_predicted_change_pct": change_pct,
                "kronos_trend_forecast": k_trend,
                "kronos_confidence_score": conf,
                "kronos_recommendation": "ACCUMULER (Haute Confluence Neuronal)" if change_pct > 1.5 and conf >= 75 else ("ALLÉGER" if change_pct < -1.5 else "CONSERVER"),
                "predicted_kline_samples": res.get("predicted_candles", [])[:5],
                "history_sessions_used": len(candles),
                "history_range": f"{candles[0]['date']} → {candles[-1]['date']}",
                "history_source": "sikafinance.com — séances quotidiennes réelles",
                "data_provenance": self._provenance(),
            }
        except Exception as e:
            return {
                "success": False,
                "symbol": stock["symbol"],
                "error": f"Erreur inférence Kronos : {e}"
            }

    def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        symbol_upper = symbol.strip().upper()
        stocks = self.data.get("stocks", [])

        stock = next((s for s in stocks if s.get("symbol", "").upper() == symbol_upper), None)
        if not stock:
            listed = ", ".join(sorted(s.get("symbol", "") for s in stocks)[:15])
            return {
                "success": False,
                "error": f"Symbole '{symbol}' non trouvé dans la cote BRVM.",
                "hint": f"{len(stocks)} valeurs cotées, dont : {listed}...",
            }

        # RSI, bêta et extrêmes 52 semaines demandent une requête par valeur :
        # on ne les récupère qu'ici, au moment où on analyse réellement le titre.
        if self.data.get("is_live") and not stock.get("detail_enriched"):
            try:
                brvm_live.enrich_stock(self.data, symbol_upper)
            except Exception as e:
                print(f"[BRVMEngine] Enrichissement {symbol_upper} indisponible : {e}")

        score_balanced = self._calculate_orion_score(stock, "balanced")
        score_div = self._calculate_orion_score(stock, "dividend")
        score_val = self._calculate_orion_score(stock, "value")

        # Obtenir la prédiction prédictive Kronos
        kronos_res = self.run_kronos_forecast_for_stock(symbol, pred_len=12)

        # Recommendation logic
        if score_balanced >= 82.0:
            recommendation = "ACHAT FORT (Strong Buy)"
            verdict = "Action sous-évaluée à très fort rendement et excellente qualité fondamentale."
        elif score_balanced >= 72.0:
            recommendation = "ACHAT (Buy)"
            verdict = "Solide opportunité d'investissement avec un profil rendement/risque attractif."
        elif score_balanced >= 60.0:
            recommendation = "CONSERVER (Hold)"
            verdict = "Valorisation correcte. À maintenir en portefeuille pour le flux de dividendes."
        else:
            recommendation = "NEUTRE / ALERTE (Watchlist)"
            verdict = "Attendre un repli de cours ou une meilleure zone de support d'achat."

        return {
            "success": True,
            "symbol": stock["symbol"],
            "name": stock["name"],
            "sector": stock["sector"],
            "country": stock["country"],
            "price_xof": stock["price_xof"],
            "change_pct": stock.get("change_pct", 0.0),
            "currency": "XOF",
            "orion_score": score_balanced,
            "orion_scores_by_profile": {
                "balanced": score_balanced,
                "dividend": score_div,
                "value": score_val
            },
            "recommendation": recommendation,
            "verdict": verdict,
            "kronos_neural_forecast": {
                "model": kronos_res.get("kronos_model", "Kronos PyTorch Engine"),
                "trend_forecast": kronos_res.get("kronos_trend_forecast", "BULLISH"),
                "confidence_score_pct": kronos_res.get("kronos_confidence_score", 85.0),
                "predicted_target_xof": kronos_res.get("kronos_predicted_target_xof", stock["price_xof"]),
                "predicted_change_pct": kronos_res.get("kronos_predicted_change_pct", 0.0),
                "kronos_recommendation": kronos_res.get("kronos_recommendation", "CONSERVER")
            },
            "fundamental_analysis": {
                "per": stock.get("per"),
                "per_evaluation": self._evaluate_per(stock.get("per")),
                "dividend_yield_pct": stock.get("dividend_yield_pct"),
                "dividend_per_share_xof": stock.get("dividend_per_share_xof"),
                "dividend_year": stock.get("dividend_year"),
                "roe_pct": stock.get("roe_pct"),
                "net_margin_pct": stock.get("net_margin_pct"),
                "market_cap_xof": stock.get("market_cap_xof"),
                "shares_outstanding": stock.get("shares_outstanding"),
                "ratios_source": stock.get("fundamentals_source", "reference_statique"),
                "ratios_warning": (
                    "PER, ROE et marge nette ne sont publiés par aucune source de cote : "
                    "ce sont des valeurs de référence, pas des données de marché."
                ),
            },
            "technical_analysis": {
                "trend": stock.get("tech_trend"),
                "trend_source": "dérivé de la position dans le range 52 semaines",
                "rsi": stock.get("rsi"),
                "rsi_status": self._evaluate_rsi(stock.get("rsi")),
                "beta_1y": stock.get("beta"),
                "52w_high_xof": stock.get("52w_high_xof"),
                "52w_low_xof": stock.get("52w_low_xof"),
                "open_xof": stock.get("open_xof"),
                "high_xof": stock.get("high_xof"),
                "low_xof": stock.get("low_xof"),
                "previous_close_xof": stock.get("previous_close_xof"),
                "volume": stock.get("volume"),
                "volume_xof": stock.get("volume_xof"),
            },
            "data_provenance": self._provenance(),
            "description": stock.get("description", "")
        }

    @staticmethod
    def _evaluate_per(per: Optional[float]) -> str:
        if per is None:
            return "Non disponible (aucune source ne publie le PER de la BRVM)"
        if per < 8:
            return "Sous-évalué (< 8x)"
        return "Raisonnable" if per < 12 else "Élevé"

    @staticmethod
    def _evaluate_rsi(rsi: Optional[float]) -> str:
        if rsi is None:
            return "Non disponible"
        if rsi < 35:
            return "Survendu"
        return "Suracheté" if rsi > 70 else "Zone Neutre"

    def pick_stocks(self, profile: str = "balanced", sector: Optional[str] = None, top_n: int = 5) -> Dict[str, Any]:
        stocks = self.data.get("stocks", [])
        profile_clean = profile.lower()

        if sector:
            sector_clean = sector.lower()
            stocks = [s for s in stocks if sector_clean in s.get("sector", "").lower()]

        scored_stocks = []
        for s in stocks:
            score = self._calculate_orion_score(s, profile=profile_clean)
            scored_stocks.append((score, s))

        scored_stocks.sort(key=lambda item: item[0], reverse=True)
        top_picks = scored_stocks[:top_n]

        results = []
        for rank, (score, s) in enumerate(top_picks, start=1):
            price = s.get("price_xof")
            support = s.get("support_xof") or s.get("52w_low_xof")
            resistance = s.get("resistance_xof") or s.get("52w_high_xof")
            results.append({
                "rank": rank,
                "symbol": s["symbol"],
                "name": s["name"],
                "sector": s.get("sector"),
                "country": s.get("country"),
                "price_xof": price,
                "change_pct": s.get("change_pct"),
                "dividend_yield_pct": s.get("dividend_yield_pct"),
                "dividend_per_share_xof": s.get("dividend_per_share_xof"),
                "per": s.get("per"),
                "roe_pct": s.get("roe_pct"),
                "market_cap_xof": s.get("market_cap_xof"),
                "orion_score": score,
                "tech_trend": s.get("tech_trend"),
                "buying_zone_xof": f"{support} - {price}" if support and price else None,
                "target_price_xof": resistance if resistance else (round(price * 1.15) if price else None),
                "summary": s.get("description", "")
            })

        return {
            "success": True,
            "profile": profile_clean,
            "sector_filter": sector or "Tous les secteurs",
            "total_matches": len(scored_stocks),
            "picks_count": len(results),
            "picks": results,
            "data_provenance": self._provenance(),
        }

    def build_income_portfolio(self, target_monthly_income_xof: float = 150000.0) -> Dict[str, Any]:
        """
        Construit un portefeuille BRVM optimisé spécifiquement pour générer un revenu cible mensuel
        (ex: 150.000 FCFA / mois = 1.800.000 FCFA / an) en combinant dividendes et croissance.
        """
        target_monthly_income_xof = float(target_monthly_income_xof)
        target_yearly_income_xof = target_monthly_income_xof * 12.0

        stocks = self.data.get("stocks", [])

        # Un revenu se planifie sur le dividende récurrent, jamais sur le dernier
        # versement : une distribution exceptionnelle (FILTISAC a versé 13x son
        # dividende habituel en 2024) ferait dimensionner le portefeuille sur un
        # flux qui ne se reproduira pas.
        income_candidates = []
        adjusted = []
        for s in stocks:
            recurring = s.get("dividend_recurring_xof") or s.get("dividend_per_share_xof")
            price = s.get("price_xof")
            if not recurring or not price:
                continue
            recurring_yield = recurring / price * 100.0
            if s.get("dividend_is_exceptional"):
                adjusted.append({
                    "symbol": s["symbol"], "name": s["name"],
                    "last_dividend_xof": s.get("dividend_per_share_xof"),
                    "planned_on_xof": recurring,
                    "raison": s.get("dividend_note"),
                })
            if recurring_yield >= 4.0:
                income_candidates.append((s, recurring, round(recurring_yield, 2)))

        income_candidates.sort(
            key=lambda item: self._calculate_orion_score(item[0], "dividend"), reverse=True
        )
        selected = income_candidates[:5]
        if not selected:
            return {
                "success": False,
                "error": ("Aucune valeur de la cote n'offre un rendement récurrent d'au "
                          "moins 4% aux cours actuels."),
                "data_provenance": self._provenance(),
            }

        # Allocation pondérée (ex: 30% Sonatel, 25% SGBCI, 20% Palmci, 15% Coris, 10% Total CI)
        weights = [0.30, 0.25, 0.20, 0.15, 0.10][:len(selected)]
        total_w = sum(weights)
        weights = [w / total_w for w in weights]

        portfolio_items = []
        total_investment_xof = 0.0
        total_annual_dividend_xof = 0.0

        for (stock, div_per_share, recurring_yield), weight in zip(selected, weights):
            target_stock_annual_div = target_yearly_income_xof * weight
            price = stock["price_xof"]

            shares_needed = int(target_stock_annual_div / div_per_share) + 1
            investment = shares_needed * price
            annual_div = shares_needed * div_per_share

            total_investment_xof += investment
            total_annual_dividend_xof += annual_div

            portfolio_items.append({
                "symbol": stock["symbol"],
                "name": stock["name"],
                "sector": stock.get("sector"),
                "country": stock.get("country"),
                "price_xof": price,
                "shares_to_buy": shares_needed,
                "capital_required_xof": round(investment, 2),
                "dividend_per_share_xof": div_per_share,
                "dividend_basis": ("norme des exercices antérieurs" if stock.get("dividend_is_exceptional")
                                   else "dernier dividende déclaré"),
                "dividend_warning": stock.get("dividend_note"),
                "dividend_history": stock.get("dividend_history"),
                "annual_dividend_expected_xof": round(annual_div, 2),
                "monthly_equivalent_xof": round(annual_div / 12.0, 2),
                "dividend_yield_pct": recurring_yield,
                "last_dividend_xof": stock.get("dividend_per_share_xof"),
                "weight_pct": round(weight * 100, 1),
                "orion_score": self._calculate_orion_score(stock, "dividend")
            })

        avg_yield = round((total_annual_dividend_xof / total_investment_xof) * 100, 2) if total_investment_xof > 0 else 0.0

        return {
            "success": True,
            "target_monthly_income_xof": target_monthly_income_xof,
            "target_yearly_income_xof": target_yearly_income_xof,
            "achieved_monthly_income_xof": round(total_annual_dividend_xof / 12.0, 2),
            "achieved_yearly_income_xof": round(total_annual_dividend_xof, 2),
            "total_capital_required_xof": round(total_investment_xof, 2),
            "portfolio_average_yield_pct": avg_yield,
            "allocation": portfolio_items,
            "exceptional_dividends_adjusted": adjusted,
            "payout_calendar": [
                {"period": "Mai - Juillet (Saison des dividendes BRVM)", "expected_payout_xof": round(total_annual_dividend_xof, 2)}
            ],
            "data_provenance": self._provenance(),
            "methodology": (
                "Dividendes calculés sur la médiane des exercices publiés, aux cours "
                "du jour. Les distributions exceptionnelles sont écartées. Un dividende "
                "passé ne garantit aucun versement futur."
            ),
            "advice": (
                f"Pour générer {target_monthly_income_xof:,.0f} FCFA par mois "
                f"({target_yearly_income_xof:,.0f} FCFA/an), ce portefeuille de "
                f"{len(portfolio_items)} valeurs demande environ "
                f"{total_investment_xof:,.0f} FCFA de capital, pour un rendement "
                f"récurrent moyen de {avg_yield}% aux cours actuels."
            ),
        }


def get_brvm_engine() -> BRVMEngine:
    return BRVMEngine.get_instance()
