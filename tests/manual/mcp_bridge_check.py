"""
Vérification du pont MCP d'Orion (TradingView + MetaTrader 5).

⚠ MANUEL — démarre réellement les serveurs MCP déclarés dans mcp_servers.json.
N'ENVOIE AUCUN ORDRE : seuls des tools de lecture sont appelés, et le refus des
tools d'exécution est vérifié explicitement.

    python tests/manual/mcp_bridge_check.py
"""
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(ICI))
sys.path.insert(0, PROJ)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJ, ".env"))

from server import mcp_bridge
from server.orchestrator import get_tools
from server.confirm import _load_dangerous_set

echecs = []


def verifie(nom, cond, detail=""):
    print(f"   {'OK  ' if cond else 'ECHEC'} {nom} {detail}")
    if not cond:
        echecs.append(nom)


print("[1] Chargement du pont")
mcp_bridge.load()
st = mcp_bridge.status()
print("   bridge_enabled   :", st["bridge_enabled"])
print("   execution_enabled:", st["execution_enabled"])
print("   tools exposés    :", st["tool_count"])
if st["errors"]:
    print("   ERREURS          :", json.dumps(st["errors"], ensure_ascii=False))
for s in st["servers"]:
    print(f"   - {s['alias']}: alive={s['alive']} "
          f"({len(s['tools'])} tools) {s['server_info'].get('name', '')}")
verifie("au moins un serveur connecté", any(s["alive"] for s in st["servers"]))

print("\n[2] Les schémas MCP arrivent bien dans get_tools()")
noms = {t["name"] for t in get_tools()}
verifie("mcp_status présent", "mcp_status" in noms)
verifie("des tools mt5_* exposés", any(n.startswith("mt5_") for n in noms),
        str(sorted(n for n in noms if n.startswith("mt5_"))))
verifie("des tools tv_* exposés", any(n.startswith("tv_") for n in noms),
        str(sorted(n for n in noms if n.startswith("tv_"))[:6]) + " ...")

print("\n[3] SÉCURITÉ — les tools d'exécution sont refusés (switch à false)")
if mcp_bridge.execution_enabled():
    print("   ATTENTION : ORION_TRADING_EXECUTION_ENABLED=true, test non concluant.")
    echecs.append("switch exécution déjà ouvert pendant le test")
else:
    for nom in ("mt5_order_send", "mt5_position_close", "mt5_position_modify"):
        h = mcp_bridge.MCP_HANDLERS.get(nom)
        if h is None:
            verifie(f"{nom} exposé", False, "(absent)")
            continue
        # Arguments volontairement inoffensifs : le refus doit tomber AVANT
        # tout contact avec le serveur.
        r = h({"symbol": "XAUUSD", "side": "buy", "volume": 0.01, "ticket": 0})
        refuse = r.get("success") is False and "EXÉCUTION" in r.get("error", "")
        verifie(f"{nom} refusé", refuse, r.get("error", "")[:70])

print("\n[4] SÉCURITÉ — les ordres exigent la confirmation par mot de passe")
dangereux = _load_dangerous_set()
for nom in ("mt5_order_send", "mt5_position_close", "mt5_position_modify"):
    verifie(f"{nom} dans la liste de confirmation", nom in dangereux)

print("\n[5] LECTURE — MetaTrader 5")
for nom, params in (("mt5_account_info", {}),
                    ("mt5_symbol_info", {"symbol": "XAUUSDc"}),
                    ("mt5_quote", {"symbol": "XAUUSDc"})):
    h = mcp_bridge.MCP_HANDLERS.get(nom)
    if h is None:
        print(f"   {nom}: non exposé")
        continue
    r = h(params)
    apercu = json.dumps(r, ensure_ascii=False)[:220]
    print(f"   {nom} -> {apercu}")

print("\n[6] LECTURE — TradingView")
for nom, params in (("tv_tv_health_check", {}), ("tv_quote_get", {"symbol": "OANDA:XAUUSD"})):
    h = mcp_bridge.MCP_HANDLERS.get(nom)
    if h is None:
        print(f"   {nom}: non exposé")
        continue
    r = h(params)
    print(f"   {nom} -> {json.dumps(r, ensure_ascii=False)[:220]}")

print("\n[7] Arrêt propre des serveurs")
mcp_bridge.unload()
verifie("tous les process arrêtés",
        all(not c.alive() for c in mcp_bridge.CLIENTS.values()) or not mcp_bridge.CLIENTS)

print("\n==== RÉSULTAT :", "OK" if not echecs else f"ÉCHECS : {echecs}", "====")
sys.exit(1 if echecs else 0)
