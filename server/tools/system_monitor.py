"""
Tool LLM & API pour surveiller la santé système, la charge processeur, la mémoire et les processus.

Usages :
    "Quel est l'état d'utilisation CPU et RAM du serveur ?"
    "Quels sont les processus les plus gourmands ?"
"""
from __future__ import annotations

import os
import platform
import sys
import time

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_system_metrics() -> dict:
    """Retourne les métriques système actuelles (CPU, Mémoire, Disque, OS, Uptime)."""
    uname = platform.uname()
    metrics = {
        "success": True,
        "timestamp": time.time(),
        "system": {
            "os": f"{uname.system} {uname.release}",
            "machine": uname.machine,
            "processor": uname.processor or uname.machine,
            "python_version": sys.version.split()[0],
        },
    }

    if HAS_PSUTIL:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time

        metrics["cpu"] = {
            "usage_percent": cpu_pct,
            "cores_logical": cpu_count,
        }
        metrics["memory"] = {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "available_gb": round(mem.available / (1024 ** 3), 2),
            "usage_percent": mem.percent,
        }
        metrics["disk"] = {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "usage_percent": disk.percent,
        }
        metrics["uptime_hours"] = round(uptime_seconds / 3600, 2)
    else:
        metrics["cpu"] = {"usage_percent": 0.0, "note": "psutil non disponible"}
        metrics["memory"] = {"usage_percent": 0.0, "note": "psutil non disponible"}
        metrics["disk"] = {"usage_percent": 0.0, "note": "psutil non disponible"}
        metrics["uptime_hours"] = 0.0

    return metrics


def list_running_processes(limit: int = 15, sort_by: str = "cpu") -> dict:
    """Liste les N principaux processus en cours d'exécution.
    
    sort_by: 'cpu' ou 'memory'
    """
    limit = max(1, min(int(limit or 15), 50))
    if not HAS_PSUTIL:
        return {"success": False, "error": "Le paquet psutil est requis pour lister les processus."}

    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
        try:
            info = proc.info
            procs.append({
                "pid": info['pid'],
                "name": info['name'],
                "cpu_percent": round(info['cpu_percent'] or 0.0, 1),
                "memory_percent": round(info['memory_percent'] or 0.0, 1),
                "status": info['status'],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    sort_key = "memory_percent" if sort_by.lower() == "memory" else "cpu_percent"
    procs.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
    top_procs = procs[:limit]

    return {
        "success": True,
        "count": len(top_procs),
        "sorted_by": sort_by,
        "processes": top_procs,
    }


HANDLERS = {
    "get_system_metrics": lambda p: get_system_metrics(),
    "list_running_processes": lambda p: list_running_processes(**p),
}
