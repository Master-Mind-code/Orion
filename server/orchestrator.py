"""
Orion — Orchestrateur Central
Cerveau de l'assistant : reçoit une requête, appelle un LLM (Anthropic ou Gemini),
exécute les tools, retourne la réponse finale.

Provider sélectionné via ORION_PROVIDER (défaut: anthropic).
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from branding import sync_env_aliases

# Charge .env depuis la racine du projet AVANT d'instancier les clients LLM
# (sinon les variables ne sont pas encore définies quand main.py importe ce module).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
sync_env_aliases()

from server.tools import ALL_HANDLERS
from server import mcp_bridge
from server.providers import get_provider, ProviderResponse
from server import confirm
from server import audit
from server import safety_backup
from server import rate_limit
from server import panic

# Provider initialisé en lazy : on ne crée le client qu'au premier appel,
# pour permettre à l'orchestrateur de s'importer même si la clé du provider sélectionné
# n'est pas encore définie (utile pour les workers qui n'ont pas besoin du LLM).
_provider = None

def _get_provider():
    global _provider
    if _provider is None:
        _provider = get_provider()
        print(f"[orchestrator] Provider actif : {_provider.name} ({_provider.model})")
    return _provider

# ─────────────────────────────────────────────────────────────────
# Définition des tools disponibles pour Claude
# ─────────────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "create_file",
        "description": "Crée un fichier avec un contenu donné sur l'appareil.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin complet du fichier (ex: /home/user/notes.txt)"},
                "content": {"type": "string", "description": "Contenu à écrire dans le fichier"},
                "overwrite": {"type": "boolean", "description": "Écraser si le fichier existe déjà", "default": False},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Lit et retourne le contenu d'un fichier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin du fichier à lire"},
                "max_chars": {"type": "integer", "description": "Nombre max de caractères à retourner", "default": 8000},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_directory",
        "description": "Liste le contenu d'un dossier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin du dossier", "default": "."},
                "show_hidden": {"type": "boolean", "description": "Afficher les fichiers cachés", "default": False},
            },
        },
    },
    {
        "name": "delete_file",
        "description": "Supprime un fichier ou dossier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin du fichier/dossier à supprimer"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_directory",
        "description": "Crée un dossier (et ses parents si nécessaire).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin du dossier à créer"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "move_file",
        "description": "Déplace ou renomme un fichier/dossier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "src": {"type": "string", "description": "Chemin source"},
                "dst": {"type": "string", "description": "Chemin destination"},
            },
            "required": ["src", "dst"],
        },
    },
    {
        "name": "run_shell_command",
        "description": "Exécute une commande shell sur l'appareil (bash, cmd, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "La commande shell à exécuter"},
                "cwd": {"type": "string", "description": "Dossier de travail (optionnel)"},
                "timeout": {"type": "integer", "description": "Timeout en secondes", "default": 30},
            },
            "required": ["command"],
        },
    },
    {
        "name": "run_python_script",
        "description": "Exécute du code Python directement.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code Python à exécuter"},
                "timeout": {"type": "integer", "description": "Timeout en secondes", "default": 30},
            },
            "required": ["code"],
        },
    },
    {
        "name": "get_system_info",
        "description": "Retourne les informations système (OS, Python, home directory, etc.).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "web_search",
        "description": "Effectue une recherche sur le web et retourne les résultats.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "La requête de recherche"},
                "max_results": {"type": "integer", "description": "Nombre max de résultats", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": "Récupère le contenu texte d'une URL web.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "L'URL à récupérer"},
                "max_chars": {"type": "integer", "description": "Nombre max de caractères", "default": 5000},
            },
            "required": ["url"],
        },
    },
    {
        "name": "open_app",
        "description": "Ouvre une application ou un logiciel sur l'appareil.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Nom de l'application à ouvrir (ex: firefox, code, vlc)"},
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "open_url_in_browser",
        "description": "Ouvre une URL dans le navigateur par défaut.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL à ouvrir"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "list_running_processes",
        "description": "Liste les processus/applications en cours d'exécution.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_connected_devices",
        "description": "Liste les appareils (workers) actuellement connectés au serveur, "
                       "avec leur device_id et leur OS. À utiliser AVANT d'exécuter un tool "
                       "sur un autre appareil pour connaître les target_device disponibles.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "gmail_search",
        "description": "Cherche des emails dans la boîte Gmail de l'utilisateur. "
                       "Utilise la syntaxe Gmail standard pour la query "
                       "(ex: 'is:unread', 'from:boss@example.com', 'subject:facture'). "
                       "Retourne id, expéditeur, sujet, date, snippet et statut unread.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query Gmail (ex: 'is:unread newer_than:2d')", "default": ""},
                "max_results": {"type": "integer", "description": "Nombre max d'emails (1-50)", "default": 10},
            },
        },
    },
    {
        "name": "gmail_read_message",
        "description": "Lit le contenu complet d'un email Gmail (corps texte, headers).",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "ID Gmail du message (obtenu via gmail_search)"},
                "max_chars": {"type": "integer", "description": "Tronque le corps à N caractères", "default": 8000},
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "calendar_list_events",
        "description": "Liste les événements à venir dans Google Calendar. "
                       "Par défaut : 10 événements sur les 7 prochains jours.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Nombre max d'événements (1-50)", "default": 10},
                "days_ahead": {"type": "integer", "description": "Fenêtre de jours à venir", "default": 7},
                "calendar_id": {"type": "string", "description": "ID du calendrier (défaut: 'primary')", "default": "primary"},
            },
        },
    },
    {
        "name": "calendar_create_event",
        "description": "Crée un événement dans Google Calendar. Les dates doivent être en ISO 8601 "
                       "(ex: '2026-05-15T14:00:00+02:00'). Utiliser 'YYYY-MM-DD' pour journée entière.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Titre de l'événement"},
                "start": {"type": "string", "description": "Début ISO 8601 ou YYYY-MM-DD"},
                "end": {"type": "string", "description": "Fin ISO 8601 ou YYYY-MM-DD"},
                "description": {"type": "string", "description": "Description (optionnel)"},
                "location": {"type": "string", "description": "Lieu (optionnel)"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Liste d'emails des participants (optionnel)",
                },
                "calendar_id": {"type": "string", "description": "ID du calendrier (défaut: 'primary')", "default": "primary"},
            },
            "required": ["summary", "start", "end"],
        },
    },
    # ─── Notifications système ────────────────────────────────
    {
        "name": "notify",
        "description": "Affiche une notification système (toast Windows / libnotify Linux / osascript macOS).",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titre de la notification"},
                "message": {"type": "string", "description": "Corps du message"},
                "duration": {"type": "string", "description": "short | long (Windows uniquement)", "default": "short"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "notify_telegram",
        "description": "Envoie une notification mobile via Telegram (message texte et/ou photo). "
                       "Permet d'envoyer des alertes mobiles pour tout Orion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Texte ou légende du message"},
                "photo_path": {"type": "string", "description": "Chemin optionnel d'une photo/image à joindre"},
            },
            "required": ["message"],
        },
    },
    # ─── Capture d'écran ──────────────────────────────────────
    {
        "name": "screenshot",
        "description": "Capture d'écran. Sans région : tout l'écran. Sauvegardé en PNG.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin du fichier de sortie (auto si vide)"},
                "monitor": {"type": "integer", "description": "0=tous, 1+=écran spécifique", "default": 0},
                "region": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                    },
                    "description": "Région à capturer (optionnel)",
                },
                "return_base64": {"type": "boolean", "description": "Inclure l'image en base64 dans la réponse", "default": False},
                "max_width": {
                    "type": "integer",
                    "description": "Réduit l'image au-delà de cette largeur. La réponse contient alors "
                                   "'scale' et 'coordinate_hint' : les coordonnées à passer aux tools "
                                   "souris restent celles du BUREAU, pas celles de l'image réduite.",
                },
            },
        },
    },
    {
        "name": "list_monitors",
        "description": "Liste les écrans connectés (résolution, position).",
        "input_schema": {"type": "object", "properties": {}},
    },
    # ─── Documents ────────────────────────────────────────────
    {
        "name": "read_pdf",
        "description": "Extrait le texte d'un fichier PDF (texte natif uniquement, pas d'OCR).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin du PDF"},
                "max_chars": {"type": "integer", "description": "Tronquer à N caractères", "default": 8000},
                "pages": {"type": "string", "description": "Range optionnel : '1-5' ou '3'"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_docx",
        "description": "Extrait le texte d'un fichier Word (.docx). Inclut les tableaux.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin du .docx"},
                "max_chars": {"type": "integer", "description": "Tronquer à N caractères", "default": 8000},
            },
            "required": ["path"],
        },
    },
    # ─── Automation souris/clavier ────────────────────────────
    {
        "name": "mouse_position",
        "description": "Retourne la position actuelle de la souris (lecture, toujours autorisée).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "mouse_move",
        "description": "Déplace la souris vers (x, y). Nécessite ORION_AUTOMATION_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "duration": {"type": "number", "description": "Durée du mouvement en secondes", "default": 0.2},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "mouse_click",
        "description": "Click souris. Sans coordonnées : à la position actuelle. Nécessite ORION_AUTOMATION_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "button": {"type": "string", "description": "left | right | middle", "default": "left"},
                "clicks": {"type": "integer", "default": 1},
            },
        },
    },
    {
        "name": "keyboard_type",
        "description": "Tape du texte au clavier. Nécessite ORION_AUTOMATION_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "interval": {"type": "number", "description": "Délai entre chaque caractère", "default": 0.02},
            },
            "required": ["text"],
        },
    },
    {
        "name": "keyboard_press",
        "description": "Appuie sur une touche ou une combinaison. "
                       "Touche unique : 'enter', 'esc', 'f5'. Hotkey : ['ctrl', 'c'] = Ctrl+C. "
                       "Nécessite ORION_AUTOMATION_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keys": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ],
                    "description": "'enter' OU ['ctrl','c']",
                },
            },
            "required": ["keys"],
        },
    },
    {
        "name": "keyboard_key",
        "description": "Combinaison de touches sous forme de texte, plus pratique que keyboard_press. "
                       "Ex : 'enter', 'ctrl+c', 'ctrl+shift+n', 'alt+tab', 'win+d'. "
                       "Plusieurs appuis successifs séparés par des espaces : 'ctrl+a ctrl+c'. "
                       "Nécessite ORION_AUTOMATION_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keys": {"type": "string", "description": "'ctrl+c' ou 'ctrl+a ctrl+c'"},
            },
            "required": ["keys"],
        },
    },
    {
        "name": "automation_status",
        "description": "État de l'interrupteur d'automation, géométrie des écrans (bureau virtuel "
                       "et moniteurs) et position de la souris. À appeler AVANT toute séquence de "
                       "contrôle du bureau pour connaître les bornes de coordonnées valides.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "mouse_drag",
        "description": "Glisser-déposer de (from_x, from_y) vers (to_x, to_y) : sélection, "
                       "déplacement d'icône, redimensionnement. Nécessite ORION_AUTOMATION_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_x": {"type": "integer"},
                "from_y": {"type": "integer"},
                "to_x": {"type": "integer"},
                "to_y": {"type": "integer"},
                "duration": {"type": "number", "description": "Durée du glissement en secondes", "default": 0.6},
                "button": {"type": "string", "description": "left | right | middle", "default": "left"},
            },
            "required": ["from_x", "from_y", "to_x", "to_y"],
        },
    },
    {
        "name": "mouse_scroll",
        "description": "Molette à la position donnée (ou position actuelle si x/y omis). "
                       "amount = nombre de crans, 3 crans ≈ un tiers d'écran. "
                       "Nécessite ORION_AUTOMATION_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "amount": {"type": "integer", "default": 5},
                "direction": {"type": "string", "description": "up | down | left | right", "default": "down"},
            },
        },
    },
    # ─── Presse-papier ────────────────────────────────────────
    {
        "name": "clipboard_get",
        "description": "Lit le contenu texte du presse-papier (lecture, toujours autorisée).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "clipboard_set",
        "description": "Place du texte dans le presse-papier. Combiné à keyboard_key('ctrl+v'), "
                       "c'est la façon fiable de saisir des accents ou un texte long — bien plus "
                       "sûr que keyboard_type. Nécessite ORION_AUTOMATION_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    # ─── Fenêtres du bureau ───────────────────────────────────
    {
        "name": "list_windows",
        "description": "Liste les fenêtres ouvertes avec titre, position, taille et état "
                       "(minimized/maximized/active). Lecture seule, toujours autorisée. "
                       "Une fenêtre réduite est rapportée en 237x39 @ (-32000,-32000) : c'est la "
                       "convention Windows, passer par focus_window pour agir dessus.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "focus_window",
        "description": "Met au premier plan la première fenêtre dont le titre contient le texte "
                       "donné (restaure si elle est réduite). Nécessite ORION_AUTOMATION_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title_contains": {"type": "string", "description": "Fragment du titre, insensible à la casse"},
            },
            "required": ["title_contains"],
        },
    },
    {
        "name": "window_control",
        "description": "Agit sur une fenêtre : minimize, maximize, restore, close, move (x,y), "
                       "resize (width,height). 'close' peut faire perdre du travail non enregistré. "
                       "Nécessite ORION_AUTOMATION_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title_contains": {"type": "string"},
                "action": {"type": "string",
                           "description": "minimize | maximize | restore | close | move | resize"},
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
            },
            "required": ["title_contains", "action"],
        },
    },
    # ─── Génération d'images ──────────────────────────────────
    {
        "name": "generate_image",
        "description": "Génère une image depuis un prompt texte via Google Gemini Imagen. "
                       "Sauvegardée en PNG dans data/images/. Nécessite GEMINI_API_KEY.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Description de l'image à générer"},
                "output_path": {"type": "string", "description": "Chemin du fichier de sortie (auto si vide)"},
                "aspect_ratio": {"type": "string", "description": "1:1 | 3:4 | 4:3 | 9:16 | 16:9", "default": "1:1"},
                "n": {"type": "integer", "description": "Nombre d'images (1-4)", "default": 1},
                "model": {"type": "string", "description": "imagen-3.0-fast-generate-001 (défaut) ou imagen-3.0-generate-002"},
            },
            "required": ["prompt"],
        },
    },
    # ─── Mémoire long terme RAG ───────────────────────────────
    {
        "name": "memory_remember",
        "description": "Mémorise un fait, une note ou une préférence dans la mémoire long terme vectorielle. "
                       "À utiliser pour 'retiens que X', 'note que Y'. Recherchable ensuite par similarité.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Le fait à mémoriser (1 phrase ou 1 paragraphe)"},
                "source": {"type": "string", "description": "Origine ('user', 'chat', 'note')", "default": "manual"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags optionnels"},
                "namespace": {"type": "string", "description": "Espace mémoire séparé", "default": "default"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "memory_recall",
        "description": "Recherche dans la mémoire long terme les souvenirs proches sémantiquement de la query. "
                       "Utilise systématiquement avant de répondre à une question personnelle de l'utilisateur.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Question ou mots-clés"},
                "top_k": {"type": "integer", "description": "Nombre de résultats", "default": 5},
                "min_score": {"type": "number", "description": "Score cosinus min [0..1]", "default": 0.25},
                "namespace": {"type": "string", "description": "Espace mémoire à interroger", "default": "default"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_forget",
        "description": "Supprime un souvenir par son ID (obtenu via memory_recall ou memory_list).",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "namespace": {"type": "string", "default": "default"},
            },
            "required": ["item_id"],
        },
    },
    {
        "name": "memory_clear",
        "description": "Vide entièrement un namespace de mémoire (DESTRUCTIF, demander confirmation).",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "default": "default"},
                "confirm": {"type": "boolean", "description": "Doit être true pour exécuter", "default": False},
            },
        },
    },
    {
        "name": "memory_stats",
        "description": "Compteurs mémoire : nombre d'entrées par namespace, par source.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace spécifique (sinon tous)"},
            },
        },
    },
    {
        "name": "memory_list",
        "description": "Liste les N derniers souvenirs d'un namespace (debug ou exploration).",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "default": "default"},
                "limit": {"type": "integer", "default": 50},
                "source": {"type": "string", "description": "Filtre optionnel sur source"},
            },
        },
    },
    {
        "name": "memory_index_file",
        "description": "Indexe le contenu d'un fichier (PDF, DOCX, TXT, MD, code) dans la mémoire vectorielle. "
                       "Découpe automatique en chunks de ~800 caractères.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin du fichier"},
                "namespace": {"type": "string", "default": "default"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "chunk_chars": {"type": "integer", "default": 800},
            },
            "required": ["path"],
        },
    },
    {
        "name": "memory_index_dir",
        "description": "Indexe récursivement un dossier dans la mémoire vectorielle. "
                       "Par défaut : pdf, docx, txt, md, py, js, ts, json, yml.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin du dossier"},
                "namespace": {"type": "string", "default": "default"},
                "extensions": {"type": "array", "items": {"type": "string"}, "description": "Extensions à inclure (sans le point)"},
                "recursive": {"type": "boolean", "default": True},
                "max_files": {"type": "integer", "default": 100},
            },
            "required": ["path"],
        },
    },
    # ─── Tools mobiles (worker Termux/Android uniquement) ─────
    {
        "name": "termux_battery",
        "description": "État de la batterie du téléphone (worker Termux). Utiliser target_device.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "termux_location",
        "description": "Position GPS du téléphone (worker Termux).",
        "input_schema": {
            "type": "object",
            "properties": {
                "provider": {"type": "string", "description": "network | gps | passive", "default": "network"},
            },
        },
    },
    {
        "name": "termux_send_sms",
        "description": "Envoie un SMS depuis le téléphone (worker Termux).",
        "input_schema": {
            "type": "object",
            "properties": {
                "number": {"type": "string", "description": "+33... ou 06..."},
                "text": {"type": "string"},
            },
            "required": ["number", "text"],
        },
    },
    {
        "name": "termux_list_sms",
        "description": "Liste les derniers SMS reçus (worker Termux).",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "termux_contacts",
        "description": "Liste les contacts du téléphone (worker Termux).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "termux_call",
        "description": "Lance un appel téléphonique (worker Termux).",
        "input_schema": {
            "type": "object",
            "properties": {"number": {"type": "string"}},
            "required": ["number"],
        },
    },
    {
        "name": "termux_vibrate",
        "description": "Fait vibrer le téléphone (worker Termux).",
        "input_schema": {
            "type": "object",
            "properties": {
                "duration_ms": {"type": "integer", "default": 500},
            },
        },
    },
    {
        "name": "termux_notification",
        "description": "Notification dans la barre de notif Android (worker Termux).",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "termux_clipboard_get",
        "description": "Lit le presse-papier du téléphone (worker Termux).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "termux_clipboard_set",
        "description": "Écrit dans le presse-papier du téléphone (worker Termux).",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "termux_torch",
        "description": "Allume/éteint la lampe torche du téléphone (worker Termux).",
        "input_schema": {
            "type": "object",
            "properties": {"on": {"type": "boolean", "default": True}},
        },
    },
    # ─── Backups (récupération si Orion supprime/écrase) ──────
    {
        "name": "list_backups",
        "description": "Liste les sauvegardes automatiques créées avant chaque "
                       "delete_file/move_file. Permet de retrouver et restaurer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hours": {"type": "number", "description": "Fenêtre temporelle", "default": 24},
                "limit": {"type": "integer", "description": "Max d'entrées", "default": 50},
            },
        },
    },
    {
        "name": "restore_backup",
        "description": "Restaure une sauvegarde. Sans target → restaure à l'emplacement original.",
        "input_schema": {
            "type": "object",
            "properties": {
                "backup_path": {"type": "string", "description": "Chemin du .bak (obtenu via list_backups)"},
                "target":      {"type": "string", "description": "Cible alternative (optionnel)"},
                "overwrite":   {"type": "boolean", "description": "Écraser la cible existante", "default": False},
            },
            "required": ["backup_path"],
        },
    },
    {
        "name": "purge_backups",
        "description": "Supprime les backups plus vieux que N jours. DESTRUCTIF, demande confirm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "older_than_days": {"type": "integer", "default": 30},
                "confirm":         {"type": "boolean", "default": False},
            },
        },
    },
    # ─── Audit log (consultation des actions passées) ─────────
    {
        "name": "audit_recent",
        "description": "Liste les actions récentes exécutées par Orion (audit log). "
                       "Utilise pour répondre à 'qu'est-ce que tu as fait ?', "
                       "'liste les actions sensibles', 'erreurs récentes'. "
                       "Retourne timestamp, device, tool, succès, durée.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit":  {"type": "integer", "description": "Nombre max d'entrées (1-100)", "default": 20},
                "hours":  {"type": "number",  "description": "Fenêtre temporelle en heures", "default": 24},
                "sensitive_only": {"type": "boolean", "description": "Filtrer sur actions sensibles uniquement", "default": False},
                "failed_only":    {"type": "boolean", "description": "Filtrer sur échecs uniquement", "default": False},
            },
        },
    },
    {
        "name": "audit_stats",
        "description": "Statistiques agrégées de l'audit log : total, succès, échecs, "
                       "actions sensibles, top 5 des tools les plus utilisés.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hours": {"type": "number", "description": "Fenêtre temporelle en heures", "default": 24},
            },
        },
    },
    # ─── Vision (analyse d'image) ─────────────────────────────
    {
        "name": "analyze_image",
        "description": "Analyse une image (PNG, JPG, etc.) et retourne une description textuelle. "
                       "Utilise Claude/Gemini Vision. Combine avec screenshot pour 'regarde mon écran et dis-moi…'. "
                       "Idéal pour : décrire une photo, lire le texte d'une capture, analyser un graphique, "
                       "comprendre une erreur visible à l'écran.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin de l'image (PNG, JPG, GIF, WebP, BMP)"},
                "prompt": {
                    "type": "string",
                    "description": "Question ou consigne sur l'image (ex: 'lis le texte', 'décris', 'que voit-on ?')",
                    "default": "Décris cette image en détail.",
                },
                "provider": {
                    "type": "string",
                    "description": "anthropic | gemini | ollama (défaut: provider Orion courant)",
                },
            },
            "required": ["path"],
        },
    },
    # ─── Cockpit ──────────────────────────────────────────────
    {
        "name": "cockpit_set_mode",
        "description": "Bascule l'affichage du cockpit sur un mode : 'voice' (conversation), "
                       "'trading' (poste de trading), 'desktop' (écran, fenêtres, presse-papier), "
                       "'system' (services, pont MCP, audit). Purement visuel. À utiliser dès que "
                       "la tâche demandée correspond à un autre mode que celui affiché, AVANT de "
                       "commencer le travail — l'écran doit suivre la conversation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "description": "voice | trading | desktop | system"},
            },
            "required": ["mode"],
        },
    },
    {
        "name": "cockpit_modes",
        "description": "Liste les modes du cockpit et ce que chacun affiche.",
        "input_schema": {"type": "object", "properties": {}},
    },
    # ─── Vision par caméra ────────────────────────────────────
    {
        "name": "camera_status",
        "description": "Disponibilité de la caméra, état de l'interrupteur ORION_CAMERA_ENABLED, "
                       "applications de vision lançables et celles en cours. Lecture seule, "
                       "répond même caméra désactivée. À appeler avant toute prise de vue.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "camera_look",
        "description": "Que vois-tu ? Prend UNE image et y détecte les objets (personne, téléphone, "
                       "tasse, ordinateur...) avec score et position. Rapide. Pour une description "
                       "libre plutôt qu'une liste de classes, préférer camera_snapshot puis "
                       "analyze_image. Nécessite ORION_CAMERA_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "seuil": {"type": "number", "description": "Score minimum 0-1", "default": 0.4},
                "max_objets": {"type": "integer", "default": 8},
                "save": {"type": "boolean", "description": "Enregistrer aussi l'image", "default": False},
            },
        },
    },
    {
        "name": "camera_snapshot",
        "description": "Prend une photo et l'enregistre. Le chemin rendu se passe directement à "
                       "analyze_image pour faire décrire la scène par le modèle de vision. "
                       "Nécessite ORION_CAMERA_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin de sortie (auto dans data/captures si vide)"},
            },
        },
    },
    {
        "name": "camera_gesture",
        "description": "Lit le geste de la ou des mains devant la caméra : poing, main ouverte, "
                       "victoire, pouce levé, index, cornes... Renvoie aussi le nombre de doigts "
                       "levés. Nécessite ORION_CAMERA_ENABLED=true.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "camera_watch",
        "description": "Observe la scène devant la caméra pendant N secondes et résume les événements aperçus "
                       "(objets, personnes identifiées, mouvements, timeline). "
                       "Nécessite ORION_CAMERA_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "duree": {"type": "number", "description": "Durée d'observation en secondes (1-30)", "default": 5.0},
                "interval": {"type": "number", "description": "Intervalle de capture en secondes", "default": 1.0},
            },
        },
    },
    {
        "name": "camera_read_document",
        "description": "Photographie une facture, un reçu ou un document devant la caméra et en extrait "
                       "des données structurées JSON (fournisseur, date, total, TVA, articles) pour HAM-COMPTA. "
                       "Nécessite ORION_CAMERA_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_type": {"type": "string", "description": "Type de document (facture, recu, auto)", "default": "auto"},
                "prompt_extra": {"type": "string", "description": "Consigne spécifique supplémentaire"},
                "save_path": {"type": "string", "description": "Chemin de sauvegarde optionnel pour l'image"},
            },
        },
    },
    {
        "name": "face_enroll",
        "description": "Enregistre un nouveau visage connu sous un nom donné pour la reconnaissance faciale locale "
                       "(biométrie 100% locale stockée dans data/known_faces/). Pris depuis la caméra ou un fichier image.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nom ou prénom de la personne (ex: 'alice')"},
                "image_path": {"type": "string", "description": "Chemin optionnel d'une photo (sinon utilise la caméra)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "face_list",
        "description": "Liste les personnes dont le visage est enregistré dans la base biométrique locale.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "face_delete",
        "description": "Supprime les données biométriques locales enregistrées pour une personne.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nom de la personne à supprimer"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "vision_app_start",
        "description": "Lance une application de vision dans sa propre fenêtre : 'detection' "
                       "(mains/visages/objets), 'drowsiness' (somnolence et distraction du "
                       "conducteur), 'surveillance' (alerte intrus), 'comptage' (franchissement "
                       "de ligne), 'domotique' (extinction sur absence). Boucle bloquante à part, "
                       "pilotée au clavier. Nécessite ORION_CAMERA_ENABLED=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app": {"type": "string",
                        "description": "detection | drowsiness | surveillance | comptage | domotique"},
            },
            "required": ["app"],
        },
    },
    {
        "name": "vision_app_stop",
        "description": "Arrête une application de vision lancée par vision_app_start, ou toutes si "
                       "aucune n'est précisée.",
        "input_schema": {
            "type": "object",
            "properties": {"app": {"type": "string", "description": "Omettre pour tout arrêter"}},
        },
    },
    # ─── Tools Trading ─────────────────────────────────────────
    {
        "name": "trading_alert_create",
        "description": "Crée une alerte de niveau de prix (TradingView ou locale). "
                       "Déclenche un avertissement quand le prix franchit la limite.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbole (ex: 'XAUUSD', 'EURUSD')"},
                "price": {"type": "number", "description": "Niveau de prix à surveiller"},
                "message": {"type": "string", "description": "Message ou note d'alerte"},
                "condition": {"type": "string", "description": "crosses | crosses_above | crosses_below", "default": "crosses"},
            },
            "required": ["symbol", "price"],
        },
    },
    {
        "name": "trading_alert_list",
        "description": "Liste les alertes de niveaux de prix actives.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "trading_alert_delete",
        "description": "Supprime une alerte de niveau de prix par son ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "alert_id": {"type": "string", "description": "ID de l'alerte à supprimer"},
            },
            "required": ["alert_id"],
        },
    },
    {
        "name": "trading_session_report",
        "description": "Génère le bilan synthétique de la session de trading du jour (PnL, RR moyen, winrate) "
                       "et peut le pousser directement sur Telegram.",
        "input_schema": {
            "type": "object",
            "properties": {
                "push_telegram": {"type": "boolean", "description": "Envoyer aussi la notif sur Telegram", "default": True},
            },
        },
    },
    {
        "name": "trading_check_risk",
        "description": "Simule et calcule le pourcentage de risque d'un ordre avant exécution (garde-fou).",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbole (ex: 'XAUUSD')"},
                "action": {"type": "string", "description": "BUY | SELL"},
                "entry": {"type": "number", "description": "Prix d'entrée"},
                "sl": {"type": "number", "description": "Stop Loss"},
                "volume": {"type": "number", "description": "Volume en lots", "default": 0.01},
                "account_balance": {"type": "number", "default": 10000.0},
            },
            "required": ["symbol", "action", "entry", "sl"],
        },
    },
    {
        "name": "trading_backtest_start",
        "description": "Démarre une session de backtest guidé / Replay TradingView sur un symbole.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "default": "XAUUSD"},
                "timeframe": {"type": "string", "default": "1h"},
                "start_time": {"type": "string", "description": "Date/Heure de début (ISO)"},
            },
        },
    },
    {
        "name": "trading_backtest_step",
        "description": "Avance la simulation de backtest d'un ou plusieurs pas (chandelles).",
        "input_schema": {
            "type": "object",
            "properties": {
                "steps": {"type": "integer", "description": "Nombre de bougies à avancer", "default": 1},
            },
        },
    },
    {
        "name": "trading_backtest_results",
        "description": "Récupère les métriques de performance globales d'une stratégie de backtest.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "kronos_predict_candles",
        "description": "Exécute la prédiction neuronale du Foundation Model Kronos sur un symbole financier "
                       "(ex: 'XAUUSD', 'BTCUSD', 'EURUSD'). Prédit les prochains N chandeliers (OHLCV), "
                       "le biais directionnel, la confiance et le cône de probabilité Monte-Carlo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbole financier (ex: 'XAUUSD')", "default": "XAUUSD"},
                "pred_len": {"type": "integer", "description": "Nombre de bougies à prédire dans le futur (8 à 48)", "default": 12},
                "monte_carlo": {"type": "boolean", "description": "Générer les cônes de probabilité (Percentiles 10%, 50%, 90%)", "default": False},
            },
        },
    },
    {
        "name": "kronos_model_status",
        "description": "Obtient l'état du moteur neuronal Kronos (modèle chargé, GPU/CPU, état d'initialisation).",
        "input_schema": {"type": "object", "properties": {}},
    },

    # ─── Tools Bureau / Desktop ───────────────────────────────
    {
        "name": "screen_ocr",
        "description": "OCR de l'écran ou d'une fenêtre ('lis-moi cette erreur'). Extrai le texte "
                       "visible à l'écran via Tesseract local ou le modèle de vision d'Orion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                    },
                    "description": "Zone spécifique (optionnel)",
                },
                "monitor": {"type": "integer", "default": 0},
                "title_contains": {"type": "string", "description": "Nom de la fenêtre à lire (optionnel)"},
                "prompt": {"type": "string", "default": "Lis et retranscris tout le texte visible sur cette image."},
            },
        },
    },
    {
        "name": "window_watch",
        "description": "Surveille une fenêtre en arrière-plan ('préviens-moi quand ce téléchargement finit') "
                       "et émet une notification dès que la condition est remplie.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title_contains": {"type": "string", "description": "Titre ou fragment de la fenêtre à surveiller"},
                "condition": {"type": "string", "description": "closed | title_changed | text_appeared | text_disappeared", "default": "closed"},
                "target_text": {"type": "string", "description": "Texte cible pour text_appeared/disappeared"},
                "timeout_sec": {"type": "integer", "description": "Timeout en secondes", "default": 300},
            },
            "required": ["title_contains"],
        },
    },
    {
        "name": "clipboard_history_get",
        "description": "Consulte l'historique des 50 derniers contenus textes du presse-papier. "
                       "Permet de rechercher un texte précédemment copié.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "search": {"type": "string", "description": "Filtre de recherche par mot-clé (optionnel)"},
            },
        },
    },
    {
        "name": "clipboard_history_clear",
        "description": "Efface l'historique du presse-papier.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "macro_record_start",
        "description": "Démarre l'enregistrement d'une séquence macro (actions souris/clavier).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nom de la macro"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "macro_record_stop",
        "description": "Arrête et sauvegarde la macro actuellement en cours d'enregistrement.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "macro_action_add",
        "description": "Ajoute une action (clic, frappe, délai) à la macro en cours.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "mouse_click | mouse_move | keyboard_type | keyboard_key | delay"},
                "params": {"type": "object"},
            },
            "required": ["action_type"],
        },
    },
    {
        "name": "macro_play",
        "description": "Rejoue une macro enregistrée par son nom à la vitesse spécifiée.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nom de la macro à rejouer"},
                "speed": {"type": "number", "description": "Facteur de vitesse (1.0 = normal, 2.0 = rapide)", "default": 1.0},
                "repetitions": {"type": "integer", "description": "Nombre de répétitions", "default": 1},
            },
            "required": ["name"],
        },
    },
    {
        "name": "macro_list",
        "description": "Liste les macros enregistrées disponibles.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "macro_delete",
        "description": "Supprime une macro enregistrée.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nom de la macro à supprimer"},
            },
            "required": ["name"],
        },
    },
    # ─── Tools Voix & Réunions ───────────────────────────────
    {
        "name": "voice_dictate_obsidian",
        "description": "Enregistre une dictée vocale ('Orion, note que...') sous forme de note "
                       "datée et mise en forme dans le coffre Obsidian.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Contenu de la dictée à consigner"},
                "title": {"type": "string", "description": "Titre explicite de la note (optionnel)"},
                "category": {"type": "string", "description": "Sous-dossier dans Obsidian", "default": "Notes"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "meeting_summarize",
        "description": "Transcrit et résume un fichier de réunion/appel (.txt, .md, .mp3, .wav, .m4a). "
                       "Extrai les points clés, décisions et plan d'action (TODOS) dans une note Obsidian.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Chemin absolu ou relatif vers le fichier de réunion"},
                "title": {"type": "string", "description": "Titre du compte-rendu (optionnel)"},
                "push_telegram": {"type": "boolean", "description": "Envoyer le résumé synthétique sur Telegram", "default": False},
                "push_obsidian": {"type": "boolean", "default": True},
            },
            "required": ["file_path"],
        },
    },
    # ─── Tools Cerveau et Mémoire ────────────────────────────
    {
        "name": "vault_reindex_now",
        "description": "Déclenche immédiatement la réindexation automatique des fichiers du coffre Obsidian "
                       "dans la mémoire RAG d'Orion.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "vault_reindex_status",
        "description": "Consulte l'état du service de réindexation automatique du coffre Obsidian.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "journal_generate_daily",
        "description": "Génère et consigne la note de journal de bord rétrospective de la journée "
                       "dans le coffre Obsidian (résumé d'audit, actions et opérations).",
        "input_schema": {
            "type": "object",
            "properties": {
                "today_only": {"type": "boolean", "default": True},
            },
        },
    },
    {
        "name": "episodic_query",
        "description": "Interroge la mémoire épisodique d'Orion ('qu'est-ce qu'on a fait la semaine dernière ?') "
                       "en analysant la chronologie des opérations, journaux de bord et souvenirs RAG.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Question ou sujet recherché dans la mémoire épisodique"},
                "days_back": {"type": "integer", "description": "Nombre de jours dans le passé à analyser", "default": 7},
            },
        },
    },
    # ─── Pont MCP ─────────────────────────────────────────────
    {
        "name": "mcp_status",
        "description": "Diagnostic du pont MCP : serveurs externes connectés (TradingView, "
                       "MetaTrader 5...), tools exposés, erreurs de démarrage, et état des deux "
                       "interrupteurs (pont / exécution d'ordres). À appeler quand un tool mt5_* "
                       "ou tv_* échoue, pour savoir si le serveur est vivant.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

# Tools qui interagissent avec le matériel/OS et acceptent un target_device.
# (web_search, fetch_url, list_connected_devices, gmail_*, calendar_*,
#  generate_image, memory_* ne sont pas device-bound : ils tournent sur le serveur.)
_DEVICE_BOUND_TOOLS = {
    "create_file", "read_file", "list_directory", "delete_file", "create_directory",
    "move_file", "run_shell_command", "run_python_script", "get_system_info",
    "open_app", "open_url_in_browser", "list_running_processes",
    # Nouveaux device-bound
    "notify", "notify_telegram", "screenshot", "list_monitors", "read_pdf", "read_docx",
    "mouse_position", "mouse_move", "mouse_click", "keyboard_type", "keyboard_press",
    "automation_status", "mouse_drag", "mouse_scroll", "keyboard_key",
    "clipboard_get", "clipboard_set", "clipboard_history_get", "clipboard_history_clear",
    "list_windows", "focus_window", "window_control", "window_watch",
    "screen_ocr", "macro_record_start", "macro_record_stop", "macro_action_add", "macro_play", "macro_list", "macro_delete",
    "camera_status", "camera_look", "camera_snapshot", "camera_gesture",
    "camera_watch", "camera_read_document", "face_enroll", "face_list", "face_delete",
    "vision_app_start", "vision_app_stop",
    "voice_dictate_obsidian", "meeting_summarize",
    # Tools Termux : ne s'exécutent QUE sur worker Android
    "termux_battery", "termux_location", "termux_send_sms", "termux_list_sms",
    "termux_contacts", "termux_call", "termux_vibrate", "termux_notification",
    "termux_clipboard_get", "termux_clipboard_set", "termux_torch",
}

# Augmente le schéma de chaque tool device-bound avec un paramètre target_device optionnel.
for _tool in TOOLS:
    if _tool["name"] in _DEVICE_BOUND_TOOLS:
        _tool["input_schema"].setdefault("properties", {})["target_device"] = {
            "type": "string",
            "description": "device_id de l'appareil cible (ex: 'mon-telephone'). Omettre ou 'server' "
                           "pour exécuter sur le serveur. Utilise list_connected_devices d'abord.",
        }


# ─────────────────────────────────────────────────────────────────
# Tools MCP externes (TradingView, MetaTrader 5, ...)
# ─────────────────────────────────────────────────────────────────
# Les schémas ne sont pas connus à l'import : il faut interroger chaque serveur.
# On charge donc à la première utilisation, jamais à l'import — sinon le simple
# fait d'importer l'orchestrateur (tests, CLI, worker) lancerait des process.

def get_tools() -> list[dict]:
    """Schémas natifs + schémas découverts sur les serveurs MCP déclarés."""
    try:
        mcp_bridge.load()  # idempotent, no-op si ORION_MCP_ENABLED != true
    except Exception:
        return TOOLS
    if not mcp_bridge.MCP_TOOLS:
        return TOOLS
    return TOOLS + mcp_bridge.MCP_TOOLS


def _resolve_handler(tool_name: str):
    handler = ALL_HANDLERS.get(tool_name)
    if handler is not None:
        return handler
    return mcp_bridge.MCP_HANDLERS.get(tool_name)


# ─────────────────────────────────────────────────────────────────
# Prompt système d'Orion
# ─────────────────────────────────────────────────────────────────
MAX_ITERATIONS = 25

SYSTEM_PROMPT = """Tu es Orion, un assistant IA personnel ultra-compétent.
Tu travailles directement sur l'appareil de l'utilisateur.

