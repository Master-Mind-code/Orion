"""
Orion Trading — Collecteur de données BRVM en temps réel.

Récupère la cote réelle de la Bourse Régionale des Valeurs Mobilières (UEMOA)
depuis les plateformes publiques, et produit un instantané au format attendu
par BRVMEngine.

Sources utilisées
─────────────────
  brvm.org (officiel)   cote complète des 47 valeurs, indices, capitalisations.
                        Cours différés de 15 minutes pendant la séance.
  sikafinance.com       OHLC intraday, historique des dividendes et rendements,
                        et par valeur : RSI, bêta 1 an, extrêmes 52 semaines.

Deux sources demandées ne sont pas exploitables côté serveur :
  richbourse.com        répond 403 à tout client non-navigateur (filtrage nginx).
  bstrade.bridge-securities.com
                        chaîne TLS incomplète (intermédiaire absent) : la
                        vérification du certificat échoue. C'est un portail de
                        courtage authentifié, pas une source de cote publique.

Ce que les sources couvrent — et ce qu'elles ne couvrent pas
───────────────────────────────────────────────────────────
Réel : cours, variation, volume, OHLC, capitalisation, titres en circulation,
       dividende, rendement, RSI, bêta, extrêmes 52 semaines, indices.
Absent : PER, ROE, marge nette. Aucune des sources ne les publie. Ils sont
       repris du fichier de référence data/brvm_stocks.json et chaque valeur
       porte alors `fundamentals_source = "reference_statique"`. Un consommateur
       ne doit jamais présenter ces trois ratios comme des données de marché.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
CACHE_FILE = DATA_DIR / "brvm_live_cache.json"
REFERENCE_FILE = DATA_DIR / "brvm_stocks.json"

# La BRVM diffuse ses cours avec 15 minutes de retard : rafraîchir plus vite
# ne rapporte rien et matraque les serveurs de la Bourse pour rien.
DEFAULT_MAX_AGE_SEC = 900

HTTP_TIMEOUT_SEC = 25
HTTP_RETRIES = 2

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

BRVM_QUOTES_URL = "https://www.brvm.org/fr/cours-actions/0"
BRVM_INDICES_URL = "https://www.brvm.org/fr/indices"
BRVM_CAPS_URL = "https://www.brvm.org/fr/capitalisations/0"
SIKA_QUOTES_URL = "https://www.sikafinance.com/marches/aaz"
SIKA_DIVIDENDS_URL = "https://www.sikafinance.com/marches/dividendes"
SIKA_STOCK_URL = "https://www.sikafinance.com/marches/cotation_{slug}"
SIKA_HISTORY_URL = "https://www.sikafinance.com/marches/historiques/{slug}"

# Pages sectorielles de brvm.org : le numéro est l'identifiant du secteur.
BRVM_SECTOR_PAGES = {
    194: "Consommation de Base",
    195: "Consommation Discrétionnaire",
    196: "Energie",
    197: "Industriels",
    198: "Services Financiers",
    199: "Services Publics",
    200: "Télécommunications",
}

# Suffixe pays des URL sikafinance (cotation_SNTS.sn) → pays de cotation.
_COUNTRY_BY_SUFFIX = {
    "ci": "Côte d'Ivoire",
    "sn": "Sénégal",
    "bf": "Burkina Faso",
    "bj": "Bénin",
    "tg": "Togo",
    "ml": "Mali",
    "ne": "Niger",
    "gw": "Guinée-Bissau",
}

_lock = Lock()
_memo: Dict[str, Any] = {"snapshot": None, "fetched_at": 0.0}


# ════════════════════════════════════════════════════════════════════════════
# Utilitaires de récupération et de parsing
# ════════════════════════════════════════════════════════════════════════════

class BRVMSourceError(RuntimeError):
    """Une source de cote n'a pas pu être lue."""


def _decode(payload: bytes) -> str:
    """Décode le corps d'une page en UTF-8.

    Les deux sites servent bien de l'UTF-8 conforme à ce qu'ils déclarent.
    Le repli cp1252 ne sert qu'au cas où l'un d'eux changerait d'avis : mieux
    vaut des accents approximatifs qu'une collecte qui tombe.
    """
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.decode("cp1252", errors="replace")


