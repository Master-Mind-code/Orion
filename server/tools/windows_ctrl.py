"""
Orion Tool — Gestion des fenêtres du bureau (PyGetWindow + Win32).

Lister, mettre au premier plan, réduire/agrandir/déplacer/redimensionner/fermer.

Windows principalement : PyGetWindow gère aussi macOS partiellement, mais
focus_window s'appuie sur l'API Win32 en secours. Sur Linux, ces tools
renvoient une erreur explicite plutôt que de planter.

⚠ Sous ORION_AUTOMATION_ENABLED, comme le reste du contrôle du bureau.
list_windows reste en lecture seule et n'est pas soumis à l'interrupteur.
"""
from __future__ import annotations

import sys
import time

from .automation import _enabled, _disabled_response, _missing


def _import_gw():
    try:
        import pygetwindow as gw  # type: ignore[import-not-found]
        return gw
    except ImportError:
        return None


def _visible_windows(gw) -> list:
    """Fenêtres réellement affichables : titre non vide et géométrie valide."""
    out = []
    for w in gw.getAllWindows():
        try:
            if w.title.strip() and w.width > 0 and w.height > 0:
                out.append(w)
        except Exception:
            continue
    return out


def _describe(w) -> dict:
    state = []
    try:
        if w.isMinimized:
            state.append("minimized")
        if w.isMaximized:
            state.append("maximized")
        if w.isActive:
            state.append("active")
    except Exception:
        pass
    return {
        "title": w.title,
        "x": w.left, "y": w.top,
        "width": w.width, "height": w.height,
        "state": state,
    }


def list_windows() -> dict:
    """Liste les fenêtres ouvertes avec position, taille et état.

    Une fenêtre réduite est rapportée par Windows en 237x39 @ (-32000,-32000) :
    c'est la convention du système, pas une erreur. Pour agir dessus, passer par
    focus_window (qui la restaure) et non par ses coordonnées.
    """
    gw = _import_gw()
    if gw is None:
        return _missing("pygetwindow")
    try:
        wins = [_describe(w) for w in _visible_windows(gw)]
        return {"success": True, "count": len(wins), "windows": wins}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def _find(gw, title_contains: str):
    needle = str(title_contains).lower()
    matches = [w for w in _visible_windows(gw) if needle in w.title.lower()]
    if not matches:
        raise LookupError(
            f"Aucune fenêtre dont le titre contient {title_contains!r}. "
            "Utilise list_windows pour voir les titres exacts."
        )
    return matches[0]


def _is_foreground(hwnd) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        return ctypes.windll.user32.GetForegroundWindow() == hwnd
    except Exception:
        return False


def _force_foreground(hwnd) -> None:
    """Contourne le verrou anti-vol de focus de Windows.

    Un process qui ne possède pas déjà le premier plan n'a pas le droit de le
    prendre : SetForegroundWindow échoue silencieusement (il fait juste clignoter
    la barre des tâches). Simuler un appui sur ALT fait croire au système que le
    process vient de recevoir une entrée utilisateur, ce qui lève le verrou.
    """
    import ctypes
    u = ctypes.windll.user32
    VK_MENU, KEYEVENTF_KEYUP = 0x12, 0x0002
    u.ShowWindow(hwnd, 9)  # SW_RESTORE
    u.keybd_event(VK_MENU, 0, 0, 0)
    u.SetForegroundWindow(hwnd)
    u.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)


def focus_window(title_contains: str) -> dict:
    """Met au premier plan la première fenêtre dont le titre contient le texte.

    Le résultat contient 'focused' : True seulement si la fenêtre est réellement
    au premier plan APRÈS vérification. Ne jamais taper au clavier sans avoir
    contrôlé ce champ — Windows peut refuser le changement de focus.
    """
    if not _enabled():
        return _disabled_response()
    gw = _import_gw()
    if gw is None:
        return _missing("pygetwindow")
    try:
        w = _find(gw, title_contains)
    except LookupError as exc:
        return {"success": False, "error": str(exc)}

    hwnd = getattr(w, "_hWnd", None)
    try:
        if w.isMinimized:
            w.restore()
        w.activate()
    except Exception:
        pass
    time.sleep(0.25)

    # activate() ment : il ne lève pas toujours d'exception quand Windows a
    # refusé le premier plan. On vérifie, puis on insiste.
    if hwnd is not None and sys.platform == "win32" and not _is_foreground(hwnd):
        try:
            _force_foreground(hwnd)
            time.sleep(0.3)
        except Exception as exc:
            return {"success": False, "focused": False,
                    "error": f"{type(exc).__name__}: {exc}"}

    focused = _is_foreground(hwnd) if hwnd is not None else False
    if sys.platform != "win32":
        # Pas de vérification fiable ailleurs : on ne prétend rien.
        return {"success": True, "focused": None, "window": _describe(w)}
    if not focused:
        return {
            "success": False,
            "focused": False,
            "window": _describe(w),
            "error": "Windows a refusé de mettre cette fenêtre au premier plan. "
                     "Ne pas taper au clavier : la frappe irait dans la fenêtre "
                     "active actuelle. Réessayer, ou demander à l'utilisateur de "
                     "cliquer sur la fenêtre.",
        }
    return {"success": True, "focused": True, "window": _describe(w)}


