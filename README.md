# Orion — assistant IA personnel

Assistant autonome multi-appareils : cerveau LLM interchangeable, outils système,
pilotage du bureau, pont vers des serveurs MCP externes (TradingView, MetaTrader 5),
et une interface cockpit 3D disponible en application de bureau.

---

## Installation

### 1. Python

```bash
pip install -r requirements.txt
```

Dépendances optionnelles, à installer selon ce que tu veux activer :

| Fichier | Débloque |
|---|---|
| `requirements-extras.txt` | pilotage du bureau, captures, notifications, PDF/DOCX |
| `requirements-voice.txt` | voix locale (Whisper + Kokoro + VAD) |
| `requirements-google.txt` | Gmail + Google Calendar |
| `requirements-rag.txt` | mémoire long terme vectorielle |
| `requirements-worker.txt` | mode worker sur un appareil distant |

### 2. Configuration

```bash
cp .env.example .env
```

Renseigne au minimum `ANTHROPIC_API_KEY` (ou `GEMINI_API_KEY`) et
`ORION_SECRET_TOKEN`. Les presets font le reste :

```bash
python start.py init                    # liste les presets
python start.py init --preset trading   # trading, voice, worker, google, minimal
```

### 3. Interface

```bash
npm --prefix frontend install
npm --prefix desktop install     # seulement pour l'application de bureau
```

---

## Lancement

| Commande | Effet |
|---|---|
| `python start.py server` | serveur central + UI navigateur |
| `python start.py cli` | CLI autonome, sans serveur |
| `python start.py voice` | service voix locale (« hey orion ») |
| `python start.py worker` | exécute les outils sur un appareil distant |
| `python start.py controller` | CLI distante vers un serveur existant |
| `python start.py ui` | ouvre seulement l'UI navigateur |
| `python start.py install-startup` | démarrage automatique Windows |
| `python start.py remove-startup` | le désactive |

### Application de bureau

```bash
npm --prefix frontend run dev     # terminal 1
npm --prefix desktop run dev      # terminal 2
```

Orion s'ouvre en fenêtre native sans bordure, plus une **capsule flottante**
toujours au-dessus dans un coin de l'écran. **Ctrl+Alt+O** rappelle ou masque le
cockpit sans quitter ce que tu fais ; un clic sur la capsule fait la même chose.

Pour empaqueter un installeur Windows :

```bash
npm --prefix frontend run build
npm --prefix desktop run build
```

---

## Le cockpit

Interface 3D commune à tous les modes : réacteur WebGL au centre, satellites
animés (radar, jauges, spectre, molécules, globe), châssis SVG. Le bloom ne
s'applique qu'au rendu WebGL — le chrome et le texte restent nets.

| Mode | Contenu |
|---|---|
| **Voix** | conversation orale, transcription flottante, micro sous le réacteur |
| **Trading** | cadran de performance, P&L cumulé, positions, signal IA, journal |
| **Bureau** | écran en direct, fenêtres avec vignettes et actions, presse-papier |
| **Système** | à construire (pont MCP, audit, santé des services) |

Le réacteur reflète l'état réel : au repos, en écoute, en traitement, en parole,
en alerte.

Routes : `/cockpit`, `/capsule`, plus les vues d'origine `/` (chat texte),
`/voice` et `/trading`, inchangées.

---

## Capacités

**Fichiers et système** — créer, lire, modifier, supprimer, déplacer ; commandes
shell ; scripts Python ; processus ; informations système.

**Web** — recherche (Brave ou DuckDuckGo), lecture de pages.

**Documents** — PDF, DOCX, vision sur images.

**Bureau** — captures, souris (déplacement, clic, glisser, molette), clavier
(frappe, combinaisons), fenêtres (lister, activer, réduire, agrandir, déplacer,
fermer), presse-papier.

**Google Workspace** — Gmail et Calendar via OAuth.

**Mémoire** — mémoire long terme vectorielle (RAG).

**Mobile** — outils Termux sur Android en mode worker.