def _soup(url: str):
    """Télécharge une page et la parse."""
    import httpx
    from bs4 import BeautifulSoup

    last_exc: Optional[Exception] = None
    for attempt in range(HTTP_RETRIES + 1):
        try:
            resp = httpx.get(url, headers=_HEADERS, timeout=HTTP_TIMEOUT_SEC,
                             follow_redirects=True)
            resp.raise_for_status()
            return BeautifulSoup(_decode(resp.content), "lxml")
        except Exception as exc:  # réseau, HTTP, parsing
            last_exc = exc
            if attempt < HTTP_RETRIES:
                time.sleep(1.5 * (attempt + 1))
    raise BRVMSourceError(f"{url} : {type(last_exc).__name__} — {last_exc}")


def _num(raw: Any) -> Optional[float]:
    """Convertit un nombre au format francophone en float.

    Gère les espaces insécables des milliers et la virgule décimale :
    '36 000' → 36000.0, '1,23' → 1.23, '-6,98%' → -6.98, '' → None.
    """
    if raw is None:
        return None
    text = str(raw).replace("\xa0", " ").replace(" ", " ")
    text = text.replace("%", "").replace("FCFA", "").replace("XOF", "")
    text = text.replace(" ", "").replace(",", ".").strip()
    if not text or text in ("-", "--", "n/a", "N/A"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize(name: str) -> str:
    """Clé de rapprochement des libellés entre brvm.org et sikafinance.

    Les deux sites orthographient différemment (accents, apostrophes typographiques,
    espaces insécables) et sikafinance tronque ses libellés à 20 caractères dans
    le tableau des dividendes.
    """
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text).upper()
    return " ".join(text.split())


def _cells(row) -> List[str]:
    return [c.get_text(strip=True) for c in row.find_all(["th", "td"])]


def _biggest_table(soup, min_rows: int = 10):
    """Renvoie le tableau le plus fourni de la page.

    brvm.org place la cote après trois tableaux d'entête (top 5, flop 5,
    activité du marché) ; cibler un index fixe casserait à la moindre
    réorganisation de la page.
    """
    best, best_len = None, 0
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) > best_len:
            best, best_len = table, len(rows)
    if best is None or best_len < min_rows:
        raise BRVMSourceError(f"tableau principal introuvable (max {best_len} lignes)")
    return best


# ════════════════════════════════════════════════════════════════════════════
# Collecteurs par source
# ════════════════════════════════════════════════════════════════════════════

def fetch_brvm_quotes() -> Dict[str, Any]:
    """Cote officielle des actions : cours, variation, volume (brvm.org)."""
    soup = _soup(BRVM_QUOTES_URL)
    table = _biggest_table(soup, min_rows=20)

    quotes: Dict[str, Dict[str, Any]] = {}
    for row in table.find_all("tr")[1:]:
        cells = _cells(row)
        if len(cells) < 7 or not cells[0]:
            continue
        symbol = cells[0].strip().upper()
        quotes[symbol] = {
            "symbol": symbol,
            "name": " ".join(cells[1].split()),
            "volume": _num(cells[2]),
            "previous_close_xof": _num(cells[3]),
            "open_xof": _num(cells[4]),
            "price_xof": _num(cells[5]),
            "change_pct": _num(cells[6]),
        }

    if not quotes:
        raise BRVMSourceError("cote brvm.org vide")

    return {"quotes": quotes, "session": _parse_session_header(soup)}


def _parse_session_header(soup) -> Dict[str, Any]:
    """Extrait l'horodatage et l'état de séance affichés en tête de brvm.org."""
    text = soup.get_text(" ", strip=True)
    stamp = re.search(r"(\d{1,2}\s+\w+,?\s+\d{4})\s*-\s*(\d{1,2}:\d{2})", text)
    status = "OUVERTE" if re.search(r"S[ée]ance\s+Ouverte", text, re.I) else (
        "FERMÉE" if re.search(r"S[ée]ance\s+Ferm[ée]e", text, re.I) else "INCONNU")
    delayed = bool(re.search(r"Diff[ée]r[ée]e\s+de\s+(\d+)\s+minutes", text, re.I))
    return {
        "market_timestamp": f"{stamp.group(1)} {stamp.group(2)}" if stamp else None,
        "session_status": status,
        "delayed_15min": delayed,
    }