def window_control(
    title_contains: str,
    action: str,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict:
    """Agit sur une fenêtre.

    action : minimize | maximize | restore | close | move (x,y) | resize (width,height).
    'close' ferme la fenêtre — le contenu non enregistré peut être perdu.
    """
    if not _enabled():
        return _disabled_response()
    gw = _import_gw()
    if gw is None:
        return _missing("pygetwindow")
    try:
        w = _find(gw, title_contains)
    except LookupError as exc:
        return {"success": False, "error": str(exc)}

    act = str(action).strip().lower()
    try:
        if act == "minimize":
            w.minimize()
        elif act == "maximize":
            w.maximize()
        elif act == "restore":
            w.restore()
        elif act == "close":
            title = w.title
            w.close()
            return {"success": True, "action": "close", "closed": title}
        elif act == "move":
            if x is None or y is None:
                return {"success": False, "error": "move exige x et y."}
            w.moveTo(int(x), int(y))
        elif act == "resize":
            if width is None or height is None:
                return {"success": False, "error": "resize exige width et height."}
            w.resizeTo(int(width), int(height))
        else:
            return {"success": False,
                    "error": f"Action inconnue : {action!r}. Attendu : "
                             "minimize|maximize|restore|close|move|resize."}
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    return {"success": True, "action": act, "window": _describe(w)}


def window_watch(
    title_contains: str,
    condition: str = "closed",
    target_text: str | None = None,
    timeout_sec: int = 300,
    poll_interval: float = 2.0,
) -> dict:
    """Surveille une fenêtre en arrière-plan et envoie une notification quand la condition est remplie.

    condition: 'closed' | 'title_changed' | 'text_appeared' | 'text_disappeared'
    """
    import threading

    def _watch_task():
        gw = _import_gw()
        if gw is None:
            return
        
        t_start = time.time()
        timeout = float(timeout_sec)
        interval = max(0.5, float(poll_interval))
        initial_title = None

        try:
            w_init = _find(gw, title_contains)
            initial_title = w_init.title
        except LookupError:
            pass

        triggered = False
        reason = ""

        while time.time() - t_start < timeout:
            time.sleep(interval)
            try:
                w_current = _find(gw, title_contains)
            except LookupError:
                if condition == "closed":
                    triggered = True
                    reason = f"La fenêtre '{title_contains}' est maintenant fermée."
                    break
                w_current = None

            if w_current:
                if condition == "title_changed" and initial_title and w_current.title != initial_title:
                    triggered = True
                    reason = f"Le titre de la fenêtre a changé : '{w_current.title}'"
                    break

                if target_text and condition in ("text_appeared", "text_disappeared"):
                    if target_text.lower() in w_current.title.lower():
                        if condition == "text_appeared":
                            triggered = True
                            reason = f"Le texte '{target_text}' est apparu dans le titre."
                            break
                    else:
                        if condition == "text_disappeared":
                            triggered = True
                            reason = f"Le texte '{target_text}' a disparu du titre."
                            break

        if triggered:
            msg = f"🔔 Surveillance de fenêtre : {reason}"
            print(f"[WINDOW WATCH] {msg}", flush=True)
            try:
                from server.tools.notifications import notify
                notify("Orion · Surveillance Fenêtre", reason)
            except Exception:
                pass
            try:
                from server.tools.notifications import notify_telegram
                notify_telegram(msg)
            except Exception:
                pass

    threading.Thread(target=_watch_task, daemon=True).start()

    return {
        "success": True,
        "title_contains": title_contains,
        "condition": condition,
        "timeout_sec": timeout_sec,
        "message": f"Surveillance lancée en arrière-plan pour la fenêtre '{title_contains}' (condition={condition}).",
    }


HANDLERS = {
    "list_windows": lambda p: list_windows(),
    "focus_window": lambda p: focus_window(**p),
    "window_control": lambda p: window_control(**p),
    "window_watch": lambda p: window_watch(**p),
}