**Trading** — analyseur Claude branché sur MetaTrader 5 via l'EA `EA/OrionTrader.mq5`,
dashboard dédié.

**Pont MCP** — Orion consomme n'importe quel serveur MCP externe comme des outils
natifs. Voir `mcp_servers.example.json` : TradingView (22 outils) et MetaTrader 5
(10 outils) sont préconfigurés.

---

## Sécurité

Orion peut effacer des fichiers, piloter la souris et passer des ordres de
marché. Plusieurs verrous, indépendants les uns des autres.

| Verrou | Rôle |
|---|---|
| `ORION_SECRET_TOKEN` | authentifie tout accès au serveur |
| `ORION_CONFIRM_PASSWORD` | mot de passe exigé avant chaque action sensible |
| `ORION_AUTOMATION_ENABLED` | interrupteur du pilotage physique (souris, clavier, fenêtres) |
| `ORION_MCP_ENABLED` | interrupteur du pont MCP |
| `ORION_TRADING_EXECUTION_ENABLED` | **séparé** : autorise les ordres de marché réels |
| Mode panic | `POST /api/panic` coupe tout instantanément |
| Rate limit | plafonne les actions sensibles par minute et en rafale |
| Audit | chaque appel d'outil est tracé dans `data/audit.db` |
| Backups | copie automatique avant toute suppression ou écrasement |

Trois points méritent d'être compris avant d'ouvrir les interrupteurs.

**Une capture d'écran capture tout ce qui est affiché**, y compris un
gestionnaire de mots de passe ouvert ou une session bancaire. Ferme ce qui est
sensible avant d'activer `ORION_AUTOMATION_ENABLED`.

**Le failsafe souris** : amener le curseur dans le coin haut-gauche de l'écran
interrompt immédiatement l'action d'automation en cours.

**Les ordres de marché** ont leur propre interrupteur, volontairement séparé du
pont MCP : Orion peut lire le marché en permanence sans qu'un ordre puisse
partir. Et même avec `ORION_CONFIRM_TOOLS=none`, ils restent soumis au mot de
passe — cette exception n'est pas désactivable.

### Endpoint d'exécution directe

`POST /api/tool` permet au cockpit d'agir sans passer par le LLM (cliquer
« réduire » sur une fenêtre ne doit pas coûter un raisonnement). Il applique la
même chaîne que l'orchestrateur : liste blanche stricte, mode panic, rate limit,
mot de passe pour les outils sensibles, audit.

---

## Tests

```bash
python tests/smoke.py                     # suite générale
python tests/test_desktop_tools.py        # outils bureau, aucune action physique
python tests/manual/desktop_e2e.py        # bout en bout — PREND LE CONTRÔLE de la machine
python tests/manual/mcp_bridge_check.py   # pont MCP — démarre les serveurs, n'envoie aucun ordre
```

Les tests de `tests/manual/` sont à lancer sciemment : le premier pilote
réellement la souris et le clavier pendant une dizaine de secondes.

---

## Architecture

```
server/          serveur FastAPI + WebSocket, orchestrateur, sécurité
  tools/         outils exposés au LLM
  mcp_bridge/    client MCP stdio générique
  trading/       analyseur IA + routes du dashboard
  memory/        mémoire vectorielle
agent/           boucle d'agent
interface/       CLI
voice/           STT, TTS, VAD, wake word
frontend/        React + Vite + Tailwind + three.js
desktop/         coque Electron (cockpit + capsule)
EA/              Expert Advisor MetaTrader 5
tests/           suites automatiques et manuelles
```

Ajouter un outil demande de toucher trois endroits : le module et son `HANDLERS`,
`ALL_HANDLERS` dans `server/tools/__init__.py`, et le schéma dans `TOOLS` de
`server/orchestrator.py` — plus `_DEVICE_BOUND_TOOLS` s'il touche au matériel, et
`DEFAULT_DANGEROUS` de `server/confirm.py` s'il est sensible.