def fetch_brvm_indices() -> Dict[str, Any]:
    """Indices BRVM (Composite, 30, Prestige, Principal, sectoriels)."""
    soup = _soup(BRVM_INDICES_URL)

    indices: Dict[str, Dict[str, Any]] = {}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        header = " ".join(_cells(rows[0])).lower()
        if "fermeture" not in header:
            continue
        for row in rows[1:]:
            cells = _cells(row)
            if len(cells) < 4 or not cells[0]:
                continue
            # Le tiret cadratin de « BRVM – COMPOSITE » n'est pas le tiret
            # d'« BRVM - COMPOSITE » : on normalise pour avoir une clé stable.
            name = re.sub(r"\s*[-–—]\s*", " - ", " ".join(cells[0].split())).upper()
            indices[name] = {
                "name": name,
                "previous_close": _num(cells[1]),
                "value": _num(cells[2]),
                "change_pct": _num(cells[3]),
                "change_ytd_pct": _num(cells[4]) if len(cells) > 4 else None,
            }

    if not indices:
        raise BRVMSourceError("aucun indice lu sur brvm.org")
    return indices


def fetch_brvm_capitalisations() -> Dict[str, Dict[str, Any]]:
    """Capitalisation et nombre de titres par valeur (brvm.org)."""
    soup = _soup(BRVM_CAPS_URL)
    table = _biggest_table(soup, min_rows=20)

    caps: Dict[str, Dict[str, Any]] = {}
    for row in table.find_all("tr")[1:]:
        cells = _cells(row)
        if len(cells) < 6 or not cells[0]:
            continue
        caps[cells[0].strip().upper()] = {
            "shares_outstanding": _num(cells[2]),
            "market_cap_xof": _num(cells[5]),
            "market_cap_share_pct": _num(cells[6]) if len(cells) > 6 else None,
        }
    return caps


def fetch_brvm_sectors() -> Dict[str, str]:
    """Secteur d'activité de chaque valeur, via les pages sectorielles brvm.org.

    Une page par secteur : sept requêtes. Un secteur en échec ne doit pas faire
    tomber la collecte entière, on se contente de ce qui répond.
    """
    sectors: Dict[str, str] = {}
    for page_id, label in BRVM_SECTOR_PAGES.items():
        try:
            soup = _soup(f"https://www.brvm.org/fr/cours-actions/{page_id}")
            table = _biggest_table(soup, min_rows=2)
        except BRVMSourceError:
            continue
        for row in table.find_all("tr")[1:]:
            cells = _cells(row)
            if len(cells) >= 7 and cells[0]:
                sectors[cells[0].strip().upper()] = label
    return sectors


def fetch_sika_directory() -> Dict[str, Dict[str, Any]]:
    """Annuaire sikafinance : symbole → libellé complet, pays et OHLC du jour.

    C'est cette page qui donne la correspondance entre les libellés tronqués du
    tableau des dividendes et les symboles de la cote.
    """
    soup = _soup(SIKA_QUOTES_URL)
    table = soup.find("table", id="tblShare")
    if table is None:
        raise BRVMSourceError("tableau tblShare absent de sikafinance/aaz")

    directory: Dict[str, Dict[str, Any]] = {}
    for row in table.find_all("tr")[1:]:
        link = row.find("a", href=True)
        if not link:
            continue
        match = re.search(r"cotation_([A-Z0-9]+)\.([a-z]{2})", link["href"])
        if not match:
            continue
        symbol, suffix = match.group(1).upper(), match.group(2)
        cells = _cells(row)
        directory[symbol] = {
            "slug": f"{symbol}.{suffix}",
            "name": " ".join(link.get_text(strip=True).split()),
            "country": _COUNTRY_BY_SUFFIX.get(suffix, "UEMOA"),
            "open_xof": _num(cells[1]) if len(cells) > 1 else None,
            "high_xof": _num(cells[2]) if len(cells) > 2 else None,
            "low_xof": _num(cells[3]) if len(cells) > 3 else None,
            "volume_xof": _num(cells[5]) if len(cells) > 5 else None,
        }
    return directory