Tes capacités :
- Créer, lire, modifier, supprimer des fichiers et dossiers
- Exécuter des commandes shell et scripts Python
- Rechercher sur le web et lire des pages web
- Ouvrir des applications et logiciels
- Piloter le bureau : voir l'écran, déplacer et cliquer la souris, taper au
  clavier, gérer les fenêtres, lire et écrire le presse-papier

═══ PILOTAGE DU BUREAU ═══
Ces tools agissent physiquement sur la machine. Méthode :

1. automation_status EN PREMIER. Il dit si l'interrupteur est ouvert et donne la
   géométrie des écrans. Si l'automation est désactivée, dis-le à l'utilisateur
   au lieu d'enchaîner des appels qui échoueront tous.
2. Regarde avant d'agir : screenshot ou list_windows. Ne clique jamais sur des
   coordonnées devinées ou mémorisées d'un écran précédent — l'interface a pu
   bouger entre deux actions.
3. Les coordonnées sont celles du BUREAU VIRTUEL. Si tu as demandé un screenshot
   avec max_width, l'image est réduite : applique la conversion donnée par
   'coordinate_hint' avant de cliquer. Ne clique pas aux coordonnées lues
   directement sur une image réduite.
4. Pour viser précisément : une capture large pour repérer la zone, puis
   screenshot avec 'region' autour de la cible (une région sous max_width n'est
   pas réduite, échelle 1.0).
