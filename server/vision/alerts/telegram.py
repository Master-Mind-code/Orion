# -*- coding: utf-8 -*-
"""Module d'alerte Telegram réutilisable.

Envoie un message et/ou une capture d'écran sur Telegram quand une condition
se produit (somnolence, intrus, comptage...).

Caractéristiques :
    - envoi non bloquant (dans un thread) : n'interrompt pas la vidéo ;
    - anti-spam par « clé » d'alerte (cooldown configurable) ;
    - configuration via variables d'environnement ou fichier config.json.

Configuration (2 étapes) :
    1. Crée un bot avec @BotFather sur Telegram -> il te donne un TOKEN.
    2. Écris un message à ton bot, puis récupère ton CHAT_ID :
           python main.py chat-id
       (ou : python -m vision.alerts.telegram)

Renseigne token et chat_id dans config.json (voir config.example.json) ou dans
les variables d'environnement TELEGRAM_TOKEN / TELEGRAM_CHAT_ID.
"""

import os
import json
import time
import threading

import requests

from server.vision.paths import CONFIG_PATH


def charger_config():
    """Renvoie (token, chat_id) depuis les variables d'env ou config.json."""
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if (not token or not chat_id) and CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            token = token or cfg.get("telegram_token")
            chat_id = chat_id or cfg.get("telegram_chat_id")
        except (json.JSONDecodeError, OSError):
            pass
    return token, chat_id


class AlerteTelegram:
    """Envoie des alertes Telegram (message ou photo), en respectant un cooldown
    par clé pour éviter le spam."""

    def __init__(self, cooldown=30):
        self.token, self.chat_id = charger_config()
        self.cooldown = cooldown
        self._dernier = {}
        self.actif = bool(self.token and self.chat_id)
        if not self.actif:
            print("[TELEGRAM] Non configuré (token/chat_id manquants) — "
                  "alertes Telegram désactivées.", flush=True)

    # -- API publique ------------------------------------------------------- #
    def envoyer_message(self, texte, cle="message"):
        if self._pret(cle):
            threading.Thread(target=self._post_message, args=(texte,),
                             daemon=True).start()

    def envoyer_photo(self, image_bgr, legende="", cle="photo"):
        if self._pret(cle):
            threading.Thread(target=self._post_photo, args=(image_bgr, legende),
                             daemon=True).start()

    # -- Interne ------------------------------------------------------------ #
    def _pret(self, cle):
        """Vrai si l'alerte est active et hors période de cooldown pour `cle`."""
        if not self.actif:
            return False
        maintenant = time.time()
        if maintenant - self._dernier.get(cle, 0) < self.cooldown:
            return False
        self._dernier[cle] = maintenant
        return True

    def _url(self, methode):
        return f"https://api.telegram.org/bot{self.token}/{methode}"

    def _post_message(self, texte):
        try:
            requests.post(self._url("sendMessage"),
                          data={"chat_id": self.chat_id, "text": texte}, timeout=10)
        except requests.RequestException as e:
            print(f"[TELEGRAM] Échec envoi message : {e}", flush=True)

    def _post_photo(self, image_bgr, legende):
        try:
            import cv2
            ok, buffer = cv2.imencode(".jpg", image_bgr)
            if not ok:
                return
            requests.post(
                self._url("sendPhoto"),
                data={"chat_id": self.chat_id, "caption": legende},
                files={"photo": ("alerte.jpg", buffer.tobytes(), "image/jpeg")},
                timeout=15)
        except requests.RequestException as e:
            print(f"[TELEGRAM] Échec envoi photo : {e}", flush=True)


def outil_chat_id():
    """Affiche les chat_id disponibles (à lancer après avoir écrit à son bot)."""
    token, _ = charger_config()
    if not token:
        token = input("Token du bot (BotFather) : ").strip()
    try:
        rep = requests.get(f"https://api.telegram.org/bot{token}/getUpdates",
                           timeout=10).json()
    except requests.RequestException as e:
        print("Erreur réseau :", e)
        return
    if not rep.get("ok"):
        print("Token invalide ou erreur :", rep)
        return
    resultats = rep.get("result", [])
    if not resultats:
        print("Aucun message reçu. Écris d'abord un message à ton bot dans "
              "Telegram, puis relance cet outil.")
        return
    vus = set()
    print("\nchat_id trouvés :")
    for maj in resultats:
        chat = (maj.get("message") or maj.get("edited_message") or {}).get("chat", {})
        cid = chat.get("id")
        if cid and cid not in vus:
            vus.add(cid)
            nom = chat.get("first_name") or chat.get("title") or ""
            print(f"  - {cid}  ({nom})")
    print("\nCopie ton chat_id dans config.json.")


if __name__ == "__main__":
    outil_chat_id()
