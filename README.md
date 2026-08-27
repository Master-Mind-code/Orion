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
| `requirements-learning.txt` | ingestion de vidéos dans la base de connaissances |
| `requirements-worker.txt` | mode worker sur un appareil distant |

`requirements-learning.txt` suppose `requirements-rag.txt` installé, et la
transcription audio réclame en plus **ffmpeg**, qui n'est pas un paquet pip :

```bash
winget install Gyan.FFmpeg
```

Rouvre le terminal ensuite — et redémarre Orion s'il tournait déjà, sinon il
garde l'ancien `PATH` et ne verra pas ffmpeg.

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
npm --prefix desktop run dev
```

Une seule commande : elle démarre le serveur d'interface **et** la coque native,
et la coque attend que l'interface réponde avant d'ouvrir ses fenêtres. Si le
port 5173 est déjà pris, Vite échoue franchement au lieu de glisser sur un autre
port — libère-le ou coupe l'instance qui tourne déjà.

Pour ne lancer que la coque, l'interface tournant déjà ailleurs :

```bash
npm --prefix desktop run dev:coque
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

## Routes

| Adresse | Vue |
|---|---|
| `/` et `/cockpit` | le cockpit — point d'entrée par défaut |
| `/chat` | ancienne interface de chat texte, avec sa grille de mot de passe |
| `/voice` · `/trading` | vues d'origine, inchangées |
| `/capsule` | la capsule flottante (chargée par la coque Electron) |

Les mots de déverrouillage du chat texte se règlent par la variable
`VITE_ORION_UNLOCK_WORDS` (fichier `.env` du dossier `frontend/`) ou par la clé
`ORION_UNLOCK_WORDS` du localStorage — ils ne sont plus écrits dans le dépôt.
Tout ce qui porte le préfixe `VITE_` finit en clair dans le bundle : ces mots
gardent l'ouverture de l'interface, le vrai contrôle d'accès reste
`ORION_SECRET_TOKEN` côté serveur.

---

## Capacités (141 outils natifs)

Le décompte est vérifié par `tests/test_tools_registry.py`, qui échoue si un
handler existe sans schéma — auquel cas l'outil est du code mort, invisible pour
le LLM.

**Fichiers et système** — créer, lire, modifier, supprimer, déplacer ; commandes
shell ; scripts Python ; processus ; informations système (`get_system_metrics`,
`list_running_processes`).

**Bureau** — captures, souris, clavier, fenêtres Windows, presse-papier.

**Documents & Vision** — PDF, DOCX, analyse multimodale d'images, reconnaissance
faciale locale et gestes caméra (`camera_vision.py`).

**Deep Research & Web** — recherche multi-sources récursive avec synthèse
documentaire (`run_deep_research`), lecture de pages web (`fetch_url`), moteurs
DuckDuckGo / Brave Search.

**Google Workspace** — Gmail, Calendar, fichiers Google Drive
(`google_drive_list`), insertion de lignes dans Google Sheets
(`google_sheets_append`).

**Routines, RPA Bureau & Multi-Agents** — planification de tâches récurrentes
(`create_routine`), enregistreur et rejoueur de macros physiques sur le bureau
(`add_macro_step`, `play_macro`), sous-agents spécialisés
(`delegate_subagent_task`).

**Pont MCP** — Orion consomme n'importe quel serveur MCP externe comme des outils
natifs. Voir `mcp_servers.example.json` : TradingView (22 outils) et MetaTrader 5
(10 outils) sont préconfigurés.

### Base de connaissances évolutive

`learn_from_source` ingère indifféremment un fichier, un dossier, une page web,
une vidéo, un média local ou du texte brut : il reconnaît seul le type.
`learn_from_topic` part chercher sur le web sans qu'on lui donne de liens.
`learn_from_inbox` traite ce qui est déposé dans `data/knowledge_inbox`, surveillé
en continu — les fichiers appris y sont **archivés dans `_traites`, jamais
supprimés**. `knowledge_teach` restitue la matière avec ses sources,
`knowledge_status` dit ce qui a été appris et d'où.

Veille programmée par `ORION_LEARNING_TOPICS`. Vidéos : sous-titres d'abord,
transcription yt-dlp + Whisper à défaut.

> **Ce n'est pas du ré-entraînement.** Orion range du contenu dans une mémoire
> consultable et répond mieux parce qu'il retrouve plus de matière. Les poids du
> modèle ne changent pas : ils vivent chez Anthropic et Google, et rien depuis
> cette machine ne peut les modifier.

### Marché BRVM — données réelles

Cote relevée sur **brvm.org** et **sikafinance.com** (`server/trading/brvm_live.py`) :
les 47 valeurs, 12 indices, capitalisations, secteurs, historique des dividendes,
RSI, bêta 1 an, extrêmes 52 semaines, et 60 séances OHLCV par valeur.

Cours **différés de 15 minutes** pendant la séance, cache calé sur ce délai.
Chaque réponse porte un bloc `data_provenance` : si la collecte échoue, Orion
sert le fichier de référence marqué `is_live: false` — jamais en silence.

