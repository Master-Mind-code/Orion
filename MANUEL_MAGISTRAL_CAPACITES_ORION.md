# Manuel Magistral des Capacités d'Orion — Édition Master v3.0

> **Version Système** : Orion v3.0 (Master-Mind Architecture)  
> **Statut Opérationnel** : Actif & Déployé (133 Outils Natifs)  
> **Dernière Mise à Jour** : 2026  
> **Auteur & Conception** : Équipe Advanced Agentic Coding

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
18. [Catalogue Exhaustif des Outils Natifs (Sitemap System)](#18-catalogue-exhaustif-des-outils-natifs-sitemap-system)

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
   │ 133 Tools Natifs   │   │ BRVM & Kronos      │
   │ (File/QA/Video/Ads)│   │ Neural Engine      │
   └────────────────────┘   └────────────────────┘
```

### Composants Clés :
1. **Orchestrateur Central (`server/orchestrator.py`)** : Reçoit le flux de requêtes, formule les plans d'actions, effectue le routage des 133 outils natifs et gère les boucles d'itération (jusqu'à 25 itérations autonomes par demande).
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

Orion est équipé d'un moteur expert dédié à la **BRVM (Bourse Régionale des Valeurs Mobilières de l'UEMOA - Abidjan)**.

### Capacités Majeures BRVM :
- **Base de Données Régionale Enrichie (`data/brvm_stocks.json`)** : Données fondamentales et financières complètes pour l'ensemble de la cote (Sonatel, SGBCI, Orange CI, Coris Bank, Palmci, Total CI, Sodeci, CIE, Solibra, Onatel BF, etc.).
- **Calcul du Orion Score BRVM (0-100)** : Évaluation croisée du rendement dividende (Yield %), de la sous-évaluation (PER), de la rentabilité des capitaux (ROE %) et du momentum de prix.
- **Portefeuille de Revenu Cible (150.000 FCFA / mois)** : `brvm_income_portfolio` calcule le nombre exact d'actions à acheter parmi les champions régionaux pour générer 1.800.000 FCFA / an de dividendes récurrents.
- **Sélecteur d'Actions par Profil (`brvm_stock_picker`)** : Classement instantané selon 4 stratégies : `dividend`, `growth`, `value`, `balanced`.

---

## 5. Moteur Neuronal Fondateur Kronos PyTorch

Orion intègre le modèle de fondation neuronal **Kronos PyTorch (NeoQuasar/Kronos-mini)**, spécialisé dans la prédiction de séries temporelles K-lines et l'analyse quantique de marché.

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

Orion intègre un studio complet de génération de visuels publicitaires et de créations marketing (`server/tools/crea_design.py`).

### Outils & Capacités :
- **`generate_marketing_visual`** : Génération par IA d'images (Google Gemini Imagen 3) de bannières publicitaires, visuels réseaux sociaux et fiches produits aux formats Instagram Post (1:1), Story/Reels (9:16) et Facebook Banner (16:9).
- **`canva_automation_create`** : Pilotage automatisé de la plateforme Canva pour assembler des calques graphiques, intégrer des textes/boutons d'action et exporter les visuels haute résolution.

---

## 11. Gestion E-Commerce Chariow & Facebook Ads Manager

Orion pilote directement la boutique en ligne **Chariow** et gère l'écosystème publicitaire **Meta / Facebook Ads** (`server/tools/ecommerce_chariow.py`).

### Outils & Capacités :
- **`chariow_manage_store`** : Lecture du chiffre d'affaires, suivi du taux de conversion, gestion du catalogue de produits et des commandes clients de votre boutique Chariow.
- **`facebook_ads_manager`** : Création et déploiement autonome de campagnes publicitaires Facebook Ads (gestion du budget quotidien, ciblage démographique/géographique UEMOA, calcul du ROAS et suivi des clics/conversions).

---

## 12. Producteur & Générateur de Vidéos IA Réalistes

Orion est capable de concevoir, scripter et assembler des vidéos promotionnelles IA réalistes (`server/tools/video_producer.py`).

### Outils & Capacités :
- **`generate_ai_video`** : Production vidéo autonome incluant l'écriture du script, la génération de la voix-off synthétique (Kokoro TTS), l'animation des clips visuels IA et le sous-titrage automatique.
- **`create_video_ad_campaign`** : Génération de spots vidéo verticaux (9:16) prêts pour Instagram Reels, TikTok et YouTube Shorts pour mettre en valeur les offres Chariow.

---

## 13. Agent Testeur QA E2E d'Applications par Excellence

Orion devient l'agent d'assurance qualité **QA par excellence** pour tester de bout en bout l'ensemble de vos applications Web, Desktop et Mobile (`server/tools/app_qa_tester.py`).

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

## 18. Catalogue Exhaustif des Outils Natifs (133 Outils System)

### Fichiers, Code & Système (`file_manager.py`, `code_runner.py`, `system_monitor.py`)
- `create_file`, `read_file`, `list_directory`, `delete_file`, `create_directory`, `move_file`.
- `execute_command`, `run_python_script`.
- `get_system_metrics`, `list_running_processes`.

### Bureau & RPA (`automation.py`, `windows_ctrl.py`, `rpa_macro.py`)
- `automation_status`, `screenshot`, `mouse_click`, `mouse_move`, `mouse_scroll`, `keyboard_type`, `keyboard_key`.
- `list_windows`, `activate_window`, `window_control`, `clipboard_get`, `clipboard_set`.
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
- `brvm_stock_picker`, `brvm_stock_analysis`, `brvm_market_overview`, `brvm_income_portfolio`, `brvm_kronos_predict`.
- `kronos_predict_candles`, `kronos_model_status`, `trading_session_report`, `run_strategy_backtest`, `send_alert_notification`.

### Routines & Multi-Agents (`routine_tools.py`, `multi_agent.py`)
- `create_routine`, `list_routines`, `delete_routine`, `execute_routine`.
- `delegate_subagent_task`.

### Voix & Biométrie (`voice_tools.py`, `camera_vision.py`)
- `voice_dictate_obsidian`, `meeting_summarize`, `voice_flash_shortcut`.
- `camera_status`, `camera_snapshot`, `camera_look`, `camera_gesture`, `face_enroll`, `face_list`, `face_delete`, `vision_app_start`.

---

> **Note de Fin** : Ce Manuel Magistral Édition v3.0 récapitule l'intégralité des 133 capacités d'Orion. Orion constitue désormais un système autonome complet couvrant l'automatisation système, la finance/trading, le marketing e-commerce Chariow, la création multimédia IA et le test QA d'applications.