5. Pour saisir du texte avec accents ou un texte long : clipboard_set puis
   keyboard_key('ctrl+v'). keyboard_type passe par les scancodes d'un clavier US
   et déforme les accents.
6. Après une action qui change l'écran (clic sur un bouton, ouverture d'une
   fenêtre), reprends une capture avant l'action suivante.
7. Vérifie le résultat plutôt que de le supposer, et rapporte ce que tu as
   réellement observé.

Prudence : window_control avec 'close' peut faire perdre du travail non
enregistré — demande avant. Ne tape jamais de mot de passe, de numéro de carte
ou de code d'authentification au clavier, même si on te les donne : dis à
l'utilisateur de les saisir lui-même.

═══ L'ÉCRAN SUIT LA CONVERSATION ═══
Tu es affiché dans un cockpit à quatre modes : voice, trading, desktop, system.
Dès qu'une demande relève d'un autre mode que celui affiché, appelle
cockpit_set_mode AVANT de commencer le travail — pas après, pas à la place du
travail. L'utilisateur doit voir apparaître le bon poste pendant que tu agis.

- « analyse le marché », « regarde l'or », « mes positions » → trading
- « que vois-tu à l'écran », « ferme cette fenêtre », « copie ça » → desktop
- « est-ce que tout tourne », « le pont MCP répond ? », « l'audit » → system
- retour à la simple conversation → voice