def fetch_sika_dividends() -> Dict[str, Dict[str, Any]]:
    """Historique des dividendes par valeur, indexé sur le libellé normalisé.

    On garde tous les exercices publiés, pas seulement le dernier : une
    distribution exceptionnelle ne se distingue d'un dividende ordinaire qu'en
    la comparant aux années précédentes. FILTISAC a par exemple versé 1 727 FCFA
    en 2024 (rendement annoncé 93,83 %) contre 130 FCFA en 2023 — planifier un
    revenu sur ce chiffre serait une faute.
    """
    soup = _soup(SIKA_DIVIDENDS_URL)
    table = soup.find("table", id="tblDiv2")
    if table is None:
        raise BRVMSourceError("tableau tblDiv2 absent de sikafinance/dividendes")

    rows = table.find_all("tr")
    header = _cells(rows[0])
    # En-têtes de la forme « Div. 2024 » / « Rend. 2024 »
    years: List[tuple] = []
    for idx, label in enumerate(header):
        year = re.search(r"(20\d{2})", label)
        if year and label.lower().startswith("div"):
            years.append((int(year.group(1)), idx))
    years.sort(reverse=True)

    dividends: Dict[str, Dict[str, Any]] = {}
    for row in rows[1:]:
        cells = _cells(row)
        if len(cells) < 2 or not cells[0]:
            continue

        history: Dict[int, float] = {}
        for year, idx in years:
            amount = _num(cells[idx]) if idx < len(cells) else None
            if amount:
                history[year] = amount
        if not history:
            continue

        latest_year = max(history)
        dividends[_normalize(cells[0])] = {
            "dividend_per_share_xof": history[latest_year],
            "dividend_year": latest_year,
            "dividend_history": dict(sorted(history.items(), reverse=True)),
            **_assess_dividend(history),
        }
    return dividends


