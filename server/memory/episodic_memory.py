# -*- coding: utf-8 -*-
"""Module de mémoire épisodique pour Orion.

Permet de répondre aux questions temporelles rétrospectives ("qu'est-ce qu'on a fait la semaine dernière sur Orion ?").
Combine les journaux de bord, les entrées d'audit et les souvenirs RAG sur une plage de jours donnée.
"""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def get_obsidian_vault_path() -> Path:
    """Retourne le chemin du coffre Obsidian depuis l'env ou fallback dans data/obsidian_journal."""
    env_path = os.getenv("ORION_OBSIDIAN_VAULT_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    vault = ROOT_DIR / "data" / "obsidian_journal"
    vault.mkdir(parents=True, exist_ok=True)
    return vault


def episodic_query(query: str | None = None, days_back: int = 7) -> dict:
    """Interroge la mémoire épisodique d'Orion sur les N derniers jours."""
    days_back = max(1, min(365, int(days_back)))
    now = datetime.now()
    since_dt = now - timedelta(days=days_back)
    since_ts = since_dt.timestamp()
    since_str = since_dt.strftime("%Y-%m-%d")
    now_str = now.strftime("%Y-%m-%d")

    if not query:
        query = f"Qu'a-t-on accompli et quelles opérations ont été réalisées ces {days_back} derniers jours ?"

    # 1. Audit logs
    audit_events = []
    audit_stats = {}
    try:
        from server import audit
        audit_events = audit.get_recent(limit=500, since_ts=since_ts)
        audit_stats = audit.get_stats(since_ts=since_ts)
    except Exception as exc:
        print(f"[EPISODIC] Audit load error : {exc}")

    # 2. Daily journals de la période
    vault = get_obsidian_vault_path()
    journal_dir = vault / "Journal"
    journal_texts = []
    if journal_dir.exists():
        for p in journal_dir.glob("*.md"):
            try:
                # extrait la date du fichier YYYY-MM-DD_Journal.md
                file_date_str = p.stem.split("_")[0]
                file_dt = datetime.strptime(file_date_str, "%Y-%m-%d")
                if file_dt >= since_dt - timedelta(days=1):
                    journal_texts.append(f"--- Journal {file_date_str} ---\n" + p.read_text(encoding="utf-8")[:1500])
            except Exception:
                pass

    # 3. Rappels RAG sémantiques
    rag_recalls = []
    try:
        from server.memory.rag_tools import memory_recall
        rec_obs = memory_recall(query, top_k=5, namespace="obsidian")
        rec_def = memory_recall(query, top_k=5, namespace="default")
        rag_recalls = rec_obs.get("results", []) + rec_def.get("results", [])
    except Exception:
        pass

    # 4. Synthèse par LLM
    context_str = f"Période analysée : du {since_str} au {now_str} ({days_back} jours)\n"
    context_str += f"Statistiques audit : {audit_stats.get('total', len(audit_events))} opérations au total.\n\n"

    if journal_texts:
        context_str += "=== JOURNAUX DE BORD DE LA PÉRIODE ===\n" + "\n\n".join(journal_texts[:5]) + "\n\n"

    if audit_events:
        context_str += "=== EXTRAIT LOGS AUDIT ===\n"
        for ev in audit_events[:25]:
            ts_str = datetime.fromtimestamp(ev["ts"]).strftime("%Y-%m-%d %H:%M")
            context_str += f"- [{ts_str}] {ev.get('tool_name')}: {ev.get('input_preview')}\n"
        context_str += "\n"

    if rag_recalls:
        context_str += "=== SOUVENIRS RAG PERTINENTS ===\n"
        for r in rag_recalls[:5]:
            context_str += f"- {r.get('text')}\n"

    answer = _synthesize_episodic_response(query, context_str, days_back)

    return {
        "success": True,
        "query": query,
        "days_back": days_back,
        "period": f"{since_str} à {now_str}",
        "events_count": len(audit_events),
        "journals_found": len(journal_texts),
        "answer": answer,
    }


def _synthesize_episodic_response(query: str, context: str, days_back: int) -> str:
    """Génère la réponse de mémoire épisodique structurée par LLM."""
    try:
        from server.orchestrator import _get_provider
        provider = _get_provider()
        prompt = (
            f"Tu es Orion, l'assistant IA exécutif. L'utilisateur pose la question suivante sur la mémoire de travail "
            f"des {days_back} derniers jours :\n"
            f"Question: \"{query}\"\n\n"
            f"Voici les données d'archive, de journaux de bord et d'audit de la période :\n"
            f"{context[:15000]}\n\n"
            f"Rédige une réponse synthétique, claire et chronologique résumant ce qui a été fait, "
            f"les projets abordés, les trades/alertes et les accomplissements majeurs."
        )
        res = provider.call(
            system="Tu es Orion, l'assistant IA exécutif.",
            tools=[],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
        )
        if isinstance(res.content, list):
            texts = [item.get("text", "") for item in res.content if item.get("type") == "text"]
            return "\n".join(texts).strip()
        return str(res.content).strip()
    except Exception as exc:
        return f"Aperçu épisodique sur {days_back} jours : Données agrégées avec succès ({context[:300]}...)"
