"""
Client MCP stdio minimal — permet à Orion de consommer n'importe quel serveur
MCP (TradingView, MetaTrader 5, contrôle du bureau...).

Protocole : JSON-RPC 2.0 en lignes délimitées par \\n sur stdin/stdout du
process serveur. Un thread lecteur dépile les réponses et les distribue aux
appelants via des Event, ce qui rend l'API synchrone — les handlers de tools
Orion sont synchrones.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from typing import Any

# Version du protocole annoncée à l'initialisation. Les serveurs récents
# répondent avec la leur ; on ne coupe pas la connexion en cas d'écart, la
# plupart des implémentations restent compatibles.
PROTOCOL_VERSION = "2025-06-18"


class MCPError(RuntimeError):
    pass


class MCPStdioClient:
    """Un process serveur MCP, maintenu vivant, interrogeable de façon synchrone."""

    def __init__(self, alias: str, command: str, args: list[str] | None = None,
                 env: dict[str, str] | None = None, cwd: str | None = None,
                 timeout: float = 30.0):
        self.alias = alias
        self.command = command
        self.args = list(args or [])
        self.env = env or {}
        self.cwd = cwd
        self.timeout = float(timeout)

        self._proc: subprocess.Popen | None = None
        self._id = 0
        self._lock = threading.Lock()
        self._pending: dict[int, dict] = {}
        self._reader: threading.Thread | None = None
        self._stderr_tail: list[str] = []
        self.server_info: dict = {}

    # ── cycle de vie ─────────────────────────────────────────────────────

    def start(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        import os
        environ = os.environ.copy()
        environ.update(self.env)
        # CREATE_NO_WINDOW : sans ça, chaque serveur ouvre une console sur Windows.
        flags = 0
        if sys.platform == "win32":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._proc = subprocess.Popen(
            [self.command, *self.args],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            cwd=self.cwd, env=environ, creationflags=flags,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        self._handshake()

    def stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # ── transport ────────────────────────────────────────────────────────

    def _read_loop(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                # Certains serveurs polluent stdout avec des logs : on ignore.
                continue
            mid = msg.get("id")
            if mid is None:
                continue  # notification serveur, rien à réveiller
            slot = self._pending.get(mid)
            if slot is not None:
                slot["response"] = msg
                slot["event"].set()

    def _drain_stderr(self) -> None:
        """Garde les dernières lignes de stderr : sans ça, un serveur qui refuse
        de démarrer ne donne aucun indice, et le pipe plein finit par le bloquer."""
        proc = self._proc
        if proc is None or proc.stderr is None:
            return
        for line in proc.stderr:
            self._stderr_tail.append(line.rstrip())
            del self._stderr_tail[:-20]

    def _notify(self, method: str, params: dict | None = None) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _write(self, payload: dict) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            raise MCPError(f"[{self.alias}] serveur non démarré")
        with self._lock:
            proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            proc.stdin.flush()

    def _request(self, method: str, params: dict | None = None,
                 timeout: float | None = None) -> Any:
        if not self.alive():
            raise MCPError(f"[{self.alias}] process mort. stderr: "
                           f"{' | '.join(self._stderr_tail[-3:]) or '(vide)'}")
        with self._lock:
            self._id += 1
            mid = self._id
        slot = {"event": threading.Event(), "response": None}
        self._pending[mid] = slot
        try:
            self._write({"jsonrpc": "2.0", "id": mid, "method": method,
                         "params": params or {}})
            if not slot["event"].wait(timeout or self.timeout):
                raise MCPError(f"[{self.alias}] pas de réponse à {method} "
                               f"en {timeout or self.timeout:.0f}s")
            resp = slot["response"] or {}
        finally:
            self._pending.pop(mid, None)
        if "error" in resp:
            err = resp["error"]
            raise MCPError(f"[{self.alias}] {err.get('message')} "
                           f"(code {err.get('code')})")
        return resp.get("result")

    def _handshake(self) -> None:
        result = self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "orion", "version": "1.0"},
        }, timeout=self.timeout)
        self.server_info = (result or {}).get("serverInfo", {})
        self._notify("notifications/initialized")
        time.sleep(0.05)

    # ── API MCP ──────────────────────────────────────────────────────────

    def list_tools(self) -> list[dict]:
        """Tous les tools du serveur, en suivant la pagination par curseur."""
        tools: list[dict] = []
        cursor = None
        for _ in range(20):  # borne dure : évite une boucle infinie sur curseur buggé
            params = {"cursor": cursor} if cursor else {}
            result = self._request("tools/list", params) or {}
            tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            if not cursor:
                break
        return tools

    def call_tool(self, name: str, arguments: dict,
                  timeout: float | None = None) -> dict:
        result = self._request("tools/call",
                               {"name": name, "arguments": arguments or {}},
                               timeout=timeout) or {}
        return _flatten_result(result)


def _flatten_result(result: dict) -> dict:
    """Réduit un résultat MCP à quelque chose d'exploitable par le LLM d'Orion.

    Un serveur renvoie content=[{type:text,...}] et parfois structuredContent.
    On privilégie le structuré, sinon on tente de décoder le texte en JSON.
    """
    is_error = bool(result.get("isError"))
    if "structuredContent" in result:
        data = result["structuredContent"]
        return {"success": not is_error, "result": data}

    parts = []
    for block in result.get("content", []) or []:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif block.get("type") == "image":
            parts.append("[image renvoyée par le serveur MCP, non transmise]")
    texte = "\n".join(p for p in parts if p).strip()

    if texte:
        try:
            return {"success": not is_error, "result": json.loads(texte)}
        except (json.JSONDecodeError, ValueError):
            pass
    if is_error:
        return {"success": False, "error": texte or "erreur MCP sans détail"}
    return {"success": True, "result": texte}
