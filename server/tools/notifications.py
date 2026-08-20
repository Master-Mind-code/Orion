"""
Orion Tool — Notifications système (toast).

Windows : winotify (toast moderne).
Linux   : notify-send (libnotify).
macOS   : osascript display notification.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import time


def _system() -> str:
    return platform.system().lower()


def notify(title: str, message: str = "", duration: str = "short") -> dict:
    """Affiche une notification système. duration: 'short' | 'long' (Windows uniquement)."""
    title = (title or "Orion").strip()
    message = (message or "").strip()
    osname = _system()

    if osname == "windows":
        try:
            from winotify import Notification, audio
        except ImportError:
            return {
                "success": False,
                "error": "winotify n'est pas installé. Installe avec :\n"
                         "    pip install -r requirements-extras.txt",
            }
        toast = Notification(
            app_id="Orion",
            title=title,
            msg=message,
            duration=duration if duration in ("short", "long") else "short",
        )
        try:
            toast.set_audio(audio.Default, loop=False)
        except Exception:
            pass
        toast.show()
        return {"success": True, "message": f"Notification affichée : {title}"}

    if osname == "linux":
        if not shutil.which("notify-send"):
            return {"success": False, "error": "notify-send introuvable (paquet libnotify-bin)"}
        try:
            subprocess.run(["notify-send", title, message], check=False, timeout=5)
            return {"success": True, "message": f"Notification : {title}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if osname == "darwin":
        # Échappe les guillemets dans le texte
        safe_msg = message.replace('"', '\\"')
        safe_title = title.replace('"', '\\"')
        script = f'display notification "{safe_msg}" with title "{safe_title}"'
        try:
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
            return {"success": True, "message": f"Notification : {title}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    return {"success": False, "error": f"OS non supporté : {osname}"}


def notify_telegram(message: str, photo_path: str | None = None) -> dict:
    """Envoie une notification mobile via Telegram (message texte et/ou photo)."""
    message = (message or "").strip()
    if not message and not photo_path:
        return {"success": False, "error": "Message ou photo_path requis."}

    try:
        from server.vision.alerts.telegram import AlerteTelegram
    except ImportError as exc:
        return {"success": False, "error": f"Erreur import Telegram : {exc}"}

    alerte = AlerteTelegram(cooldown=0)
    if not alerte.actif:
        return {
            "success": False,
            "error": "Telegram non configuré. Ajoute TELEGRAM_TOKEN et TELEGRAM_CHAT_ID dans .env ou config.json."
        }

    if photo_path:
        from pathlib import Path
        p = Path(photo_path).expanduser()
        if not p.exists():
            return {"success": False, "error": f"Photo introuvable : {p}"}
        try:
            import cv2
            img_bgr = cv2.imread(str(p))
            if img_bgr is None:
                return {"success": False, "error": f"Impossible de lire l'image : {p}"}
            alerte.envoyer_photo(img_bgr, legende=message, cle=f"tool_photo_{time.time()}")
            return {"success": True, "message": f"Photo et message envoyés sur Telegram : {p.name}"}
        except Exception as exc:
            return {"success": False, "error": f"Erreur d'envoi Telegram : {exc}"}

    alerte.envoyer_message(message, cle=f"tool_msg_{time.time()}")
    return {"success": True, "message": "Message Telegram envoyé."}


HANDLERS = {
    "notify": lambda p: notify(**p),
    "notify_telegram": lambda p: notify_telegram(**p),
}

