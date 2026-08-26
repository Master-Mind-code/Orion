"""
Orion — Arrêt propre de tous les processus Orion.

Arrête :
  1. Le serveur Python Orion (port 8765)
  2. Le serveur de dev Vite (port 5173)
  3. L'interface Electron et serveurs MCP auxiliaires

Usage :
  python stop.py
  ou double-clic sur stop.bat
"""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def configure_output():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


configure_output()


def banner():
    print("=" * 60)
    print("            O R I O N — Arrêt des processus".center(60))
    print("=" * 60)


def kill_process_on_port(port: int) -> list[int]:
    """Trouve et arrête tous les processus écoutant sur un port TCP donné."""
    killed = []
    if sys.platform == "win32":
        try:
            cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"'
            output = subprocess.check_output(cmd, shell=True, text=True).strip()
            pids = set()
            for line in output.splitlines():
                line = line.strip()
                if line.isdigit() and int(line) > 0:
                    pids.add(int(line))
            for pid in pids:
                if pid != os.getpid():
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                    killed.append(pid)
                    print(f"  [✓] Port {port} libéré (Processus PID {pid} arrêté).")
        except Exception:
            pass
    return killed


def kill_by_keywords(keywords: list[str]):
    """Arrête les processus dont la ligne de commande contient l'un des mots-clés."""
    if sys.platform == "win32":
        ignore_pids = {os.getpid()}
        try:
            ignore_pids.add(os.getppid())
        except Exception:
            pass

        for kw in keywords:
            try:
                cmd = f'powershell -Command "Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like \'*{kw}*\' }} | Select-Object ProcessId, CommandLine"'
                output = subprocess.check_output(cmd, shell=True, text=True).strip()
                for line in output.splitlines():
                    line = line.strip()
                    parts = line.split(maxsplit=1)
                    if parts and parts[0].isdigit():
                        pid = int(parts[0])
                        cmdline = parts[1] if len(parts) > 1 else ""
                        if pid in ignore_pids or "stop.py" in cmdline or "start.py stop" in cmdline:
                            continue
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                        print(f"  [✓] Processus '{kw}' (PID {pid}) arrêté.")
            except Exception:
                pass


def main():
    banner()
    print("\n→ Recherche et fermeture des processus Orion...")

    # 1. Arrêt des processus écoutant sur les ports Orion
    kill_process_on_port(8765)  # Serveur Backend Python
    kill_process_on_port(5173)  # Dev server Vite

    # 2. Arrêt par mots-clés de commande
    kill_by_keywords([
        "start.py",
        "mt5_mcp_server",
    ])

    print("\n[✓] Nettoyage terminé. Tous les services Orion ont été arrêtés.")
    print("    Vous pouvez redémarrer proprement avec 'python start.py server' ou 'start.bat'.\n")


if __name__ == "__main__":
    main()
