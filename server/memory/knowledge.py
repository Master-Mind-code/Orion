"""
Base de connaissances évolutive d'Orion.

Ce que ce module fait — et ce qu'il ne fait pas
──────────────────────────────────────────────
Il constitue une mémoire consultable : Orion ingère des sources (fichiers,
pages web, vidéos, recherches), les découpe, les vectorise et les retrouve au
moment de répondre. Ses réponses s'améliorent parce qu'il dispose de plus de
matière, pas parce que le modèle change.

Il ne modifie **pas** les poids du modèle. Orion s'appuie sur les API Anthropic
et Google : leurs modèles sont figés côté fournisseur, aucun apprentissage de
paramètres n'est possible depuis cette machine. Toute formulation laissant
croire qu'Orion « se ré-entraîne » serait fausse.

Quatre portes d'entrée
──────────────────────
  learn_from_source   une source précise : fichier, dossier, URL, vidéo, texte.
  learn_from_topic    Orion part chercher lui-même sur le web et indexe.
  learn_from_inbox    tout ce qui a été déposé dans le dossier de dépôt.
  knowledge_teach     restitue ce qui est su d'un sujet, pour former ou appliquer.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
INBOX_DIR = DATA_DIR / "knowledge_inbox"
PROCESSED_DIR = INBOX_DIR / "_traites"
LEDGER_FILE = DATA_DIR / "memory" / "knowledge_ledger.json"

DEFAULT_NAMESPACE = "connaissances"

# Une source vraiment maigre n'apprend rien et pollue la recherche.
MIN_USEFUL_CHARS = 200


# ════════════════════════════════════════════════════════════════════════════
# Journal des sources apprises
# ════════════════════════════════════════════════════════════════════════════

def _load_ledger() -> Dict[str, Any]:
    if not LEDGER_FILE.exists():
        return {"sources": []}
    try:
        return json.loads(LEDGER_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"sources": []}


def _record(entry: Dict[str, Any]) -> None:
    """Consigne une source apprise.

    Sans ce journal, impossible de répondre à « qu'est-ce que tu as appris et
    d'où ça vient ? » : le vector store ne garde que des fragments.
    """
    ledger = _load_ledger()
    ledger["sources"] = [s for s in ledger["sources"] if s.get("source") != entry["source"]]
    ledger["sources"].append(entry)
    try:
        LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        LEDGER_FILE.write_text(json.dumps(ledger, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except OSError as exc:
        print(f"[knowledge] journal non écrit : {exc}")


def already_learned(source: str) -> Optional[Dict[str, Any]]:
    return next((s for s in _load_ledger()["sources"] if s.get("source") == source), None)


# ════════════════════════════════════════════════════════════════════════════
# Extraction du texte selon le type de source
# ════════════════════════════════════════════════════════════════════════════

def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _extract_web_page(url: str, max_chars: int = 200_000) -> Dict[str, Any]:
    """Contenu lisible d'une page web.

    On privilégie les balises de contenu (article, main) avant de retomber sur
    le corps entier : sinon les menus et pieds de page se retrouvent indexés et
    ressortent dans les recherches.
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as exc:
        return {"success": False, "error": f"Dépendance manquante : {exc}"}

    headers = {"User-Agent": "Mozilla/5.0 (compatible; Orion/3.0; +knowledge-ingest)"}
    try:
        resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"[:200]}

    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = re.sub(r"\n{3,}", "\n\n", main.get_text("\n", strip=True))

    title = soup.find("title")
    return {
        "success": True,
        "text": text[:max_chars],
        "title": title.get_text(strip=True) if title else url,
        "kind": "page web",
    }


def _extract_local_media(path: Path) -> Dict[str, Any]:
    from server.memory import media_ingest

    result = media_ingest.transcribe_audio_file(path)
    if not result["success"]:
        return result
    return {"success": True, "text": result["text"],
            "title": path.name, "kind": "média local transcrit"}


