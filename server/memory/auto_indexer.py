# -*- coding: utf-8 -*-
"""Module de réindexation automatique du coffre Obsidian dans la mémoire RAG.

Surveille en continu le dossier du coffre (défaut: data/obsidian_journal)
et réindexe automatiquement dans le namespace 'obsidian' tout fichier créé ou modifié.
"""

import json
import os
import threading
import time
from pathlib import Path
from server.memory.rag_tools import memory_index_file

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
STATE_FILE = DATA_DIR / "memory" / "vault_index_state.json"

_watcher_state = {
    "active": False,
    "interval_sec": 30.0,
    "last_scan": None,
    "total_scanned": 0,
    "last_reindexed": 0,
}
_lock = threading.Lock()


def get_obsidian_vault_path() -> Path:
    """Retourne le chemin du coffre Obsidian depuis l'env ou fallback dans data/obsidian_journal."""
    env_path = os.getenv("ORION_OBSIDIAN_VAULT_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    vault = DATA_DIR / "obsidian_journal"
    vault.mkdir(parents=True, exist_ok=True)
    return vault


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def scan_and_reindex_vault(namespace: str = "obsidian") -> dict:
    """Parcourt le coffre Obsidian et réindexe les fichiers modifiés ou nouveaux."""
    vault = get_obsidian_vault_path()
    if not vault.exists():
        return {"success": False, "error": f"Coffre introuvable : {vault}"}

    state = _load_state()
    reindexed_files = 0
    total_chunks = 0
    failures = []

    files = [p for p in vault.rglob("*") if p.is_file() and p.suffix.lower() in (".md", ".txt", ".markdown")]

    for p in files:
        key = str(p.resolve())
        mtime = p.stat().st_mtime
        last_mtime = state.get(key)

        # Si le fichier est nouveau ou a été modifié depuis le dernier scan
        if last_mtime is None or mtime > last_mtime:
            res = memory_index_file(str(p), namespace=namespace, chunk_chars=400)
            if res.get("success"):
                state[key] = mtime
                reindexed_files += 1
                total_chunks += res.get("chunks_added", 0)
            else:
                failures.append({"path": str(p), "error": res.get("error")})

    _save_state(state)

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    with _lock:
        _watcher_state["last_scan"] = now_str
        _watcher_state["total_scanned"] = len(files)
        _watcher_state["last_reindexed"] = reindexed_files

    return {
        "success": True,
        "vault": str(vault),
        "namespace": namespace,
        "total_files_scanned": len(files),
        "reindexed_files": reindexed_files,
        "chunks_added": total_chunks,
        "failures": failures[:5],
        "timestamp": now_str,
    }


def vault_reindex_now() -> dict:
    """Déclenche immédiatement une passe de réindexation du coffre Obsidian."""
    return scan_and_reindex_vault()


def vault_reindex_status() -> dict:
    """Retourne l'état courant du service de surveillance et de réindexation du coffre."""
    with _lock:
        st = dict(_watcher_state)
    st["vault_path"] = str(get_obsidian_vault_path())
    return {"success": True, "status": st}


def start_vault_watcher(interval_sec: float = 30.0):
    """Démarre le thread de surveillance du coffre Obsidian en arrière-plan."""
    with _lock:
        if _watcher_state["active"]:
            return
        _watcher_state["active"] = True
        _watcher_state["interval_sec"] = interval_sec

    def _loop():
        print(f"[AUTO INDEXER] Démarrage de la surveillance du coffre Obsidian ({interval_sec}s)...", flush=True)
        while True:
            try:
                scan_and_reindex_vault()
            except Exception as exc:
                print(f"[AUTO INDEXER!] Erreur scan : {exc}", flush=True)
            time.sleep(interval_sec)

    threading.Thread(target=_loop, daemon=True).start()