def _median(values: List[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _assess_dividend(history: Dict[int, float]) -> Dict[str, Any]:
    """Distingue le dividende récurrent d'une distribution exceptionnelle.

    Le dernier versement est comparé à la médiane des exercices *antérieurs*,
    pas à celle de l'ensemble : FILTISAC n'a que deux exercices publiés
    (130 FCFA en 2023, 1 727 en 2024) et la médiane globale, tirée vers le haut
    par le versement exceptionnel lui-même, ne le détecterait pas.

    Le dividende récurrent retenu est le dernier versement en temps normal — il
    reflète la politique de distribution actuelle — et la norme antérieure
    lorsque ce dernier versement est jugé exceptionnel.
    """
    latest_year = max(history)
    latest = history[latest_year]
    prior = [amount for year, amount in history.items() if year != latest_year]

    if not prior:
        return {
            "dividend_recurring_xof": latest,
            "dividend_years_published": 1,
            "dividend_is_exceptional": False,
            "dividend_note": ("Un seul exercice publié : impossible de vérifier si ce "
                              "dividende est récurrent."),
        }

    prior_median = _median(prior)
    exceptional = prior_median > 0 and latest > prior_median * 2.5
    recurring = prior_median if exceptional else latest

    return {
        "dividend_recurring_xof": round(recurring, 2),
        "dividend_years_published": len(history),
        "dividend_is_exceptional": exceptional,
        "dividend_note": (
            f"Dernier versement ({latest:,.0f} FCFA) sans commune mesure avec les "
            f"exercices antérieurs (médiane {prior_median:,.0f} FCFA) : distribution "
            f"exceptionnelle, à ne pas extrapoler. Planification basée sur "
            f"{prior_median:,.0f} FCFA."
        ) if exceptional else None,
    }


def fetch_sika_history(slug: str, limit: int = 60) -> List[Dict[str, Any]]:
    """Historique quotidien OHLCV réel d'une valeur, de la plus ancienne séance
    à la plus récente.

    Le site publie une soixantaine de séances par valeur. C'est ce qui permet
    d'alimenter Kronos avec de vraies K-lines plutôt qu'avec une trajectoire
    reconstruite.
    """
    soup = _soup(SIKA_HISTORY_URL.format(slug=slug))
    table = soup.find("table", id="tblhistos")
    if table is None:
        raise BRVMSourceError(f"historique indisponible pour {slug}")

    import datetime as _dt

    candles: List[Dict[str, Any]] = []
    for row in table.find_all("tr")[1:]:
        cells = _cells(row)
        if len(cells) < 7:
            continue
        try:
            day = _dt.datetime.strptime(cells[0].strip(), "%d/%m/%Y")
        except ValueError:
            continue
        close, low, high = _num(cells[1]), _num(cells[2]), _num(cells[3])
        open_, volume = _num(cells[4]), _num(cells[5])
        if not close:
            continue
        candles.append({
            "t": int(day.timestamp()),
            "date": day.strftime("%Y-%m-%d"),
            "o": open_ or close,
            "h": high or close,
            "l": low or close,
            "c": close,
            "v": volume or 0,
        })

    # Le site liste de la séance la plus récente à la plus ancienne ; un modèle
    # de série temporelle attend l'ordre chronologique.
    candles.sort(key=lambda c: c["t"])
    return candles[-limit:] if limit else candles


def fetch_sika_stock_detail(slug: str) -> Dict[str, Any]:
    """Indicateurs par valeur : RSI, bêta 1 an et extrêmes 52 semaines.

    Une requête par valeur : réservé à l'analyse d'un titre précis, jamais
    appelé pour les 47 valeurs d'un coup.
    """
    soup = _soup(SIKA_STOCK_URL.format(slug=slug))
    detail: Dict[str, Any] = {}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = _cells(row)
            if len(cells) == 2:
                label = _normalize(cells[0])
                if label.startswith("BETA"):
                    detail["beta"] = _num(cells[1])
                elif label == "RSI":
                    detail["rsi"] = _num(cells[1])
                elif label.startswith("CLOTURE VEILLE"):
                    detail["previous_close_xof"] = _num(cells[1])
            # Ligne « 1 an | plus haut | plus bas | variation »
            elif len(cells) == 4 and _normalize(cells[0]) == "1 AN":
                detail["52w_high_xof"] = _num(cells[1])
                detail["52w_low_xof"] = _num(cells[2])
                detail["change_1y_pct"] = _num(cells[3])
    return detail


# ════════════════════════════════════════════════════════════════════════════
# Assemblage de l'instantané de marché
# ════════════════════════════════════════════════════════════════════════════

def _load_reference() -> Dict[str, Dict[str, Any]]:
    """Ratios fondamentaux de référence, absents des sources de cote."""
    if not REFERENCE_FILE.exists():
        return {}
    try:
        raw = json.loads(REFERENCE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {s["symbol"].upper(): s for s in raw.get("stocks", []) if s.get("symbol")}


def _match_dividend(name: str, dividends: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Rapproche un libellé de cote d'une ligne du tableau des dividendes.

    sikafinance tronque ses libellés à une vingtaine de caractères
    (« AFRICA GLOBAL LOGIST » pour « AFRICA GLOBAL LOGISTICS ») : l'égalité
    stricte échouerait, on rapproche donc par préfixe.
    """
    key = _normalize(name)
    if key in dividends:
        return dividends[key]
    for candidate, payload in dividends.items():
        if len(candidate) >= 8 and (key.startswith(candidate) or candidate.startswith(key)):
            return payload
    return None


def _derive_trend(price: Optional[float], low: Optional[float],
                  high: Optional[float], change_pct: Optional[float]) -> str:
    """Tendance technique déduite de la position dans le range 52 semaines.

    Valeur dérivée, pas une donnée publiée : sans extrêmes 52 semaines on
    reste NEUTRAL plutôt que de conclure sur une seule séance.
    """
    if price and low and high and high > low:
        position = (price - low) / (high - low)
        if position >= 0.66:
            return "BULLISH"
        if position <= 0.33:
            return "BEARISH"
        return "NEUTRAL"
    if change_pct is not None and abs(change_pct) >= 2.0:
        return "BULLISH" if change_pct > 0 else "BEARISH"
    return "NEUTRAL"


def build_snapshot() -> Dict[str, Any]:
    """Interroge les sources et assemble un instantané au format BRVMEngine.

    La cote brvm.org est la seule source indispensable : sans elle il n'y a pas
    d'instantané. Les autres sont des enrichissements, et chacune peut échouer
    sans invalider le reste — l'état de chaque source est reporté dans
    `sources` pour que l'appelant sache ce qu'il a réellement obtenu.
    """
    sources: Dict[str, Any] = {}

    def _try(label: str, fn, default):
        try:
            value = fn()
            sources[label] = {"status": "ok"}
            return value
        except Exception as exc:
            sources[label] = {"status": "echec", "error": f"{type(exc).__name__}: {exc}"[:200]}
            return default

    # Source obligatoire.
    try:
        quotes_payload = fetch_brvm_quotes()
        sources["brvm_cours"] = {"status": "ok"}
    except Exception as exc:
        raise BRVMSourceError(
            f"cote brvm.org indisponible, aucun instantané possible : {exc}"
        ) from exc

    quotes = quotes_payload["quotes"]
    session = quotes_payload["session"]

    indices = _try("brvm_indices", fetch_brvm_indices, {})
    caps = _try("brvm_capitalisations", fetch_brvm_capitalisations, {})
    sectors = _try("brvm_secteurs", fetch_brvm_sectors, {})
    directory = _try("sikafinance_annuaire", fetch_sika_directory, {})
    dividends = _try("sikafinance_dividendes", fetch_sika_dividends, {})

    reference = _load_reference()

    stocks: List[Dict[str, Any]] = []
    for symbol, quote in sorted(quotes.items()):
        price = quote["price_xof"]
        sika = directory.get(symbol, {})
        cap = caps.get(symbol, {})
        ref = reference.get(symbol, {})
        div = _match_dividend(sika.get("name") or quote["name"], dividends) or {}

        dividend_per_share = div.get("dividend_per_share_xof")
        dividend_recurring = div.get("dividend_recurring_xof")
        # Les rendements sont recalculés sur le cours du jour : celui publié par
        # sikafinance est figé sur le cours de son propre relevé.
        dividend_yield = (round(dividend_per_share / price * 100, 2)
                          if dividend_per_share and price else None)
        recurring_yield = (round(dividend_recurring / price * 100, 2)
                           if dividend_recurring and price else None)

        stock: Dict[str, Any] = {
            "symbol": symbol,
            "name": sika.get("name") or quote["name"],
            "sector": sectors.get(symbol) or ref.get("sector") or "Non classé",
            "country": sika.get("country") or ref.get("country") or "UEMOA",

            # ── Cote réelle ──
            "price_xof": price,
            "change_pct": quote["change_pct"],
            "previous_close_xof": quote["previous_close_xof"],
            "open_xof": quote["open_xof"] or sika.get("open_xof"),
            "high_xof": sika.get("high_xof"),
            "low_xof": sika.get("low_xof"),
            "volume": quote["volume"],
            "volume_xof": sika.get("volume_xof"),
            "market_cap_xof": cap.get("market_cap_xof") or ref.get("market_cap_xof"),
            "shares_outstanding": cap.get("shares_outstanding"),

            # ── Dividende réel, rendements recalculés sur le cours du jour ──
            "dividend_per_share_xof": dividend_per_share,
            "dividend_yield_pct": dividend_yield,
            "dividend_year": div.get("dividend_year"),
            "dividend_history": div.get("dividend_history"),
            "dividend_recurring_xof": dividend_recurring,
            "dividend_recurring_yield_pct": recurring_yield,
            "dividend_years_published": div.get("dividend_years_published"),
            "dividend_is_exceptional": div.get("dividend_is_exceptional", False),
            "dividend_note": div.get("dividend_note"),

            # ── Ratios non publiés par les sources : référence statique ──
            "per": ref.get("per"),
            "roe_pct": ref.get("roe_pct"),
            "net_margin_pct": ref.get("net_margin_pct"),
            "description": ref.get("description", ""),

            # ── Technique : enrichi à la demande par enrich_stock() ──
            "rsi": None,
            "beta": None,
            "52w_high_xof": None,
            "52w_low_xof": None,
            "tech_trend": _derive_trend(price, None, None, quote["change_pct"]),

            "sika_slug": sika.get("slug"),
            "price_source": "brvm.org",
            "fundamentals_source": "reference_statique" if ref else "indisponible",
            "detail_enriched": False,
        }
        stocks.append(stock)

    composite = indices.get("BRVM - COMPOSITE", {})

    return {
        "market": "BRVM (Bourse Régionale des Valeurs Mobilières)",
        "zone": "UEMOA",
        "currency": "XOF",
        "is_live": True,
        "fetched_at": time.time(),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "market_timestamp": session.get("market_timestamp"),
        "session_status": session.get("session_status"),
        "delayed_15min": session.get("delayed_15min"),
        "index": {
            "name": "BRVM Composite",
            "value": composite.get("value"),
            "change_pct": composite.get("change_pct"),
            "change_ytd_pct": composite.get("change_ytd_pct"),
        },
        "indices": indices,
        "stocks": stocks,
        "sources": sources,
        "notice": (
            "Cours différés de 15 minutes (brvm.org). PER, ROE et marge nette ne "
            "sont publiés par aucune source : ils proviennent du fichier de "
            "référence et ne sont pas des données de marché."
        ),
    }


def enrich_stock(snapshot: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """Complète une valeur avec RSI, bêta et extrêmes 52 semaines.

    Une requête réseau supplémentaire, pour une seule valeur : appelé au moment
    d'analyser un titre, pas à la construction de l'instantané.
    """
    symbol = symbol.strip().upper()
    stock = next((s for s in snapshot.get("stocks", []) if s["symbol"] == symbol), None)
    if stock is None:
        return {}
    if stock.get("detail_enriched"):
        return stock
    slug = stock.get("sika_slug")
    if not slug:
        return stock

    try:
        detail = fetch_sika_stock_detail(slug)
    except BRVMSourceError:
        return stock

    stock.update({k: v for k, v in detail.items() if v is not None})
    stock["tech_trend"] = _derive_trend(
        stock.get("price_xof"), stock.get("52w_low_xof"),
        stock.get("52w_high_xof"), stock.get("change_pct"),
    )
    stock["detail_enriched"] = True
    return stock


# ════════════════════════════════════════════════════════════════════════════
# Cache
# ════════════════════════════════════════════════════════════════════════════

def _read_cache() -> Optional[Dict[str, Any]]:
    if not CACHE_FILE.exists():
        return None
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_cache(snapshot: Dict[str, Any]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        print(f"[brvm_live] cache non écrit : {exc}")


def age_seconds(snapshot: Optional[Dict[str, Any]]) -> float:
    if not snapshot or not snapshot.get("fetched_at"):
        return float("inf")
    return max(0.0, time.time() - float(snapshot["fetched_at"]))


def get_snapshot(max_age_sec: int = DEFAULT_MAX_AGE_SEC,
                 force: bool = False) -> Dict[str, Any]:
    """Instantané de marché, depuis le cache s'il est encore frais.

    En cas d'échec réseau, on rend le dernier instantané connu marqué `stale`
    plutôt que rien : une donnée datée et signalée comme telle vaut mieux
    qu'une erreur, tant que l'appelant sait qu'elle est datée.
    """
    with _lock:
        cached = _memo["snapshot"] or _read_cache()

        if not force and cached and age_seconds(cached) <= max_age_sec:
            cached["stale"] = False
            _memo["snapshot"] = cached
            return cached

        try:
            snapshot = build_snapshot()
        except BRVMSourceError as exc:
            if cached:
                cached["stale"] = True
                cached["stale_reason"] = str(exc)[:200]
                cached["age_seconds"] = round(age_seconds(cached))
                _memo["snapshot"] = cached
                return cached
            raise

        snapshot["stale"] = False
        snapshot["age_seconds"] = 0
        _memo["snapshot"] = snapshot
        _write_cache(snapshot)
        return snapshot


def source_health() -> Dict[str, Any]:
    """Teste chaque source et rapporte son état, sans rien mettre en cache."""
    checks = {
        "brvm.org / cours-actions": fetch_brvm_quotes,
        "brvm.org / indices": fetch_brvm_indices,
        "brvm.org / capitalisations": fetch_brvm_capitalisations,
        "sikafinance / cotations": fetch_sika_directory,
        "sikafinance / dividendes": fetch_sika_dividends,
    }
    report: Dict[str, Any] = {}
    for label, fn in checks.items():
        started = time.time()
        try:
            payload = fn()
            count = len(payload.get("quotes", payload)) if isinstance(payload, dict) else 0
            report[label] = {
                "status": "ok",
                "entries": count,
                "latency_ms": round((time.time() - started) * 1000),
            }
        except Exception as exc:
            report[label] = {"status": "echec", "error": f"{type(exc).__name__}: {exc}"[:200]}

    report["richbourse.com"] = {
        "status": "inexploitable",
        "error": "HTTP 403 — le site refuse les clients non-navigateur.",
    }
    report["bstrade.bridge-securities.com"] = {
        "status": "inexploitable",
        "error": ("Chaîne TLS incomplète (certificat intermédiaire absent) : la "
                  "vérification échoue. Portail de courtage authentifié, pas une "
                  "source de cote publique."),
    }
    return report