def extract_source_text(source: str, language: Optional[str] = None,
                        cookies_from_browser: Optional[str] = None,
                        cookies_file: Optional[str] = None) -> Dict[str, Any]:
    """Texte exploitable d'une source, quel que soit son type.

    L'appelant n'a pas à savoir si `source` est un chemin, une URL, une vidéo
    ou du texte brut : c'est le travail de cette fonction de le déterminer.
    """
    source = source.strip()
    if not source:
        return {"success": False, "error": "Source vide."}

    if _looks_like_url(source):
        from server.memory import media_ingest
        if media_ingest.is_video_url(source):
            result = media_ingest.get_video_transcript(
                source, language=language, cookies_from_browser=cookies_from_browser,
                cookies_file=cookies_file)
            if result["success"]:
                return {"success": True, "text": result["text"],
                        "title": result.get("title") or source,
                        "kind": f"vidéo ({result['method']})",
                        "language": result.get("language"),
                        "duration_seconds": result.get("duration_seconds")}
            return result
        return _extract_web_page(source)

    path = Path(source).expanduser()
    if path.exists():
        if path.is_dir():
            return {"success": False, "error": "dossier", "is_dir": True, "path": str(path)}
        if path.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg", ".flac",
                                   ".mp4", ".mkv", ".webm", ".mov", ".avi"):
            return _extract_local_media(path)

        from server.memory.rag_tools import _read_file_text
        text = _read_file_text(path)
        if not text.strip():
            return {"success": False, "error": (
                f"Aucun texte extrait de {path.name}. Format non pris en charge, "
                f"ou PDF scanné sans couche texte.")}
        return {"success": True, "text": text, "title": path.name, "kind": "fichier"}

    # Ni URL ni chemin : on considère que c'est le savoir lui-même.
    return {"success": True, "text": source, "title": "note directe", "kind": "texte brut"}


# ════════════════════════════════════════════════════════════════════════════
# Apprentissage
# ════════════════════════════════════════════════════════════════════════════

def _index_text(text: str, source_label: str, namespace: str,
                tags: List[str], chunk_chars: int = 800) -> Dict[str, Any]:
    from server.memory.rag_tools import _chunk_text, _store
    from server.memory.embedder import get_embedder

    chunks = _chunk_text(text, target_chars=int(chunk_chars))
    if not chunks:
        return {"success": False, "error": "Texte vide après découpage."}

    try:
        vectors = get_embedder().embed(chunks)
        added = _store(namespace).add_batch(chunks, vectors,
                                            source=source_label, tags=tags)
    except ImportError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    return {"success": True, "chunks_added": added}


