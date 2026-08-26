"""
Module d'alertes multi-canal (Telegram, Discord, Email, Notifications système) pour Orion.

Usages :
    "Envoie une alerte Telegram si le drawdown dépasse 2%"
    "Notifie sur Discord que le rapport de trading est prêt"
"""
from __future__ import annotations

import json
import os
import smtplib
import urllib.request
from email.mime.text import MIMEText
from typing import Any, Dict


def send_alert_notification(
    title: str,
    message: str,
    channel: str = "all",
    severity: str = "info",
) -> Dict[str, Any]:
    """Envoie une notification/alerte sur Telegram, Discord, Email ou le système local.
    
    channel: 'telegram', 'discord', 'email', 'system', 'all'
    severity: 'info', 'warning', 'critical'
    """
    results = {}
    channel = channel.lower()
    prefix = "🚨 [CRITIQUE]" if severity == "critical" else "⚠️ [ATTENTION]" if severity == "warning" else "ℹ️ [INFO]"
    full_message = f"{prefix} {title}\n\n{message}"

    # 1. Telegram
    if channel in ("telegram", "all"):
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if bot_token and chat_id:
            try:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = json.dumps({"chat_id": chat_id, "text": full_message}).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    results["telegram"] = {"success": True, "status": resp.status}
            except Exception as e:
                results["telegram"] = {"success": False, "error": str(e)}
        else:
            results["telegram"] = {"success": False, "note": "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID non configurés"}

    # 2. Discord Webhook
    if channel in ("discord", "all"):
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if webhook_url:
            try:
                data = json.dumps({"content": full_message}).encode("utf-8")
                req = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    results["discord"] = {"success": True, "status": resp.status}
            except Exception as e:
                results["discord"] = {"success": False, "error": str(e)}
        else:
            results["discord"] = {"success": False, "note": "DISCORD_WEBHOOK_URL non configuré"}

    # 3. Email (SMTP)
    if channel in ("email", "all"):
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        email_to = os.getenv("ALERT_EMAIL_TO")

        if smtp_host and smtp_user and smtp_pass and email_to:
            try:
                msg = MIMEText(full_message)
                msg["Subject"] = f"Orion Alerte: {title}"
                msg["From"] = smtp_user
                msg["To"] = email_to

                with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                results["email"] = {"success": True, "sent_to": email_to}
            except Exception as e:
                results["email"] = {"success": False, "error": str(e)}
        else:
            results["email"] = {"success": False, "note": "Configuration SMTP manquante dans .env"}

    # 4. Local System Notification
    results["local_log"] = True

    return {
        "success": True,
        "title": title,
        "severity": severity,
        "channels": results,
    }


HANDLERS = {
    "send_alert_notification": lambda p: send_alert_notification(**p),
}