Une seule bascule par demande. Ne rebascule pas à chaque outil.

═══ MARCHÉS ET TRADING ═══
Les tools mt5_* (MetaTrader 5, COMPTE RÉEL) et tv_* (TradingView) sont branchés
via le pont MCP. Ils touchent de l'argent réel : discipline obligatoire.

Avant d'analyser :
- Si un tool mt5_* ou tv_* échoue, appelle mcp_status pour savoir si le serveur
  est vivant avant de conclure quoi que ce soit.
- Les symboles du courtier portent un suffixe (XAUUSDc, EURUSDc...). Utilise
  toujours mt5_symbols_search pour trouver le nom exact — ne devine jamais.
- TradingView exige que son application de bureau tourne avec CDP activé. Si les
  tools tv_* renvoient "CDP connection failed", n'en conclus pas que TradingView
  est absent : demande à l'utilisateur de lancer son raccourci
  "Lancer TradingView (CDP)". Le tool tv_tv_launch ne trouve pas l'exécutable sur
  cette machine, inutile d'insister avec.
- Ne cite jamais un prix de mémoire ou par estimation : lis-le avec mt5_quote ou
  tv_quote_get. Un chiffre inventé sur un marché est une faute grave.

Avant d'exécuter un ordre :
- N'ouvre, ne modifie et ne ferme JAMAIS une position de ta propre initiative.
  Il faut une instruction explicite de l'utilisateur, avec au minimum le
  symbole, le sens, le volume et le stop loss.