| Outil | Usage |
|---|---|
| `brvm_live_quote` | cote directe d'une ou plusieurs valeurs |
| `brvm_stock_analysis` | analyse complète + prédiction Kronos |
| `brvm_stock_picker` | classement par profil (dividend, growth, value, balanced) |
| `brvm_income_portfolio` | portefeuille visant un revenu mensuel en dividendes |
| `brvm_market_refresh` | force la collecte, diagnostique chaque source |

**Deux limites à connaître.** PER, ROE et marge nette ne sont publiés par aucune
source : ils viennent du fichier de référence, portent
`ratios_source: "reference_statique"` et ne doivent pas être présentés comme des
données de marché — ce qui pèse sur le score Orion, dont ils représentent la
moitié. Et `richbourse.com` (HTTP 403) comme `bstrade.bridge-securities.com`
(chaîne TLS incomplète) sont inexploitables côté serveur.

Le portefeuille de revenu planifie sur le **dividende récurrent**, pas sur le
dernier versement : une distribution exceptionnelle est détectée par comparaison
aux exercices antérieurs et signalée plutôt qu'extrapolée.

### Trading

- **Mission de Survie (100.000 / jour)** — suivi du P&L quotidien, *Health Score*
  0-100 %, limites de drawdown et bascule automatique en *Cooldown*, widget HUD
  dédié.
- **Kronos pour la BRVM** — modèle neuronal PyTorch autorégressif
  (*NeoQuasar/Kronos-mini*) alimenté par les 60 dernières séances réelles de la
  valeur. Refuse de prédire en dessous de 20 séances disponibles plutôt que de
  produire un chiffre sur des données reconstruites.
- **Backtesting & alertes** — `run_strategy_backtest`, et diffusion sur Telegram,
  Discord et Email (`send_alert_notification`).
- **MetaTrader 5 & TradingView** — analyseur branché sur MT5 via
  `EA/OrionTrader.mq5`, pont MCP pour TradingView, dashboard dédié.

### Marketing, e-commerce et QA — modules à l'état de maquette

Ces quatre modules sont câblés et répondent, mais renvoient des **données
simulées** : chiffre d'affaires codé en dur, ROAS fictif, tests toujours au vert,
chemins vidéo jamais écrits. Utilisables comme squelette, pas comme source de
vérité — et Orion les présentera comme des faits tant qu'ils ne seront pas
branchés sur leurs vraies API.

| Module | Outils | État |
|---|---|---|
| Création visuelle & Canva | `generate_marketing_visual`, `canva_automation_create` | image réelle (Imagen 3), assemblage Canva simulé |
| E-commerce & publicité | `chariow_manage_store`, `facebook_ads_manager` | simulé |
| Production vidéo IA | `generate_ai_video`, `create_video_ad_campaign` | simulé |
| Tests QA E2E | `run_app_e2e_test`, `generate_qa_bug_report` | simulé |


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

Quatre points méritent d'être compris avant d'ouvrir les interrupteurs.

**`ORION_CONFIRM_PASSWORD` non renseigné désactive toute la couche de
confirmation**, pour *tous* les outils — `delete_file` et `run_shell_command`
compris, pas seulement ceux qu'on croirait tolérables. Renseigne-le si tu
comptes sur ce verrou.

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
python tests/test_tools_registry.py       # parité handlers / schémas — aucun réseau
python tests/test_knowledge.py            # ingestion et restitution des connaissances
python tests/test_brvm_live.py            # collecte BRVM réelle et mode dégradé
python tests/smoke.py                     # suite générale
python tests/test_full_kronos_orion_pipeline.py  # pipeline complet Kronos + Orion
python tests/test_brvm_engine.py          # moteur d'analyse BRVM, portefeuille & Kronos
python tests/test_desktop_tools.py        # outils bureau, aucune action physique
python tests/manual/desktop_e2e.py        # bout en bout — PREND LE CONTRÔLE de la machine
python tests/manual/mcp_bridge_check.py   # pont MCP — démarre les serveurs, n'envoie aucun ordre
```

`test_brvm_live.py` interroge les vraies plateformes ; ses tests en ligne
s'ignorent d'eux-mêmes si le réseau ne répond pas, pour qu'une coupure ne fasse
pas passer la suite pour cassée. `test_knowledge.py` travaille dans un namespace
jetable et nettoie derrière lui.

Les tests de `tests/manual/` sont à lancer sciemment : le premier pilote
réellement la souris et le clavier pendant une dizaine de secondes.

---

## Architecture

```
server/          serveur FastAPI + WebSocket, orchestrateur, sécurité
  tools/         outils exposés au LLM (bureau, web, vision, BRVM, Kronos, etc.)
  mcp_bridge/    client MCP stdio générique
  trading/       analyseur IA, mission 100k, moteur BRVM, moteur neuronal Kronos + routes HTTP
    brvm_live.py   collecte de la cote réelle sur brvm.org et sikafinance
  memory/        mémoire vectorielle
    knowledge.py    ingestion universelle et restitution des connaissances
    media_ingest.py extraction du texte des vidéos et de l'audio
data/            persistance JSON/SQLite (mission_state.json, audit.db, caches)
  knowledge_inbox/  dépose un document ici, Orion l'apprend seul
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

Oublier le schéma ne casse rien visiblement : l'outil existe, mais le LLM ignore
son existence et ne l'appellera jamais. C'est arrivé sur 24 outils d'un coup.
`tests/test_tools_registry.py` verrouille désormais cette parité.
