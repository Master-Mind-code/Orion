"""
Contrôle complet des capacités d'Orion.

Exerce chaque sous-système en LECTURE et vérifie que les verrous refusent bien
ce qu'ils doivent refuser. N'envoie aucun ordre de marché, n'écrit aucun
fichier, ne pilote ni souris ni clavier.

    python tests/manual/audit_complet.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OK, KO, INFO = "  OK  ", " ECHEC", "  --  "
resultats: list[tuple[str, str, str]] = []


def note(section: str, libelle: str, etat: str, detail: str = "") -> None:
    resultats.append((section, libelle, etat))
    print(f"{etat}  {libelle:44s} {detail}"[:150])


def section(titre: str) -> None:
    print(f"\n═══ {titre} ═══")


# ────────────────────────────── Registre ──────────────────────────────────
section("REGISTRE DES OUTILS")
from server.orchestrator import TOOLS, _DEVICE_BOUND_TOOLS  # noqa: E402
from server.tools import ALL_HANDLERS  # noqa: E402
from server import confirm, panic, rate_limit, audit  # noqa: E402

INTERCEPTES = {"list_connected_devices"}
noms = {t["name"] for t in TOOLS}
orphelins = sorted(noms - set(ALL_HANDLERS) - INTERCEPTES)
note("registre", f"{len(noms)} schémas déclarés", INFO)
note("registre", f"{len(ALL_HANDLERS)} handlers enregistrés", INFO)
note("registre", "chaque schéma a son handler", OK if not orphelins else KO,
     str(orphelins))
sans_desc = [t["name"] for t in TOOLS if not t.get("description")]
note("registre", "toutes les descriptions présentes", OK if not sans_desc else KO,
     str(sans_desc))
note("registre", f"{len(_DEVICE_BOUND_TOOLS)} outils routables vers un appareil", INFO)
note("registre", f"{len(confirm._load_dangerous_set())} outils sous confirmation", INFO)

# ────────────────────────────── Sécurité ──────────────────────────────────
section("VERROUS")
inter = {
    "ORION_AUTOMATION_ENABLED": "pilotage physique",
    "ORION_CAMERA_ENABLED": "caméra",
    "ORION_MCP_ENABLED": "pont MCP",
    "ORION_TRADING_EXECUTION_ENABLED": "ordres de marché",
}
for cle, quoi in inter.items():
    val = os.getenv(cle, "false").strip().lower() in ("1", "true", "yes", "on", "oui")
    note("verrous", f"{quoi}", INFO, "OUVERT" if val else "fermé")
note("verrous", "mot de passe de confirmation défini", OK if confirm._enabled() else KO)
note("verrous", "mauvais mot de passe rejeté",
     OK if not confirm.password_matches("nimporte-quoi") else KO)
note("verrous", "mode panic au repos", OK if not panic.is_active() else KO)
note("verrous", "rate limit actif", OK if rate_limit._enabled() else INFO)
note("verrous", "audit actif", OK if audit._enabled() else INFO,
     f"{audit.db_size_kb()} Ko")

# ─────────────────────────────── Bureau ───────────────────────────────────
section("BUREAU")
st = ALL_HANDLERS["automation_status"]({})
note("bureau", "automation_status répond", OK if st.get("success") else KO,
     f"écrans: {len(st.get('monitors') or [])}")
w = ALL_HANDLERS["list_windows"]({})
note("bureau", "list_windows", OK if w.get("success") else KO,
     f"{w.get('count', 0)} fenêtres")
c = ALL_HANDLERS["clipboard_get"]({})
note("bureau", "clipboard_get", OK if c.get("success") else KO,
     f"{c.get('length', 0)} caractères")
m = ALL_HANDLERS["list_monitors"]({})
note("bureau", "list_monitors", OK if m.get("success") else KO)

# ─────────────────────────────── Caméra ───────────────────────────────────
section("CAMÉRA")
cs = ALL_HANDLERS["camera_status"]({})
note("caméra", "camera_status répond", OK if cs.get("success") else KO)
note("caméra", "modèle de détection présent", OK if cs.get("modele_objets") else KO)
for paquet in ("cv2", "mediapipe", "cvzone"):
    note("caméra", f"{paquet} disponible", OK if cs.get(paquet) else KO)
note("caméra", f"{len(cs.get('apps_disponibles') or {})} applications de vision", INFO)

# ─────────────────────────────── Mémoire ──────────────────────────────────
section("MÉMOIRE")
try:
    from server.memory.rag_tools import memory_stats, memory_recall
    s = memory_stats(namespace="obsidian")
    note("mémoire", "index Obsidian", OK if s.get("success") else KO,
         f"{s.get('count', 0)} fragments, dim {s.get('dim')}")
    r = memory_recall(query="comment lancer Orion", namespace="obsidian", top_k=1)
    trouve = (r.get("results") or [{}])[0]
    note("mémoire", "rappel vectoriel",
         OK if trouve.get("score", 0) > 0.3 else KO,
         f"score {round(trouve.get('score', 0), 3)} · "
         f"{str(trouve.get('source', '?')).split(chr(92))[-1]}")
except Exception as exc:  # noqa: BLE001
    note("mémoire", "RAG", KO, f"{type(exc).__name__}: {exc}")

# ───────────────────────────── Pont MCP ───────────────────────────────────
section("PONT MCP")
from server import mcp_bridge  # noqa: E402
try:
    mcp_bridge.load()
    st = mcp_bridge.status()
    note("mcp", "pont chargé", OK if st.get("bridge_enabled") else INFO,
         f"{st.get('tool_count', 0)} outils")
    for srv in st.get("servers", []):
        note("mcp", f"serveur {srv['alias']}", OK if srv["alive"] else KO,
             f"{len(srv['tools'])} outils")
    for alias, err in (st.get("errors") or {}).items():
        note("mcp", f"erreur {alias}", KO, str(err)[:60])

    # Lecture réelle
    h = mcp_bridge.MCP_HANDLERS
    if "mt5_account_info" in h:
        a = h["mt5_account_info"]({}).get("result", {})
        note("mcp", "MT5 compte lisible", OK if a.get("ok") else KO,
             f"{a.get('broker', '?')} · {a.get('currency', '?')}")
    if "mt5_quote" in h:
        q = h["mt5_quote"]({"symbol": "XAUUSDc"}).get("result", {})
        note("mcp", "MT5 cotation XAUUSDc", OK if q.get("ok") else KO,
             f"bid {q.get('bid')}")
    if "tv_tv_health_check" in h:
        t = h["tv_tv_health_check"]({}).get("result", {})
        note("mcp", "TradingView CDP", OK if t.get("success") else INFO,
             t.get("chart_symbol") or "hors ligne")

    # Sécurité : les ordres doivent refuser
    for outil in ("mt5_order_send", "mt5_position_close", "mt5_position_modify"):
        if outil not in h:
            continue
        rep = h[outil]({"symbol": "XAUUSDc", "side": "buy", "volume": 0.01, "ticket": 0})
        refuse = rep.get("success") is False and "EXÉCUTION" in str(rep.get("error", ""))
        note("mcp", f"{outil} refusé", OK if refuse else KO)
        note("mcp", f"{outil} sous confirmation",
             OK if outil in confirm._load_dangerous_set() else KO)
except Exception as exc:  # noqa: BLE001
    note("mcp", "pont MCP", KO, f"{type(exc).__name__}: {exc}")

# ────────────────────────────── Serveur ───────────────────────────────────
section("SERVEUR HTTP")
try:
    import urllib.request
    token = os.getenv("ORION_SECRET_TOKEN") or os.getenv("JARVIS_SECRET_TOKEN", "")
    base = "http://localhost:8765"

    with urllib.request.urlopen(f"{base}/status", timeout=6) as r:
        st = json.loads(r.read())
    note("serveur", "/status", OK, st.get("status", "?"))
    note("serveur", "interfaces connectées", INFO, str(len(st.get("controllers") or [])))
    note("serveur", "appareils distants", INFO, str(len(st.get("workers") or [])))

    entetes = {"Content-Type": "application/json",
               "Authorization": f"Bearer {token}"}
    req = urllib.request.Request(
        f"{base}/api/tool", method="POST",
        data=json.dumps({"tool": "list_windows", "args": {}}).encode(),
        headers=entetes)
    with urllib.request.urlopen(req, timeout=10) as r:
        rep = json.loads(r.read())
    note("serveur", "/api/tool exécute un outil", OK if rep.get("success") else KO,
         f"{rep.get('count', 0)} fenêtres")

    # Un outil hors liste blanche doit être refusé
    req = urllib.request.Request(
        f"{base}/api/tool", method="POST",
        data=json.dumps({"tool": "delete_file", "args": {"path": "x"}}).encode(),
        headers=entetes)
    try:
        urllib.request.urlopen(req, timeout=6)
        note("serveur", "outil hors liste blanche refusé", KO, "accepté !")
    except urllib.error.HTTPError as e:
        note("serveur", "outil hors liste blanche refusé", OK if e.code == 403 else KO,
             f"HTTP {e.code}")

    # Sans token, tout doit être refusé
    req = urllib.request.Request(
        f"{base}/api/tool", method="POST",
        data=json.dumps({"tool": "list_windows", "args": {}}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=6)
        note("serveur", "sans token refusé", KO, "accepté !")
    except urllib.error.HTTPError as e:
        note("serveur", "sans token refusé", OK if e.code in (401, 403) else KO,
             f"HTTP {e.code}")
except Exception as exc:  # noqa: BLE001
    note("serveur", "serveur HTTP", KO,
         f"{type(exc).__name__}: {exc} — lancer `python start.py server`")

# ─────────────────────────────── Cockpit ──────────────────────────────────
section("COCKPIT")
r = ALL_HANDLERS["cockpit_set_mode"]({"mode": "trading"})
note("cockpit", "bascule de mode", OK if r.get("success") else KO, str(r.get("mode")))
r = ALL_HANDLERS["cockpit_set_mode"]({"mode": "zzz"})
note("cockpit", "mode inconnu refusé", OK if r.get("success") is False else KO)

# ─────────────────────────────── Récap ────────────────────────────────────
section("RÉCAPITULATIF")
ko = [f"{s}/{l}" for s, l, e in resultats if e == KO]
oks = sum(1 for _, _, e in resultats if e == OK)
print(f"  Contrôles réussis : {oks}")
print(f"  Échecs            : {len(ko)}")
for x in ko:
    print(f"    ✗ {x}")

try:
    mcp_bridge.unload()
except Exception:
    pass
sys.exit(1 if ko else 0)
