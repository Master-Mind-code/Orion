# -*- coding: utf-8 -*-
"""Module de rotation et nettoyage automatique des captures d'écran et clichés d'Orion.

Évite l'accumulation indéfinie de fichiers PNG/JPG dans data/screenshots, data/captures, etc.
"""

import os
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CAPTURE_DIRS = [
    ROOT_DIR / "data" / "screenshots",
    ROOT_DIR / "data" / "captures",
    ROOT_DIR / "data" / "camera_snapshots",
    ROOT_DIR / "data" / "images",
]


def rotate_captures(
    max_files: int = 100,
    max_age_days: int = 7,
    max_total_mb: float = 500.0,
) -> dict:
    """Effectue la rotation des fichiers de captures et images temporaires."""
    now = time.time()
    cutoff_time = now - (max_age_days * 86400)
    deleted_count = 0
    bytes_freed = 0

    all_files = []

    # 1. Collecte tous les fichiers des répertoires de captures
    for d in CAPTURE_DIRS:
        if not d.exists():
            continue
        for p in d.glob("*"):
            if p.is_file():
                try:
                    stat = p.stat()
                    all_files.append({
                        "path": p,
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                    })
                except Exception:
                    pass

    # Sort par date de modification (les plus anciens d'abord)
    all_files.sort(key=lambda x: x["mtime"])

    remaining_files = []

    # 2. Suppression des fichiers trop anciens (> max_age_days)
    for item in all_files:
        if item["mtime"] < cutoff_time:
            try:
                item["path"].unlink(missing_ok=True)
                deleted_count += 1
                bytes_freed += item["size"]
            except Exception as exc:
                print(f"[CAPTURE ROTATION] Impossible de supprimer {item['path']} : {exc}")
        else:
            remaining_files.append(item)

    # 3. Limite en nombre de fichiers
    if len(remaining_files) > max_files:
        excess_count = len(remaining_files) - max_files
        to_delete = remaining_files[:excess_count]
        remaining_files = remaining_files[excess_count:]

        for item in to_delete:
            try:
                item["path"].unlink(missing_ok=True)
                deleted_count += 1
                bytes_freed += item["size"]
            except Exception as exc:
                print(f"[CAPTURE ROTATION] Impossible de supprimer {item['path']} : {exc}")

    # 4. Limite en espace disque total (MB)
    max_bytes = max_total_mb * 1024 * 1024
    total_size = sum(item["size"] for item in remaining_files)

    while total_size > max_bytes and remaining_files:
        item = remaining_files.pop(0)
        try:
            item["path"].unlink(missing_ok=True)
            deleted_count += 1
            bytes_freed += item["size"]
            total_size -= item["size"]
        except Exception as exc:
            print(f"[CAPTURE ROTATION] Impossible de supprimer {item['path']} : {exc}")

    freed_mb = round(bytes_freed / (1024 * 1024), 2)
    return {
        "success": True,
        "deleted_files": deleted_count,
        "freed_mb": freed_mb,
        "remaining_files": len(remaining_files),
    }


HANDLERS = {
    "rotate_captures": lambda p: rotate_captures(**p),
}
