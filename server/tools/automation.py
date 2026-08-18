"""
Orion Tool — Automation souris/clavier/presse-papier (PyAutoGUI + Win32).

⚠ Outils sensibles : peut prendre le contrôle de la machine.
Désactivés par défaut. Active avec ORION_AUTOMATION_ENABLED=true dans .env.

Deux garde-fous en plus de l'interrupteur :
  - Failsafe PyAutoGUI : déplacer la souris dans le coin haut-gauche déclenche
    une exception et coupe l'automation immédiatement.
  - server/confirm.py : les tools listés dans DEFAULT_DANGEROUS demandent le
    mot de passe avant de s'exécuter.

Les coordonnées sont TOUJOURS celles du bureau virtuel (multi-écran, valeurs
négatives possibles sur un écran placé à gauche du principal), jamais celles
d'une image redimensionnée.
"""
from __future__ import annotations

import os
import sys
import time

# ── Conscience DPI ──────────────────────────────────────────────────────────
# Indispensable AVANT le premier import de pyautogui/mss : sans ça, sur un écran
# avec mise à l'échelle Windows (125 %, 150 %...), les coordonnées rendues par
# une capture ne correspondent pas à celles de la souris.
def ensure_dpi_aware() -> None:
    """Déclare le process conscient du DPI. Idempotent, sans effet hors Windows.

    Appelé à l'import de ce module et par screenshot.py, qui peut être importé
    en premier : l'appel doit précéder toute utilisation de mss/pyautogui.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


ensure_dpi_aware()


def _enabled() -> bool:
    return os.getenv("ORION_AUTOMATION_ENABLED", "false").strip().lower() in (
        "1", "true", "yes", "on", "oui",
    )


def _disabled_response() -> dict:
    return {
        "success": False,
        "error": "Automation désactivée. Active avec ORION_AUTOMATION_ENABLED=true dans .env.\n"
                 "Failsafe PyAutoGUI : bouge la souris dans le coin haut-gauche pour couper.",
    }


def _import_pyautogui():
    try:
        import pyautogui  # type: ignore[import-not-found]
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.02
        return pyautogui
    except ImportError:
        return None


def _missing(pkg: str, extra: str = "requirements-extras.txt") -> dict:
    return {"success": False,
            "error": f"{pkg} n'est pas installé. Installe avec :\n    pip install -r {extra}"}


def _move(pg, x: int, y: int) -> None:
    """Déplacement absolu du curseur.

    Sur Windows on passe par SetCursorPos plutôt que pyautogui.moveTo : pyautogui
    borne les coordonnées à l'écran principal et rend inatteignable un second
    écran placé à gauche ou au-dessus (coordonnées négatives).
    """
    pg.failSafeCheck()
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
        time.sleep(0.03)
    else:
        pg.moveTo(int(x), int(y))


# ════════════════════════════════════════════════════════════════════════════
# État
# ════════════════════════════════════════════════════════════════════════════

def automation_status() -> dict:
    """État de l'interrupteur + géométrie des écrans + position souris.

    À appeler avant toute séquence de contrôle : donne les bornes du bureau
    virtuel dans lesquelles les coordonnées doivent tomber.
    """
    pg = _import_pyautogui()
    out: dict = {
        "success": True,
        "enabled": _enabled(),
        "hint": "Coordonnées = bureau virtuel, pas l'image d'une capture réduite.",
    }
    if not _enabled():
        out["hint"] = ("Automation désactivée : seuls mouse_position, automation_status "
                       "et les lectures répondent. Active ORION_AUTOMATION_ENABLED=true.")
    if pg is not None:
        x, y = pg.position()
        out["mouse"] = {"x": x, "y": y}
    try:
        import mss
        with mss.mss() as sct:
            virt = sct.monitors[0]
            out["virtual_desktop"] = {
                "left": virt["left"], "top": virt["top"],
                "width": virt["width"], "height": virt["height"],
            }
            out["monitors"] = [
                {"index": i, "left": m["left"], "top": m["top"],
                 "width": m["width"], "height": m["height"]}
                for i, m in enumerate(sct.monitors) if i > 0
            ]
    except ImportError:
        out["monitors"] = "mss non installé"
    return out


# ════════════════════════════════════════════════════════════════════════════
# Souris
# ════════════════════════════════════════════════════════════════════════════

def mouse_position() -> dict:
    """Position actuelle de la souris (lecture seule, toujours autorisée)."""
    pg = _import_pyautogui()
    if pg is None:
        return _missing("pyautogui")
    x, y = pg.position()
    sw, sh = pg.size()
    return {"success": True, "x": x, "y": y, "screen_width": sw, "screen_height": sh}


def mouse_move(x: int, y: int, duration: float = 0.2) -> dict:
    if not _enabled():
        return _disabled_response()
    pg = _import_pyautogui()
    if pg is None:
        return _missing("pyautogui")
    try:
        _move(pg, x, y)
        return {"success": True, "x": int(x), "y": int(y)}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def mouse_click(
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
    clicks: int = 1,
) -> dict:
    if not _enabled():
        return _disabled_response()
    pg = _import_pyautogui()
    if pg is None:
        return _missing("pyautogui")
    if button not in ("left", "right", "middle"):
        return {"success": False, "error": "button doit être left|right|middle"}
    try:
        if x is not None and y is not None:
            _move(pg, x, y)
        pg.click(button=button, clicks=int(clicks), interval=0.08)
        return {"success": True, "button": button, "clicks": int(clicks),
                "x": x, "y": y}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def mouse_drag(
    from_x: int, from_y: int, to_x: int, to_y: int,
    duration: float = 0.6, button: str = "left",
) -> dict:
    """Glisser-déposer d'un point à un autre (sélection, déplacement d'icône...)."""
    if not _enabled():
        return _disabled_response()
    pg = _import_pyautogui()
    if pg is None:
        return _missing("pyautogui")
    if button not in ("left", "right", "middle"):
        return {"success": False, "error": "button doit être left|right|middle"}
    try:
        _move(pg, from_x, from_y)
        pg.mouseDown(button=button)
        try:
            steps = max(6, int(float(duration) / 0.03))
            for i in range(1, steps + 1):
                _move(pg,
                      int(from_x + (to_x - from_x) * i / steps),
                      int(from_y + (to_y - from_y) * i / steps))
        finally:
            # Sans ça, un failsafe en plein glisser laisse le bouton enfoncé et
            # la machine devient inutilisable à la souris.
            pg.mouseUp(button=button)
        return {"success": True, "from": [int(from_x), int(from_y)],
                "to": [int(to_x), int(to_y)]}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def mouse_scroll(
    x: int | None = None, y: int | None = None,
    amount: int = 5, direction: str = "down",
) -> dict:
    """Molette. direction : up|down|left|right. amount = nombre de crans."""
    if not _enabled():
        return _disabled_response()
    pg = _import_pyautogui()
    if pg is None:
        return _missing("pyautogui")
    if direction not in ("up", "down", "left", "right"):
        return {"success": False, "error": "direction doit être up|down|left|right"}
    try:
        if x is not None and y is not None:
            _move(pg, x, y)
        clicks = int(amount) * 120
        if direction in ("up", "down"):
            pg.scroll(clicks if direction == "up" else -clicks)
        else:
            pg.hscroll(clicks if direction == "right" else -clicks)
        return {"success": True, "direction": direction, "amount": int(amount)}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


# ════════════════════════════════════════════════════════════════════════════
# Clavier
# ════════════════════════════════════════════════════════════════════════════

def keyboard_type(text: str, interval: float = 0.02) -> dict:
    """Tape du texte dans la fenêtre active.

    Pour les accents et les textes longs, clipboard_set + keyboard_key('ctrl+v')
    est nettement plus fiable : typewrite passe par les scancodes du clavier US.
    """
    if not _enabled():
        return _disabled_response()
    pg = _import_pyautogui()
    if pg is None:
        return _missing("pyautogui")
    try:
        pg.typewrite(text, interval=float(interval))
        return {"success": True, "typed_chars": len(text)}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def keyboard_press(keys: str | list[str]) -> dict:
    """Touche unique ('enter', 'esc', 'f5') ou hotkey (['ctrl', 'c'] = Ctrl+C)."""
    if not _enabled():
        return _disabled_response()
    pg = _import_pyautogui()
    if pg is None:
        return _missing("pyautogui")
    try:
        if isinstance(keys, str):
            pg.press(keys)
            return {"success": True, "pressed": keys}
        pg.hotkey(*keys)
        return {"success": True, "hotkey": "+".join(keys)}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def keyboard_key(keys: str) -> dict:
    """Combinaisons sous forme de texte, plus pratique que keyboard_press.

    Exemples : 'enter', 'ctrl+c', 'ctrl+shift+n', 'alt+tab', 'win+d'.
    Plusieurs appuis successifs séparés par des espaces : 'ctrl+a ctrl+c'.
    """
    if not _enabled():
        return _disabled_response()
    pg = _import_pyautogui()
    if pg is None:
        return _missing("pyautogui")
    try:
        done = []
        for combo in str(keys).split():
            parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
            if not parts:
                continue
            if len(parts) == 1:
                pg.press(parts[0])
            else:
                pg.hotkey(*parts)
            done.append(combo)
            time.sleep(0.05)
        if not done:
            return {"success": False, "error": "Aucune touche reconnue."}
        return {"success": True, "sent": done}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


# ════════════════════════════════════════════════════════════════════════════
# Presse-papier
# ════════════════════════════════════════════════════════════════════════════

def clipboard_get() -> dict:
    """Lit le contenu texte du presse-papier."""
    try:
        import pyperclip  # type: ignore[import-not-found]
    except ImportError:
        return _missing("pyperclip")
    try:
        content = pyperclip.paste()
        return {"success": True, "content": content,
                "length": len(content) if content else 0}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def clipboard_set(text: str) -> dict:
    """Place du texte dans le presse-papier (à coller ensuite avec ctrl+v)."""
    if not _enabled():
        return _disabled_response()
    try:
        import pyperclip  # type: ignore[import-not-found]
    except ImportError:
        return _missing("pyperclip")
    try:
        pyperclip.copy(text)
        return {"success": True, "length": len(text)}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


HANDLERS = {
    "automation_status": lambda p: automation_status(),
    "mouse_position": lambda p: mouse_position(),
    "mouse_move": lambda p: mouse_move(**p),
    "mouse_click": lambda p: mouse_click(**p),
    "mouse_drag": lambda p: mouse_drag(**p),
    "mouse_scroll": lambda p: mouse_scroll(**p),
    "keyboard_type": lambda p: keyboard_type(**p),
    "keyboard_press": lambda p: keyboard_press(**p),
    "keyboard_key": lambda p: keyboard_key(**p),
    "clipboard_get": lambda p: clipboard_get(),
    "clipboard_set": lambda p: clipboard_set(**p),
}