- Fais d'abord tourner mt5_order_send SANS confirm (aperçu / dry run), montre
  l'aperçu à l'utilisateur — prix, volume, SL, TP, risque en devise du compte —
  et attends son accord avant de relancer avec confirm.
- Refuse un ordre sans stop loss. Dis-le clairement et propose un niveau.
- Vérifie la taille de position par rapport à mt5_account_info : si le risque
  dépasse manifestement ce que le compte supporte, signale-le avant d'agir.
- Après exécution, relis mt5_positions_get et rapporte l'état réel obtenu, pas
  l'état espéré.

Tu n'es pas conseiller financier agréé. Tu peux décrire ce que montrent les
données, les structures et les niveaux ; dis clairement que la décision et le
risque appartiennent à l'utilisateur, sans te transformer en donneur d'ordres.

Principes :
- Sois proactif : si tu dois créer un fichier Python, crée-le ET exécute-le si c'est logique
- Confirme chaque action effectuée avec son résultat
- Si une commande échoue, propose une alternative
- Réponds en français sauf si on te parle dans une autre langue
- Pour les tâches complexes, décompose et exécute étape par étape
- Ne demande pas confirmation pour des actions non-destructives
- Pour supprimer/écraser des fichiers importants, confirme d'abord

Tu es sur l'appareil de l'utilisateur. Agis comme un assistant technique de confiance."""

# Suffixe ajouté quand l'utilisateur parle via le service voix (device_id "voice-*").
# Le TTS lit le texte tel quel : pas de markdown, pas d'emoji, phrases courtes.
VOICE_SYSTEM_SUFFIX = """

