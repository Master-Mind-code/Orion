# Manuel Magistral des Capacités d'Orion — Édition Master

> **Version Système** : Orion v2.0 (Master-Mind Architecture)  
> **Statut Opérationnel** : Actif & Déployé  
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
10. [Catalogue Exhaustif des Outils Natifs (Sitemap System)](#10-catalogue-exhaustif-des-outils-natifs-sitemap-system)

---

## 1. Vue d'Ensemble & Philosophie de l'IA Autonome

**Orion** est un assistant IA personnel de classe souveraine et autonome, conçu pour fonctionner directement sur l'appareil de l'utilisateur. Contrairement aux agents conversationnels passifs, Orion est doté de capacités d'action directe : il interagit avec le système d'exploitation, manipule les fichiers, exécute des scripts, pilote les fenêtres graphiques, analyse les flux financiers internationaux et régionaux, et surveille les marchés en continu.

### Principes Fondeurs :
- **Survie du Capital & Discipline Absolue** : Rigueur d'exécution maximale. Aucun compromis sur la gestion du risque.
- **Proactivité Autonome** : Orion n'attend pas des instructions pas-à-pas ; il planifie, analyse et exécute les sous-tâches jusqu'à l'atteinte de l'objectif final.
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
   │ Tools Natifs System│   │ BRVM & Kronos      │
   │ (File/Automation)  │   │ Neural Engine      │
   └────────────────────┘   └────────────────────┘
```

### Composants Clés :
1. **Orchestrateur Central (`server/orchestrator.py`)** : Reçoit le flux de requêtes, formule les plans d'actions, effectue le routage des outils natifs et gère les boucles d'itération (jusqu'à 25 itérations autonomes par demande).
2. **Fournisseurs de LLM Interchangeables (`server/providers/`)** : Bascule transparente entre Anthropic Claude (Haiku, Sonnet, Opus) et Google Gemini.
3. **Cockpit 3D & Capsule Flottante (`desktop/`, `frontend/`)** : Interface futuriste WebGL en 4 modes (Voix, Trading, Bureau, Système) avec réacteur réactif et raccourci système global **Ctrl+Alt+O**.
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

```
                           ┌───────────────────────────┐
                           │ Base Financière BRVM      │
                           │ (data/brvm_stocks.json)   │
                           └─────────────┬─────────────┘
                                         │
                                         ▼
                           ┌───────────────────────────┐
                           │   BRVMEngine (Scoring)    │
                           │ PER + Yield + ROE + Tech  │
                           └─────────────┬─────────────┘
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 ▼                       ▼                       ▼
    ┌────────────────────────┐ ┌───────────────────┐ ┌──────────────────────┐
    │ brvm_income_portfolio  │ │ brvm_stock_picker │ │ brvm_stock_analysis  │
    │ (Target 150k FCFA/mois)│ │ (Profils d'achat) │ │ (Fiche d'action)     │
    └────────────────────────┘ └───────────────────┘ └──────────────────────┘
```

### Capacités Majeures BRVM :
- **Base de Données Régionale Enrichie (`data/brvm_stocks.json`)** : Données fondamentales et financières complètes pour l'ensemble de la cote (Sonatel, SGBCI, Orange CI, Coris Bank, Palmci, Total CI, Sodeci, CIE, Solibra, Onatel BF, etc.).
- **Calcul du Orion Score BRVM (0-100)** : Évaluation croisée du rendement dividende (Yield %), de la sous-évaluation (PER), de la rentabilité des capitaux (ROE %) et du momentum de prix.
- **Portefeuille de Revenu Cible (150.000 FCFA / mois)** : `brvm_income_portfolio` calcule le nombre exact d'actions à acheter parmi les champions régionaux pour générer 1.800.000 FCFA / an de dividendes récurrents (ex: allocation équilibrée Palmci + SGBCI + Ecobank + Coris Bank + Onatel BF pour un rendement annuel net moyen de **10.16%**).
- **Sélecteur d'Actions par Profil (`brvm_stock_picker`)** : Classement instantané selon 4 stratégies : `dividend` (rendement passif), `growth` (croissance), `value` (décote), `balanced` (équilibré).

---

## 5. Moteur Neuronal Fondateur Kronos PyTorch

Orion intègre le modèle de fondation neuronal **Kronos PyTorch (NeoQuasar/Kronos-mini)**, spécialisé dans la prédiction de séries temporelles K-lines et l'analyse quantique de marché.

### Inférence & Algorithmes :
- **Tokenizer BSQuantizer + Transformer Autorégressif** : Discrétise les variations de prix OHLCV et de volumes pour projeter les trajectoires futures.
- **Inférence Multi-Marchés & BRVM (`brvm_kronos_predict`)** : Génère des simulations de bougies K-lines pour prédire le cours cible en FCFA des actions africaines et la probabilité de tendance (confiance %).
- **Simulations Monte-Carlo (`KronosEngine.run_monte_carlo_simulations`)** : Génère 10 à 100 trajectoires stochastiques pour déterminer l'enveloppe de prix (percentiles 10%, 50%, 90%).

---

## 6. Pilotage Physique du Bureau & Vision Synthétique

Orion peut interagir physiquement avec le système d'exploitation comme le ferait un opérateur humain.

### Modules d'Automation (`server/tools/automation.py`, `windows_ctrl.py`) :
- **Souris** : Déplacement absolu/relatif, clic gauche/droit/double, glisser-déposer (*drag & drop*), molette.
- **Clavier** : Saisie de texte avec gestion du presse-papier pour préserver les accents français, combinaisons de touches (`Ctrl+C`, `Ctrl+V`, `Alt+Tab`).
- **Fenêtres Windows** : Lister les fenêtres actives, basculer au premier plan, réduire, agrandir, déplacer, redimensionner et fermer proprement.
- **Vision par Découpage de Région (`screenshot`)** : Capture de l'écran ou de sous-régions précises à l'échelle 1.0 pour viser des éléments graphiques au pixel près.
- **Analyse d'Image par IA (`analyze_image`)** : Utilisation de modèles de vision multimodaux pour lire le texte à l'écran, analyser un schéma ou diagnostiquer une erreur système.

---

## 7. Service Vocal Immersif & Biométrie Locale

Orion propose une expérience vocale naturelle sans dépendre d'un service cloud tiers pour le traitement de la parole.

### Pipeline Vocal (`server/voice/`, `voice/`) :
- **Reconnaissance Vocale (STT)** : OpenAI Whisper local.
- **Synthèse Vocale Naturelle (TTS)** : Modèle Kokoro TTS à haut débit.
- **Détection d'Activité Vocale (VAD)** : Filtrage automatique du bruit et des silences.
- **Wake Word ("Hey Orion")** : Écoute continue en arrière-plan.

### Biométrie & Vision par Caméra (`server/tools/camera_vision.py`) :
- **Reconnaissance Faciale Locale (`face_enroll`, `face_list`, `face_delete`)** : Base de données biométrique 100% locale stockée dans `data/known_faces/`.
- **Détection de Gestes (`camera_gesture`)** : Lecture des gestes de la main (poing, main ouverte, pouce levé, nombre de doigts).
- **Applications de Surveillance (`vision_app_start`)** : Somnolence au volant, intrusion, comptage de franchissement de ligne.

---

## 8. Pont Inter-Processus MCP (TradingView & MetaTrader 5)

Orion implémente le protocole universel **Model Context Protocol (MCP)** via un bridge stdio générique (`server/mcp_bridge/`).

### Intégration Native des Serveurs MCP :
- **TradingView (22 Outils MCP)** : Contrôle direct de l'application TradingView Desktop via Chrome DevTools Protocol (CDP). Lecture des graphiques, dessin de lignes de tendance, création d'alertes de prix.
- **MetaTrader 5 (10 Outils MCP)** : Connexion directe au terminal MT5. Lecture des données de tick, cotations temps réel (`mt5_quote`), positions ouvertes (`mt5_positions_get`), envoi d'ordres de marché avec pré-validation obligatoire (`mt5_order_send`).

---

## 9. Architecture de Sécurité, Audit & Mode Panic

Parce qu'Orion possède des droits d'action physique et financière, la sécurité est assurée par 8 couches superposées.

| Couche | Description & Fonctionnement |
|---|---|
| **`ORION_SECRET_TOKEN`** | Jetons d'authentification obligatoires pour chaque WebSocket et API HTTP. |
| **`ORION_CONFIRM_PASSWORD`** | Mot de passe requis avant l'exécution de tout outil destructif ou sensible. |
| **`ORION_AUTOMATION_ENABLED`** | Interrupteur matériel autorisant ou bloquant le contrôle physique de la souris/clavier. |
| **`ORION_TRADING_EXECUTION_ENABLED`** | Interrupteur indépendant dédié à l'exécution d'ordres réels en bourse. |
| **Mode Panic (`POST /api/panic`)** | Verrouillage instantané de tous les outils du système en 1 clic. |
| **Fail-Safe Souris** | Placer le curseur dans le coin supérieur gauche de l'écran stoppe immédiatement l'automation. |
| **Journal d'Audit (`data/audit.db`)** | Traçabilité SQLite inaltérable de chaque appel d'outil (horodatage, arguments, succès/échec). |
| **Sauvegardes Automatiques (`safety_backup.py`)** | Backup automatique avant toute suppression ou modification de fichier important. |

---

## 10. Catalogue Exhaustif des Outils Natifs (Sitemap System)

### Fichiers & Système (`file_manager.py`, `code_runner.py`)
- `create_file` : Crée un fichier avec contenu textuel.
- `read_file` : Lit et retourne le contenu d'un fichier.
- `list_directory` : Liste le contenu d'un dossier.
- `delete_file` : Supprime un fichier ou dossier (avec backup automatique).
- `create_directory` : Crée un dossier et ses parents.
- `move_file` : Déplace ou nomme un fichier.
- `execute_command` : Exécute une commande Shell/PowerShell.
- `run_python_script` : Exécute un script Python.

### Bureau & Automation (`automation.py`, `windows_ctrl.py`)
- `automation_status` : Vérifie l'état de l'interrupteur et la géométrie des écrans.
- `screenshot` : Prends une capture d'écran globale ou ciblée par région.
- `mouse_click` / `mouse_move` / `mouse_scroll` : Contrôle physiquement la souris.
- `keyboard_type` / `keyboard_key` : Saisie clavier et combinaisons.
- `list_windows` / `activate_window` / `window_control` : Gestion complète des fenêtres.
- `clipboard_get` / `clipboard_set` : Lecture et écriture dans le presse-papier.

### Analyse Financière & Trading (`trading_tools.py`, `brvm_tools.py`, `kronos_tools.py`)
- `brvm_stock_picker` : Sélecteur d'actions IA sur la BRVM par profil d'investissement.
- `brvm_stock_analysis` : Analyse complète (Fondamentale + Technique + Kronos) d'un titre BRVM.
- `brvm_market_overview` : Vue globale du marché régional UEMOA (BRVM Composite).
- `brvm_income_portfolio` : Générateur de portefeuille de revenus cibles (ex: 150.000 FCFA/mois).
- `brvm_kronos_predict` : Projection neurale K-lines sur une action BRVM.
- `kronos_predict_candles` : Inférence neurale Kronos sur n'importe quel actif.
- `kronos_model_status` : État et GPU du modèle PyTorch Kronos.
- `trading_session_report` : Rapport de session de trading avec push Telegram.

### Caméra & Biométrie (`camera_vision.py`)
- `camera_status` / `camera_snapshot` / `camera_look` : Prise de vue et détection d'objets.
- `camera_gesture` : Reconnaissance des gestes et comptage des doigts.
- `face_enroll` / `face_list` / `face_delete` : Base biométrique faciale locale.
- `vision_app_start` / `vision_app_stop` : Lancement d'applications de vision en temps réel.

### Mémoire & Cockpit (`rag_tools.py`, `cockpit.py`)
- `memory_remember` / `memory_recall` / `memory_forget` : Mémoire long terme vectorielle RAG.
- `cockpit_set_mode` / `cockpit_modes` : Bascule visuelle des modes du cockpit (Voice, Trading, Desktop, System).

---

> **Note de Fin** : Ce Manuel Magistral constitue le guide de référence complet des capacités de l'écosystème Orion. Il atteste de la pleine opérationnalité des systèmes d'automatisation, de trading haute performance et d'analyse financière sur les marchés internationaux et la BRVM.
