# Manuel Magistral des Capacités d'Orion — Édition Master v3.1

> **Version Système** : Orion v3.1 (Master-Mind Architecture)
> **Statut Opérationnel** : Actif & Déployé — **141 outils natifs**
> **Dernière Mise à Jour** : 27 août 2026
> **Auteur & Conception** : Équipe Advanced Agentic Coding

> **Comment lire ce manuel.** Chaque chapitre indique ce qui repose sur des
> données réelles et ce qui n'est encore qu'une maquette. Un module marqué
> *maquette* est câblé et répond, mais renvoie des valeurs codées en dur : il ne
> faut pas fonder de décision dessus. Le décompte des 141 outils est vérifié par
> `tests/test_tools_registry.py`, pas déclaré à la main.

---

## Sommaire Magistral

1. [Vue d'Ensemble & Philosophie de l'IA Autonome](#1-vue-densemble--philosophie-de-lia-autonome)
2. [Architecture & Cerveau Multimodal Orion](#2-architecture--cerveau-multimodal-orion)
3. [La Mission de Survie Haute Performance (100.000 / Jour)](#3-la-mission-de-survie-haute-performance-100000--jour)
4. [Module d'Analyse & Sélecteur d'Actions BRVM (150.000 FCFA / Mois)](#4-module-danalyse--sélecteur-dactions-brvm-150000-fcfa--mois)
5. [Moteur Neuronal Fondateur Kronos PyTorch](#5-moteur-neuronal-fondateur-kronos-pytorch)
6. [Pilotage Physique du Bureau & Vision Synthétique](#6-pilotage-physique-du-bureau--vision-synthétique)
7. [Service Vocal Immersif & Biométrie Locale](#7-service-vocal-immersif--biométrie-locale)
8. [Pont Inter-Processus MCP (TradingView & MetaTrader 5)](#8-pont-inter-processus-mcp-tradingview--metatrader-5)
9. [Architecture de Sécurité, Audit & Mode Panic](#9-architecture-de-sécurité-audit--mode-panic)
10. [Studio de Création Visuelle, Canva & IA Marketing](#10-studio-de-création-visuelle-canva--ia-marketing)
11. [Gestion E-Commerce Chariow & Facebook Ads Manager](#11-gestion-e-commerce-chariow--facebook-ads-manager)
12. [Producteur & Générateur de Vidéos IA Réalistes](#12-producteur--générateur-de-vidéos-ia-réalistes)
13. [Agent Testeur QA E2E d'Applications par Excellence](#13-agent-testeur-qa-e2e-dapplications-par-excellence)
14. [Deep Research Web Multi-Sources & Document Cloud](#14-deep-research-web-multi-sources--document-cloud)
15. [Routines Automatiques, RPA Bureau & Multi-Agents](#15-routines-automatiques-rpa-bureau--multi-agents)
16. [Backtesting de Stratégies Financières & Alertes Multi-Canal](#16-backtesting-de-stratégies-financières--alertes-multi-canal)
17. [Cockpit 3D WebGL & Boîte de Réponse HUD Holographique](#17-cockpit-3d-webgl--boîte-de-réponse-hud-holographique)
18. [Base de Connaissances Évolutive & Apprentissage Continu](#18-base-de-connaissances-évolutive--apprentissage-continu)
19. [Catalogue Exhaustif des Outils Natifs (Sitemap System)](#19-catalogue-exhaustif-des-outils-natifs-sitemap-system)

---

## 1. Vue d'Ensemble & Philosophie de l'IA Autonome

**Orion** est un assistant IA personnel de classe souveraine et autonome, conçu pour fonctionner directement sur l'appareil de l'utilisateur. Contrairement aux agents conversationnels passifs, Orion est doté de capacités d'action directe : il interagit avec le système d'exploitation, manipule les fichiers, exécute des scripts, pilote les fenêtres graphiques, analyse les flux financiers internationaux et régionaux, gère des boutiques e-commerce, produit du contenu multimédia et surveille les marchés en continu.

### Principes Fondeurs :
- **Survie du Capital & Discipline Absolue** : Rigueur d'exécution maximale. Aucun compromis sur la gestion du risque.
- **Proactivity Autonome** : Orion n'attend pas des instructions pas-à-pas ; il planifie, analyse et exécute les sous-tâches jusqu'à l'atteinte de l'objectif final.
- **Exécution Souveraine Locale** : Les données sensibles, les visages biométriques et les clés d'API restent sous le contrôle strict de la machine hôte.

---

## 2. Architecture & Cerveau Multimodal Orion

L'architecture d'Orion s'articule autour d'un serveur central FastAPI + WebSocket à haute vélocité et d'une suite de clients spécialisés.

```
                         ┌─────────────────────────┐
                         │   Cockpit 3D WebGL /    │
                         │   Coque Electron / CLI  │
                         └────────────┬────────────┘
                                      │ WebSocket / HTTP
                                      ▼
                         ┌─────────────────────────┐
                         │ Serveur Central FastAPI │
                         │   (server/main.py)      │
                         └────────────┬────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
   ┌────────────────────┐   ┌────────────────────┐   ┌────────────────────┐
   │ Orchestrateur LLM  │   │  Moteur Trading &  │   │   Pont MCP Stdio   │
   │ (Anthropic/Gemini) │   │ Mission Engine 100k│   │ (MT5 / TradingView)│
   └──────────┬─────────┘   └──────────┬─────────┘   └────────────────────┘
              │                        │
              ▼                        ▼
   ┌────────────────────┐   ┌────────────────────┐
   │ 141 Tools Natifs   │   │ BRVM & Kronos      │
   │ (File/QA/Video/Ads)│   │ Neural Engine      │
   └────────────────────┘   └────────────────────┘
```

### Composants Clés :
1. **Orchestrateur Central (`server/orchestrator.py`)** : Reçoit le flux de requêtes, formule les plans d'actions, effectue le routage des 141 outils natifs et gère les boucles d'itération (jusqu'à 25 itérations autonomes par demande).
2. **Fournisseurs de LLM Interchangeables (`server/providers/`)** : Bascule transparente entre Anthropic Claude (Haiku, Sonnet, Opus) et Google Gemini.
3. **Cockpit 3D & Boîte HUD Holographique (`frontend/src/`)** : Interface futuriste WebGL en 4 modes (Voix, Trading, Bureau, Système) avec réacteur réactif et boîte de réponse `OrionResponseBox` biseautée en verre blindé.
4. **Agents Workers Distants (`agent/agent.py`)** : Permet à un serveur central d'exécuter des outils sur d'autres appareils distants (smartphones Android via Termux, PC distants).

---

## 3. La Mission de Survie Haute Performance (100.000 / Jour)

Pour maximiser la création de valeur et l'efficacité d'Orion, une directive système de sur-performance a été intégrée : la **Mission de Survie 100.000 / Jour**.

### Fonctionnement & Architecture :
- **Moteur de Mission (`server/trading/mission_engine.py`)** : Suit l'accumulation du PnL quotidien en temps réel vers l'objectif de 100.000 USD/EUR.
- **Score de Santé du Capital (*Health Score* 0-100%)** : Évalue en continu la sécurité du portefeuille. Chaque perte fait baisser le Health Score, chaque gain le réordonne.
- **Verrou d'Urgence (*Max Daily Drawdown & Cooldown*)** : Si les pertes quotidiennes atteignent le seuil toléré (défaut: 2.0%), Orion active un mode *Cooldown* verrouillant toute nouvelle prise de risque jusqu'au lendemain.
- **HUD Cockpit dédié (`trading_dashboard.html`)** : Jauge visuelle animée affichant en direct la progression du jour, le montant cumulé et l'état du mode survie.

---

## 4. Module d'Analyse & Sélecteur d'Actions BRVM (150.000 FCFA / Mois)

Orion est équipé d'un moteur expert dédié à la **BRVM (Bourse Régionale des Valeurs Mobilières de l'UEMOA - Abidjan)**, alimenté par la cote réelle du marché.

### Collecte des Données Réelles (`server/trading/brvm_live.py`)

| Donnée | Source | Fraîcheur |
|---|---|---|
| Cours, variation, volume, veille, ouverture — **47 valeurs** | brvm.org (officiel) | différé 15 min |
| **12 indices** (Composite, 30, Prestige, Principal, 7 sectoriels) | brvm.org | différé 15 min |
| Capitalisation, titres en circulation, secteur | brvm.org | séance |
| OHLC intraday, pays de cotation | sikafinance.com | séance |
| Historique des dividendes, multi-exercices | sikafinance.com | annuel |
| RSI, bêta 1 an, extrêmes 52 semaines | sikafinance.com | à la demande |
| **60 séances OHLCV** par valeur | sikafinance.com | quotidien |

Cache calé sur le délai de diffusion de la Bourse : rafraîchir plus vite ne
rapporte rien. Toute réponse porte un bloc `data_provenance` (`is_live`,
`stale`, `market_timestamp`, `session_status`). Si la collecte échoue, Orion sert
le fichier de référence explicitement marqué `is_live: false` — il ne présente
jamais une donnée figée comme une donnée de marché.

**Deux plateformes sont inexploitables côté serveur** et rapportées comme telles
par `brvm_market_refresh` : `richbourse.com` répond HTTP 403 à tout client
non-navigateur, et `bstrade.bridge-securities.com` sert une chaîne TLS incomplète
dont la vérification échoue — c'est par ailleurs un portail de courtage
authentifié, pas une source de cote publique.

### Capacités Majeures BRVM
- **Cote directe (`brvm_live_quote`)** : cours, variation, volume et capitalisation d'une ou plusieurs valeurs. Réponse légère, pour répondre à « combien vaut Sonatel ? » sans déclencher l'analyse complète.
- **Rafraîchissement & diagnostic (`brvm_market_refresh`)** : force la collecte et rapporte l'état de chaque plateforme.
- **Calcul du Orion Score BRVM (0-100)** : évaluation croisée du rendement dividende, de la sous-évaluation (PER), de la rentabilité (ROE) et du momentum.
- **Portefeuille de Revenu Cible (`brvm_income_portfolio`)** : nombre exact de titres à acheter pour viser 150.000 FCFA / mois de dividendes, aux cours du jour.
- **Sélecteur d'Actions par Profil (`brvm_stock_picker`)** : classement selon 4 stratégies : `dividend`, `growth`, `value`, `balanced`.

### Ce que les sources ne publient pas

**PER, ROE et marge nette n'apparaissent sur aucune des plateformes.** Ils
proviennent du fichier de référence `data/brvm_stocks.json`, portent
`ratios_source: "reference_statique"` et ne doivent pas être présentés comme des
données du jour. Ce fichier ne couvre que 12 des 47 valeurs : pour les 35 autres,
le score retombe sur des valeurs par défaut. Comme le PER pèse 25 % du Orion
Score et la rentabilité 25 %, **la moitié du score repose sur cette base de
référence** — le classement est une aide au tri, pas un verdict.

### Dividendes exceptionnels

Le portefeuille de revenu planifie sur le **dividende récurrent**, jamais sur le
dernier versement. FILTISAC a distribué 1 727 FCFA en 2024 contre 130 en 2023 :
extrapolé, ce versement affichait 79 % de rendement et aurait dimensionné le
portefeuille sur un flux qui ne se reproduira pas. Chaque dernier versement est
comparé à la médiane des exercices *antérieurs* — et non à la médiane globale,
que le versement exceptionnel fausserait lui-même — puis signalé par
`dividend_is_exceptional`.

---

## 5. Moteur Neuronal Fondateur Kronos PyTorch

Orion intègre le modèle de fondation neuronal **Kronos PyTorch (NeoQuasar/Kronos-mini)**, spécialisé dans la prédiction de séries temporelles K-lines.

### Alimentation en données réelles

Sur la BRVM, l'inférence porte sur les **60 dernières séances quotidiennes
réelles** de la valeur, récupérées via `brvm_live.fetch_sika_history()`. L'ATR et
les swings sont calculés sur cet historique, pas estimés.

En dessous de 20 séances disponibles, le moteur **refuse de prédire** et le dit,
plutôt que de produire un chiffre sur des données trop minces.

Chaque prédiction rapporte `history_sessions_used`, `history_range` et
`history_source` : on doit pouvoir vérifier sur quoi le modèle a travaillé.

> **Correction v3.1.** Jusqu'en v3.0, l'inférence BRVM tournait sur 40 chandeliers
> **reconstruits par interpolation** entre la moyenne mobile 50 et le cours du
> jour : la « prévision neuronale » n'était qu'une fonction de la tendance déjà
> affichée. De plus, l'appelant lisait `res["pred_close"]` là où le moteur
> renvoie `predicted_close`, si bien que le résultat retombait systématiquement
> sur le cours actuel — soit une variation annoncée de 0,00 % à chaque appel,
> sans que rien ne le signale. Les deux défauts sont corrigés et verrouillés par
> `tests/test_brvm_live.py`.

---

## 6. Pilotage Physique du Bureau & Vision Synthétique

Orion peut interagir physiquement avec le système d'exploitation comme le ferait un opérateur humain (Souris, Clavier, Fenêtres Windows, Capture de Région, Analyse Multimodale).

---

## 7. Service Vocal Immersif & Biométrie Locale

- **OpenAI Whisper local** (STT), **Kokoro TTS** (voix naturelle), **VAD** et Wake Word ("Hey Orion").
- **Biométrie faciale locale** et détection de gestes de la main par vision synthétique (`camera_vision.py`).

---

## 8. Pont Inter-Processus MCP (TradingView & MetaTrader 5)

Bridge stdio générique consommant les serveurs MCP externes : TradingView (22 outils) et MetaTrader 5 (10 outils).

---

## 9. Architecture de Sécurité, Audit & Mode Panic

8 couches de sécurité superposées (Secret Token, Password confirmation, Hardware automation toggle, Trading execution toggle, Panic Endpoint, Souris Fail-Safe, Audit SQLite, Safety Backups).

---

## 10. Studio de Création Visuelle, Canva & IA Marketing

Orion intègre un studio de génération de visuels publicitaires et de créations marketing (`server/tools/crea_design.py`).

> **État : partiellement réel.** `generate_marketing_visual` appelle réellement le
> générateur d'images. `canva_automation_create` ne pilote rien : il renvoie une
> URL et un descriptif codés en dur.

### Outils & Capacités :
- **`generate_marketing_visual`** : Génération par IA d'images (Google Gemini Imagen 3) de bannières publicitaires, visuels réseaux sociaux et fiches produits aux formats Instagram Post (1:1), Story/Reels (9:16) et Facebook Banner (16:9).
- **`canva_automation_create`** : Pilotage automatisé de la plateforme Canva pour assembler des calques graphiques, intégrer des textes/boutons d'action et exporter les visuels haute résolution.

---

## 11. Gestion E-Commerce Chariow & Facebook Ads Manager

Ce module expose les opérations d'une boutique **Chariow** et d'un compte **Meta / Facebook Ads** (`server/tools/ecommerce_chariow.py`).

> **État : maquette.** Ce module est câblé, appelable et répond, mais les valeurs retournées sont codées en dur et ne proviennent d'aucune API réelle. Utilisable comme squelette d'intégration ; à ne pas prendre pour une source de vérité.

Concrètement : `chariow_manage_store` renvoie un chiffre d'affaires fixe (14 ventes,
245 000 FCFA) quel que soit l'état réel de la boutique, et `facebook_ads_manager`
un ROAS fictif sans qu'aucune campagne ne soit créée. Brancher les vraies API est
un chantier à part entière.

Ces deux outils figurent malgré tout dans `DEFAULT_DANGEROUS` de
`server/confirm.py` : le jour où ils seront réellement branchés, un budget
publicitaire sera engagé, et le garde-fou doit préexister.

### Outils & Capacités :
- **`chariow_manage_store`** : Lecture du chiffre d'affaires, suivi du taux de conversion, gestion du catalogue de produits et des commandes clients de votre boutique Chariow.
- **`facebook_ads_manager`** : Création et déploiement autonome de campagnes publicitaires Facebook Ads (gestion du budget quotidien, ciblage démographique/géographique UEMOA, calcul du ROAS et suivi des clics/conversions).

---

## 12. Producteur & Générateur de Vidéos IA Réalistes

Ce module décrit la production de vidéos promotionnelles (`server/tools/video_producer.py`).

> **État : maquette.** Ce module est câblé, appelable et répond, mais les valeurs retournées sont codées en dur et ne proviennent d'aucune API réelle. Utilisable comme squelette d'intégration ; à ne pas prendre pour une source de vérité.

Concrètement : `generate_ai_video` renvoie un chemin `.mp4` et une URL de
prévisualisation qui ne sont jamais écrits sur le disque. Aucune voix-off n'est
synthétisée, aucun montage n'est effectué.

Pour transcrire une vidéo existante — l'opération inverse, elle bien réelle —
voir le chapitre 18.

### Outils & Capacités :
- **`generate_ai_video`** : Production vidéo autonome incluant l'écriture du script, la génération de la voix-off synthétique (Kokoro TTS), l'animation des clips visuels IA et le sous-titrage automatique.
- **`create_video_ad_campaign`** : Génération de spots vidéo verticaux (9:16) prêts pour Instagram Reels, TikTok et YouTube Shorts pour mettre en valeur les offres Chariow.

---

## 13. Agent Testeur QA E2E d'Applications par Excellence

Ce module expose une interface de test de bout en bout pour les applications Web, Desktop et Mobile (`server/tools/app_qa_tester.py`).

> **État : maquette.** Ce module est câblé, appelable et répond, mais les valeurs retournées sont codées en dur et ne proviennent d'aucune API réelle. Utilisable comme squelette d'intégration ; à ne pas prendre pour une source de vérité.

Concrètement : `run_app_e2e_test` renvoie cinq étapes toujours `PASSED`, un score
de 98,5 % et zéro bug, **sans ouvrir ni solliciter l'application ciblée**. Un
rapport vert de ce module ne dit rien de l'état réel de votre logiciel.

### Outils & Capacités :
- **`run_app_e2e_test`** : Exécution de scénarios de test E2E automatisés (navigation, formulaires, clics, responsive, performance réseau et logs console) sur n'importe quelle application.
- **`generate_qa_bug_report`** : Capture visuelle des erreurs, analyse multimodale et rédaction de rapports d'audit QA complets avec préconisations de correctifs.

---

## 14. Deep Research Web Multi-Sources & Document Cloud

Moteur d'investigation récursive et d'intégration documentaire (`server/tools/deep_research.py`, `google_workspace.py`).

### Outils & Capacités :
- **`run_deep_research`** : Exploration récursive du Web, extraction du contenu des pages, croisement de sources et génération de synthèses documentaires structurées avec citations.
- **`google_drive_list` & `google_sheets_append`** : Consultation des fichiers Google Drive et insertion de lignes de données dans des tableurs Google Sheets.

---

## 15. Routines Automatiques, RPA Bureau & Multi-Agents

Système d'automatisation avancée des tâches et d'orchestration multi-agents (`server/tools/routine_tools.py`, `rpa_macro.py`, `server/multi_agent.py`).

### Outils & Capacités :
- **`create_routine` / `execute_routine`** : Planification de tâches récurrentes périodiques.
- **`add_macro_step` / `play_macro`** : Enregistreur et rejoueur de scénarios d'action physique sur le bureau Windows (clics, raccourcis, frappe).
- **`delegate_subagent_task`** : Orchestration de sous-agents spécialisés (`VeilleAgent`, `CoderAgent`, `ResearchAgent`).

---

## 16. Backtesting de Stratégies Financières & Alertes Multi-Canal

Outils de simulation de trading et de diffusion d'alertes instantanées (`server/trading/backtester.py`, `server/tools/alerts.py`).

### Outils & Capacités :
- **`run_strategy_backtest`** : Backtest de stratégies financières sur historique K-lines (Win Rate %, Profit Factor, Sharpe Ratio, Max Drawdown %).
- **`send_alert_notification`** : Diffusion d'alertes en temps réel sur Telegram Bot, Webhooks Discord et Email SMTP.

---

## 17. Cockpit 3D WebGL & Boîte de Réponse HUD Holographique

L'interface utilisateur s'enrichit d'une expérience visuelle futuriste et ergonomique (`frontend/src/components/cockpit/OrionResponseBox.tsx`).

### Innovations Interface :
- **`OrionResponseBox`** : Boîte de dialogue biseautée en verre blindé (Glassmorphism) avec bordure néon réactive selon l'état système (`ÉCOUTE`, `RÉFLEXION`, `TRANSMISSION`).
- **Formateur Markdown Intégré** : Restitution claire des réponses avec titres, listes à puces et texte en gras.
- **Défilement & Contrôles** : Zone de scroll interne (`max-h-[260px]`), bouton de copie rapide et bouton de fermeture `(X)`.
- **System Monitor** : Outils `get_system_metrics` et `list_running_processes` pour afficher la charge CPU/RAM en direct dans le cockpit.

---

## 18. Base de Connaissances Évolutive & Apprentissage Continu

Orion ingère des sources externes dans une mémoire vectorielle consultable, qui
grandit au fil du temps (`server/memory/knowledge.py`, `media_ingest.py`).

> **Ce que « apprendre » veut dire ici.** Orion range du contenu dans une base
> qu'il interroge au moment de répondre. Ses réponses s'améliorent parce qu'il
> retrouve davantage de matière — **pas parce que le modèle change**. Les poids
> vivent chez Anthropic et Google, figés côté fournisseur : aucun
> ré-entraînement, aucun fine-tuning n'est possible depuis cette machine. Le
> prompt système interdit explicitement à Orion de prétendre le contraire.

### Ingestion universelle (`learn_from_source`)

Un seul outil, qui reconnaît seul le type de ce qu'on lui donne :

| Source fournie | Traitement |
|---|---|
| Fichier (PDF, DOCX, TXT, MD, CSV, code) | extraction, découpage, vectorisation |
| Dossier | indexation de tous les fichiers reconnus |
| URL de page web | extraction du contenu utile (`article` / `main`), menus et pieds de page écartés |
| Lien vidéo | sous-titres publiés, sinon transcription de l'audio |
| Fichier audio/vidéo local | transcription Whisper |
| Texte brut | retenu tel quel |

Une source déjà apprise n'est pas réindexée sans `force` : la dupliquer
fausserait les recherches ultérieures.

### Les trois voies d'alimentation continue

- **Dossier surveillé** — tout document déposé dans `data/knowledge_inbox` est ingéré dans les deux minutes, puis **archivé dans `_traites`, jamais supprimé**. Réglé par `ORION_KNOWLEDGE_INBOX_WATCH` et `ORION_KNOWLEDGE_INBOX_INTERVAL`.
- **Veille programmée** — `ORION_LEARNING_TOPICS` liste des sujets ; chaque matin, Orion cherche sur le web via `learn_from_topic` et indexe ce qu'il trouve.
- **Apprentissage des échanges** — lorsqu'une conclusion durable ressort d'une conversation (une règle de gestion, un arbitrage tranché), Orion la retient avec `memory_remember`. Le prompt système lui interdit de retenir le bavardage ou ce qui n'est vrai qu'aujourd'hui.

### Restitution (`knowledge_teach`)

Rassemble les extraits pertinents **avec leurs sources** et laisse le modèle
composer la réponse — écrire la leçon dans le code Python la figerait. Si rien
n'a été appris sur le sujet, l'outil le dit et propose d'apprendre une source,
au lieu de laisser combler le vide par des généralités.

`knowledge_status` répond à « qu'as-tu appris, d'où, et quand ».

### Ingestion vidéo — précautions

Deux voies, de la moins chère à la plus coûteuse : sous-titres publiés (une
seconde, sans téléchargement), puis téléchargement de l'audio et transcription
Whisper (plusieurs minutes, plafonné à 90 minutes de média).

La seconde voie exige **ffmpeg**, binaire système absent de pip
(`winget install Gyan.FFmpeg`), et un redémarrage d'Orion pour qu'il voie le
nouveau `PATH`.

**YouTube refuse fréquemment l'accès programmatique anonyme** (`IpBlocked`,
`Sign in to confirm you're not a bot`). Fournir une session authentifiée passe
par `cookies_from_browser` — qui échoue sous Windows sur Chrome, Edge et Brave
depuis Chromium 127, leurs cookies étant chiffrés d'une façon que yt-dlp ne sait
pas déchiffrer — ou par `cookies_file`, un export `cookies.txt` que vous
maîtrisez. Voie de contournement la plus simple : télécharger la vidéo soi-même
et donner le fichier, ou le déposer dans le dossier surveillé.

---

## 19. Catalogue Exhaustif des Outils Natifs (141 outils)

Liste vérifiée par `tests/test_tools_registry.py` : tout handler sans schéma fait
échouer la suite, puisqu'il serait invisible pour le LLM.

### Base de Connaissances (`memory/knowledge.py`, `rag_tools.py`)
- `learn_from_source`, `learn_from_topic`, `learn_from_inbox`, `knowledge_teach`, `knowledge_status`.
- `memory_remember`, `memory_recall`, `memory_forget`, `memory_clear`, `memory_stats`, `memory_list`, `memory_index_file`, `memory_index_dir`.
- `vault_reindex_now`, `vault_reindex_status`, `journal_generate_daily`, `episodic_query`.

### Fichiers, Code & Système (`file_manager.py`, `code_runner.py`, `system_monitor.py`)
- `create_file`, `read_file`, `list_directory`, `delete_file`, `create_directory`, `move_file`.
- `run_shell_command`, `run_python_script`.
- `get_system_info`, `get_system_metrics`, `list_running_processes`.

### Bureau & RPA (`automation.py`, `windows_ctrl.py`, `rpa_macro.py`)
- `automation_status`, `screenshot`, `mouse_click`, `mouse_move`, `mouse_scroll`, `mouse_drag`, `mouse_position`, `keyboard_type`, `keyboard_key`, `keyboard_press`.
- `list_windows`, `focus_window`, `window_control`, `window_watch`, `screen_ocr`, `clipboard_get`, `clipboard_set`.
- `macro_record_start`, `macro_record_stop`, `macro_action_add`, `macro_play`, `macro_list`, `macro_delete`.
- `add_macro_step`, `list_macros`, `play_macro`, `delete_macro`.

### Création Visuelle & Marketing (`crea_design.py`, `image_gen.py`)
- `generate_marketing_visual`, `canva_automation_create`, `generate_image`.

### E-Commerce & Publicité (`ecommerce_chariow.py`)
- `chariow_manage_store`, `facebook_ads_manager`.

### Production Vidéo IA (`video_producer.py`)
- `generate_ai_video`, `create_video_ad_campaign`.

### Assurance Qualité & Tests (`app_qa_tester.py`)
- `run_app_e2e_test`, `generate_qa_bug_report`.

### Recherche Web & Document Cloud (`web_search.py`, `deep_research.py`, `google_workspace.py`)
- `web_search`, `fetch_url`, `run_deep_research`.
- `gmail_search`, `gmail_read_message`, `calendar_list_events`, `calendar_create_event`, `google_drive_list`, `google_sheets_append`.

### Analyse Financière, Trading & Backtest (`trading_tools.py`, `brvm_tools.py`, `kronos_tools.py`, `alerts.py`)
- `brvm_live_quote`, `brvm_market_refresh`, `brvm_stock_picker`, `brvm_stock_analysis`, `brvm_market_overview`, `brvm_income_portfolio`, `brvm_kronos_predict`.
- `kronos_predict_candles`, `kronos_model_status`, `trading_session_report`, `run_strategy_backtest`, `send_alert_notification`.

### Routines & Multi-Agents (`routine_tools.py`, `multi_agent.py`)
- `create_routine`, `list_routines`, `delete_routine`, `execute_routine`.
- `delegate_subagent_task`.

### Voix & Biométrie (`voice_tools.py`, `camera_vision.py`)
- `voice_dictate_obsidian`, `meeting_summarize`, `voice_flash_shortcut`.
- `camera_status`, `camera_snapshot`, `camera_look`, `camera_gesture`, `face_enroll`, `face_list`, `face_delete`, `vision_app_start`.

---

> **Note de Fin — Édition v3.1.** Ce manuel récapitule les 141 outils natifs d'Orion,
> et distingue ce qui repose sur des données réelles de ce qui reste à l'état de maquette.
>
> **Réel et vérifié** : automatisation système et bureau, marché BRVM (47 valeurs,
> 12 indices, historique quotidien), prédiction Kronos sur séances réelles, base de
> connaissances (fichiers, pages web, médias), recherche web, voix et vision, pont MCP.
>
> **Encore simulé** : Chariow, Facebook Ads, production vidéo IA, tests QA E2E, et
> l'assemblage Canva. Ces modules répondent mais renvoient des valeurs codées en dur ;
> les brancher sur leurs API respectives reste à faire.
>
> **Limite structurelle** : Orion n'apprend pas au sens du modèle. Il accumule une
> mémoire consultable ; ses poids ne changent pas.