═══ MODE VOCAL ACTIF ═══
L'utilisateur te parle via micro. Tes réponses sont lues à haute voix par un TTS.
Règles strictes pour la voix :
- AUCUN emoji, AUCUN caractère décoratif (😊 ✓ → etc.). Le TTS les prononce.
- AUCUN markdown : pas de **gras**, pas d'*italique*, pas de listes à puces, pas de #titres.
- AUCUN bloc de code : si tu dois donner du code, dis "le code est dans le fichier X".
- Phrases COURTES et naturelles (max 2-3 phrases par réponse en général).
- Pas de salutations longues. Va à l'essentiel.
- Si tu lances une action longue (web_search, fetch_url), annonce d'abord en une phrase :
  "Je cherche…" puis donne le résultat.
- Si l'utilisateur demande quelque chose d'ambigu, pose UNE question courte plutôt
  que de proposer 5 options."""


def _build_system_prompt(device_id: str | None = None) -> str:
    """Construit le system prompt avec adaptations contextuelles."""
    prompt = SYSTEM_PROMPT
    if device_id and device_id.startswith("voice-"):
        prompt += VOICE_SYSTEM_SUFFIX
    return prompt


# ─────────────────────────────────────────────────────────────────
# Moteur d'exécution
# ─────────────────────────────────────────────────────────────────
def execute_tool(tool_name: str, tool_input: dict, dispatcher=None,
                 list_devices=None, device_id: str | None = None) -> str:
    """Exécute un tool et retourne le résultat en JSON string.

    Args:
        tool_name: Nom du tool Claude.
        tool_input: Paramètres ; peut contenir un 'target_device' optionnel.
        dispatcher: Callback (device_id, tool_name, tool_input) -> result_str
                    pour exécution sur un appareil distant.
        list_devices: Callback () -> list[dict] pour le tool list_connected_devices.
        device_id:  Identifiant du client appelant (sert pour la confirmation
                    par mot de passe et l'audit log).
    """
    # Cas spécial : tool de listing géré côté serveur (pas de log intéressant)
    if tool_name == "list_connected_devices":
        if list_devices is None:
            return json.dumps({"success": True, "devices": [], "message": "Mode standalone : aucun appareil distant."})
        return json.dumps({"success": True, "devices": list_devices()}, ensure_ascii=False)

    # Extraction du target_device (présent uniquement sur les tools device-bound)
    tool_input = dict(tool_input)  # copie défensive
    target = tool_input.pop("target_device", None)

    import time as _time
    is_sensitive = confirm.requires_confirmation(tool_name, tool_input)
    confirmed = False

    # ── Mode PANIC : refus tout sauf whitelist lecture ──
    if not panic.is_tool_allowed(tool_name):
        err = (f"Mode PANIC actif — '{tool_name}' refusé. "
               f"Désactive avec POST /api/panic/release pour rétablir.")
        row_id = audit.log_tool_call(
            device_id=device_id or "?", tool_name=tool_name,
            tool_input=tool_input, success=False, error=err,
            duration_ms=0, target=target, sensitive=True, confirmed=False,
        )
        audit._trigger_alert(row_id, True,
                             tool_name=tool_name, device_id=device_id,
                             success=False, error=err, confirmed=False)
        return json.dumps({"success": False, "error": err}, ensure_ascii=False)

    # ── Rate limit sur tools sensibles (anti-abus) ──
    if device_id and is_sensitive:
        ok, reason = rate_limit.check_and_record(device_id)
        if not ok:
            row_id = audit.log_tool_call(
                device_id=device_id, tool_name=tool_name,
                tool_input=tool_input, success=False, error=reason,
                duration_ms=0, target=target, sensitive=True, confirmed=False,
            )
            audit._trigger_alert(row_id, True,
                                 tool_name=tool_name, device_id=device_id,
                                 success=False, error=reason, confirmed=False)
            return json.dumps({"success": False, "error": reason}, ensure_ascii=False)

    # ── Couche de confirmation pour actions dangereuses ──
    if device_id and is_sensitive:
        approved = confirm.request_confirmation(
            device_id=device_id,
            tool_name=tool_name,
            tool_input=tool_input,
            reason=confirm.reason_for(tool_name),
        )
        if not approved:
            err = (f"Action '{tool_name}' refusée par l'utilisateur "
                   f"(confirmation par mot de passe requise).")
            row_id = audit.log_tool_call(
                device_id=device_id or "?", tool_name=tool_name,
                tool_input=tool_input, success=False, error=err,
                duration_ms=0, target=target, sensitive=True, confirmed=False,
            )
            audit._trigger_alert(row_id, True,
                                 tool_name=tool_name, device_id=device_id,
                                 success=False, error=err, confirmed=False)
            return json.dumps({"success": False, "error": err}, ensure_ascii=False)
        confirmed = True

    # ── Backup auto avant action destructive locale ──
    # (skip si exécution distante : trop coûteux à transférer)
    if (not target or target in ("", "server", "local")):
        try:
            if tool_name == "delete_file":
                src = tool_input.get("path")
                if src:
                    safety_backup.backup_file_or_dir(src)
            elif tool_name == "move_file" and tool_input.get("dst"):
                # Si la destination existe → backup avant écrasement
                from pathlib import Path as _P
                dst = _P(tool_input["dst"]).expanduser()
                if dst.exists():
                    safety_backup.backup_file_or_dir(str(dst))
        except Exception as exc:
            print(f"[backup!] {exc}")

    # ── Exécution distante via worker ──
    t0 = _time.time()
    if target and target not in ("", "server", "local") and dispatcher is not None:
        try:
            result_str = dispatcher(target, tool_name, tool_input)
        except Exception as e:
            result_str = json.dumps({"success": False, "error": f"Dispatch vers '{target}' a échoué : {e}"})
    else:
        # Exécution locale
        handler = _resolve_handler(tool_name)
        if not handler:
            result_str = json.dumps({"success": False, "error": f"Tool inconnu : {tool_name}"})
        else:
            try:
                result = handler(tool_input)
                result_str = json.dumps(result, ensure_ascii=False)
            except Exception as e:
                result_str = json.dumps({"success": False, "error": str(e)})
    duration_ms = int((_time.time() - t0) * 1000)

    # ── Log audit (best-effort, n'interrompt jamais le flow) ──
    try:
        result_obj = json.loads(result_str) if isinstance(result_str, str) else result_str
        success = bool(result_obj.get("success", True))
        error = (result_obj.get("error") or "")[:300]
    except Exception:
        success, error = True, ""
    row_id = audit.log_tool_call(
        device_id=device_id or "?", tool_name=tool_name,
        tool_input=tool_input, success=success, error=error,
        duration_ms=duration_ms, target=target,
        sensitive=is_sensitive, confirmed=confirmed,
    )
    audit._trigger_alert(row_id, is_sensitive,
                         tool_name=tool_name, device_id=device_id,
                         success=success, error=error,
                         confirmed=confirmed, duration_ms=duration_ms,
                         target=target)
    return result_str


def process_request(
    user_message: str,
    conversation_history: list = None,
    on_tool_call=None,
    dispatcher=None,
    list_devices=None,
    device_id: str | None = None,
) -> tuple[str, list]:
    """
    Traite une requête utilisateur avec boucle agentic.

    Args:
        user_message: Le message de l'utilisateur
        conversation_history: Historique de la conversation (modifié in-place)
        on_tool_call: Callback(tool_name, tool_input, result) appelé à chaque tool use
        device_id: ID du client appelant (sert à adapter le system prompt :
                   les sessions "voice-*" reçoivent des règles vocales).

    Returns:
        (réponse_finale, historique_mis_à_jour)
    """
    if conversation_history is None:
        conversation_history = []

    # Ajoute le message utilisateur
    conversation_history.append({"role": "user", "content": user_message})

    final_response = ""
    provider = _get_provider()
    system_prompt = _build_system_prompt(device_id)

    for _ in range(MAX_ITERATIONS):
        response = provider.call(
            system=system_prompt,
            tools=get_tools(),
            messages=conversation_history,
            max_tokens=4096,
        )

        tool_uses = [b for b in response.content if b["type"] == "tool_use"]
        text_parts = [b["text"] for b in response.content if b["type"] == "text"]

        if text_parts:
            final_response = "\n".join(text_parts)

        # On stocke en dicts purs (pivot) — compatible Anthropic ET Gemini au tour suivant
        conversation_history.append({"role": "assistant", "content": response.content})

        if not tool_uses:
            return final_response, conversation_history

        tool_results = []
        for tool_block in tool_uses:
            result = execute_tool(
                tool_block["name"], tool_block["input"],
                dispatcher=dispatcher, list_devices=list_devices,
                device_id=device_id,
            )
            if on_tool_call:
                on_tool_call(tool_block["name"], tool_block["input"], result)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block["id"],
                "content": result,
            })

        conversation_history.append({"role": "user", "content": tool_results})

    if not final_response:
        final_response = f"[Limite de {MAX_ITERATIONS} itérations atteinte]"
    return final_response, conversation_history


def process_request_streaming(
    user_message: str,
    conversation_history: list = None,
    on_text_delta=None,         # Callback(str) appelé pour chaque fragment de texte
    on_tool_call=None,          # Callback(name, input, result) après exécution d'un tool
    dispatcher=None,
    list_devices=None,
    device_id: str | None = None,
) -> tuple[str, list]:
    """
    Version streamée de process_request : appelle on_text_delta(fragment) en temps réel.

    Idéal pour réduire la latence perçue côté UI/voix : la réponse commence à
    s'afficher dès le premier token généré par le LLM, au lieu d'attendre la fin.

    Returns:
        (réponse_finale_complète, historique_mis_à_jour)
    """
    if conversation_history is None:
        conversation_history = []

    conversation_history.append({"role": "user", "content": user_message})

    final_response = ""
    provider = _get_provider()
    system_prompt = _build_system_prompt(device_id)

    for _ in range(MAX_ITERATIONS):
        response: ProviderResponse | None = None
        for chunk in provider.stream(
            system=system_prompt,
            tools=get_tools(),
            messages=conversation_history,
            max_tokens=4096,
        ):
            ctype = chunk.get("type")
            if ctype == "text_delta":
                text = chunk.get("text") or ""
                if text and on_text_delta:
                    try:
                        on_text_delta(text)
                    except Exception:
                        pass
            elif ctype == "done":
                response = chunk.get("response")

        if response is None:
            break

        tool_uses = [b for b in response.content if b.get("type") == "tool_use"]
        text_parts = [b["text"] for b in response.content if b.get("type") == "text"]
        if text_parts:
            final_response = "\n".join(text_parts)

        conversation_history.append({"role": "assistant", "content": response.content})

        if not tool_uses:
            return final_response, conversation_history

        tool_results = []
        for tool_block in tool_uses:
            result = execute_tool(
                tool_block["name"], tool_block["input"],
                dispatcher=dispatcher, list_devices=list_devices,
                device_id=device_id,
            )
            if on_tool_call:
                on_tool_call(tool_block["name"], tool_block["input"], result)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block["id"],
                "content": result,
            })
        conversation_history.append({"role": "user", "content": tool_results})

    if not final_response:
        final_response = f"[Limite de {MAX_ITERATIONS} itérations atteinte]"
    return final_response, conversation_history