def learn_from_source(source: str, namespace: str = DEFAULT_NAMESPACE,
                      tags: Optional[List[str]] = None,
                      language: Optional[str] = None,
                      cookies_from_browser: Optional[str] = None,
                      cookies_file: Optional[str] = None,
                      force: bool = False,
                      chunk_chars: int = 800) -> Dict[str, Any]:
    """Ingère une source et l'ajoute à la base de connaissances.

    Accepte indifféremment un fichier, un dossier, une URL, une vidéo ou du
    texte brut. Une source déjà apprise n'est pas réindexée sans `force` : cela
    dupliquerait ses fragments et fausserait les recherches ultérieures.
    """
    tags = tags or []
    source = source.strip()

    if not force:
        seen = already_learned(source)
        if seen:
            return {"success": True, "already_known": True, "source": source,
                    "learned_at": seen.get("learned_at_human"),
                    "chunks": seen.get("chunks_added"),
                    "message": "Source déjà apprise. Utilise force=true pour la réapprendre."}

    extracted = extract_source_text(source, language=language,
                                    cookies_from_browser=cookies_from_browser,
                                    cookies_file=cookies_file)

    # Un dossier : on délègue à l'indexeur de répertoire déjà en place.
    if extracted.get("is_dir"):
        from server.memory.rag_tools import memory_index_dir
        result = memory_index_dir(extracted["path"], namespace=namespace,
                                  chunk_chars=chunk_chars)
        if result.get("success"):
            _record({"source": source, "kind": "dossier", "namespace": namespace,
                     "chunks_added": result.get("chunks_added", 0),
                     "files_indexed": result.get("files_indexed", 0),
                     "tags": tags, "learned_at": time.time(),
                     "learned_at_human": time.strftime("%Y-%m-%d %H:%M:%S")})
        return result

    if not extracted["success"]:
        return {"success": False, "source": source, "error": extracted["error"],
                "hint": extracted.get("hint")}

    text = extracted["text"]
    if len(text.strip()) < MIN_USEFUL_CHARS:
        return {"success": False, "source": source,
                "error": (f"Seulement {len(text.strip())} caractères extraits : trop peu "
                          f"pour apprendre quoi que ce soit d'utile.")}

    indexed = _index_text(text, source_label=source, namespace=namespace,
                          tags=tags, chunk_chars=chunk_chars)
    if not indexed["success"]:
        return {"success": False, "source": source, "error": indexed["error"]}

    entry = {
        "source": source,
        "title": extracted.get("title", source),
        "kind": extracted.get("kind", "?"),
        "namespace": namespace,
        "tags": tags,
        "chars": len(text),
        "chunks_added": indexed["chunks_added"],
        "learned_at": time.time(),
        "learned_at_human": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _record(entry)

    return {
        "success": True,
        **entry,
        "excerpt": text[:400],
        "message": (f"{indexed['chunks_added']} fragments indexés depuis "
                    f"« {entry['title'][:60]} » ({entry['kind']})."),
    }


def learn_from_topic(topic: str, namespace: str = DEFAULT_NAMESPACE,
                     max_sources: int = 4, depth: int = 2,
                     tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Orion va chercher lui-même sur le web et indexe ce qu'il trouve.

    C'est la voie autonome : on donne un sujet, pas des liens.
    """
    from server.tools.deep_research import run_deep_research

    research = run_deep_research(query=topic, max_sources=max_sources, depth=depth)
    if not research.get("success"):
        return {"success": False, "topic": topic,
                "error": research.get("error", "Recherche infructueuse.")}

    # La synthèse elle-même vaut d'être retenue : c'est le croisement des sources.
    synthesis = (research.get("synthesis") or research.get("summary")
                 or research.get("report") or "")
    tags = (tags or []) + ["veille", _slug(topic)]

    learned, failed = [], []
    if len(str(synthesis).strip()) >= MIN_USEFUL_CHARS:
        indexed = _index_text(str(synthesis), source_label=f"veille::{topic}",
                              namespace=namespace, tags=tags)
        if indexed["success"]:
            learned.append({"source": f"veille::{topic}",
                            "chunks_added": indexed["chunks_added"]})
            _record({"source": f"veille::{topic}", "title": f"Veille — {topic}",
                     "kind": "synthèse de recherche", "namespace": namespace,
                     "tags": tags, "chunks_added": indexed["chunks_added"],
                     "learned_at": time.time(),
                     "learned_at_human": time.strftime("%Y-%m-%d %H:%M:%S")})

    for source in research.get("sources", [])[:max_sources]:
        url = source.get("url") if isinstance(source, dict) else str(source)
        if not url or not _looks_like_url(url):
            continue
        result = learn_from_source(url, namespace=namespace, tags=tags)
        if result.get("success") and not result.get("already_known"):
            learned.append({"source": url, "chunks_added": result.get("chunks_added", 0)})
        elif not result.get("success"):
            failed.append({"source": url, "error": result.get("error", "")[:120]})

    return {
        "success": bool(learned),
        "topic": topic,
        "namespace": namespace,
        "sources_learned": len(learned),
        "chunks_added": sum(item["chunks_added"] for item in learned),
        "learned": learned,
        "failed": failed,
        "error": None if learned else "Aucune source exploitable n'a pu être indexée.",
    }


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


# ════════════════════════════════════════════════════════════════════════════
# Dossier de dépôt
# ════════════════════════════════════════════════════════════════════════════

def learn_from_inbox(namespace: str = DEFAULT_NAMESPACE,
                     move_processed: bool = True,
                     max_files: int = 50) -> Dict[str, Any]:
    """Ingère tout ce qui a été déposé dans le dossier de dépôt.

    Les fichiers traités sont déplacés dans un sous-dossier plutôt que
    supprimés : Orion ne doit jamais détruire un document de l'utilisateur, et
    les laisser sur place les ferait ré-ingérer à chaque passage.
    """
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    candidates = [f for f in sorted(INBOX_DIR.iterdir())
                  if f.is_file() and not f.name.startswith(".")][:max_files]
    if not candidates:
        return {"success": True, "inbox": str(INBOX_DIR), "files_found": 0,
                "message": f"Rien à apprendre. Dépose tes documents dans {INBOX_DIR}."}

    learned, failed = [], []
    for path in candidates:
        result = learn_from_source(str(path), namespace=namespace, tags=["inbox"])
        if result.get("success"):
            learned.append({"file": path.name,
                            "chunks_added": result.get("chunks_added", 0),
                            "already_known": result.get("already_known", False)})
            if move_processed:
                PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
                try:
                    path.rename(PROCESSED_DIR / path.name)
                except OSError as exc:
                    failed.append({"file": path.name, "error": f"déplacement impossible : {exc}"})
        else:
            failed.append({"file": path.name, "error": result.get("error", "")[:150]})

    return {
        "success": True,
        "inbox": str(INBOX_DIR),
        "files_found": len(candidates),
        "files_learned": len(learned),
        "chunks_added": sum(item["chunks_added"] for item in learned),
        "learned": learned,
        "failed": failed,
        "processed_dir": str(PROCESSED_DIR) if move_processed else None,
    }


# ════════════════════════════════════════════════════════════════════════════
# Restitution
# ════════════════════════════════════════════════════════════════════════════

def knowledge_teach(topic: str, namespace: str = DEFAULT_NAMESPACE,
                    depth: int = 8, min_score: float = 0.25) -> Dict[str, Any]:
    """Rassemble ce qui est su d'un sujet, pour former ou pour appliquer.

    Ne rédige pas la leçon : renvoie la matière sourcée et laisse le modèle
    composer. Écrire le cours ici reviendrait à le figer dans du code Python.
    """
    from server.memory.rag_tools import memory_recall

    recalled = memory_recall(query=topic, top_k=int(depth),
                             min_score=float(min_score), namespace=namespace)
    hits = recalled.get("results", []) if recalled.get("success") else []

    if not hits:
        return {
            "success": False,
            "topic": topic,
            "error": f"Rien d'appris sur « {topic} » dans la base « {namespace} ».",
            "hint": ("Fais-le apprendre d'abord : learn_from_source pour un document "
                     "précis, learn_from_topic pour qu'il aille chercher lui-même."),
        }

    by_source: Dict[str, List[str]] = {}
    for hit in hits:
        by_source.setdefault(hit.get("source", "?"), []).append(hit.get("text", ""))

    return {
        "success": True,
        "topic": topic,
        "namespace": namespace,
        "extracts_count": len(hits),
        "sources_count": len(by_source),
        "sources": list(by_source),
        "material": [
            {"source": source, "extracts": extracts}
            for source, extracts in by_source.items()
        ],
        "instruction": (
            "Compose la réponse à partir de cette matière uniquement. Cite les sources. "
            "Si elle ne suffit pas à répondre, dis-le au lieu de compléter de mémoire, "
            "et propose d'apprendre une source complémentaire."
        ),
    }


def knowledge_status(namespace: Optional[str] = None) -> Dict[str, Any]:
    """Ce qu'Orion a appris, d'où, et quand."""
    from server.memory.rag_tools import memory_stats

    ledger = _load_ledger()["sources"]
    if namespace:
        ledger = [s for s in ledger if s.get("namespace") == namespace]

    by_kind: Dict[str, int] = {}
    for entry in ledger:
        kind = entry.get("kind", "?")
        by_kind[kind] = by_kind.get(kind, 0) + 1

    recent = sorted(ledger, key=lambda s: s.get("learned_at", 0), reverse=True)[:10]

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    pending = [f.name for f in INBOX_DIR.iterdir()
               if f.is_file() and not f.name.startswith(".")]

    return {
        "success": True,
        "sources_learned": len(ledger),
        "chunks_total": sum(s.get("chunks_added", 0) for s in ledger),
        "by_kind": by_kind,
        "recent_sources": [
            {"title": s.get("title", s.get("source")), "kind": s.get("kind"),
             "learned_at": s.get("learned_at_human"), "chunks": s.get("chunks_added")}
            for s in recent
        ],
        "inbox_dir": str(INBOX_DIR),
        "inbox_pending": pending,
        "vector_store": memory_stats(namespace=namespace),
        "note": ("Base de connaissances consultable. Les poids du modèle ne sont pas "
                 "modifiés : Orion répond mieux parce qu'il retrouve plus de matière, "
                 "pas parce qu'il a été ré-entraîné."),
    }


# ════════════════════════════════════════════════════════════════════════════
# Surveillance du dossier de dépôt
# ════════════════════════════════════════════════════════════════════════════

_watcher = {"active": False, "interval_sec": 120.0, "last_scan": None,
            "files_learned": 0, "last_error": None}


def inbox_watcher_status() -> Dict[str, Any]:
    return {"success": True, **_watcher, "inbox_dir": str(INBOX_DIR)}


def start_inbox_watcher(interval_sec: float = 120.0,
                        namespace: str = DEFAULT_NAMESPACE) -> Dict[str, Any]:
    """Surveille le dossier de dépôt et apprend ce qui y apparaît.

    Le premier passage charge le modèle d'embeddings (~120 Mo) : le thread est
    en démon et l'intervalle large, pour que la surveillance ne pèse pas sur le
    démarrage du serveur ni sur la machine au repos.
    """
    import threading

    if _watcher["active"]:
        return {"success": True, "already_running": True, **inbox_watcher_status()}

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    _watcher["active"] = True
    _watcher["interval_sec"] = interval_sec

    def _loop():
        while _watcher["active"]:
            try:
                pending = [f for f in INBOX_DIR.iterdir()
                           if f.is_file() and not f.name.startswith(".")]
                if pending:
                    result = learn_from_inbox(namespace=namespace)
                    _watcher["files_learned"] += result.get("files_learned", 0)
                    _watcher["last_error"] = None
                    print(f"[knowledge] {result.get('files_learned', 0)} document(s) appris "
                          f"depuis le dossier de dépôt.")
                _watcher["last_scan"] = time.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as exc:
                # Une erreur d'ingestion ne doit pas tuer la surveillance.
                _watcher["last_error"] = f"{type(exc).__name__}: {exc}"[:200]
                print(f"[knowledge!] surveillance : {_watcher['last_error']}")
            time.sleep(_watcher["interval_sec"])

    threading.Thread(target=_loop, name="orion-knowledge-inbox", daemon=True).start()
    print(f"[knowledge] Surveillance du dossier de dépôt active ({INBOX_DIR}, "
          f"toutes les {interval_sec:.0f}s).")
    return {"success": True, **inbox_watcher_status()}


def stop_inbox_watcher() -> Dict[str, Any]:
    _watcher["active"] = False
    return {"success": True, "message": "Surveillance arrêtée.", **inbox_watcher_status()}


HANDLERS = {
    "learn_from_source": lambda p: learn_from_source(**p),
    "learn_from_topic":  lambda p: learn_from_topic(**p),
    "learn_from_inbox":  lambda p: learn_from_inbox(**p),
    "knowledge_teach":   lambda p: knowledge_teach(**p),
    "knowledge_status":  lambda p: knowledge_status(**p),
}
