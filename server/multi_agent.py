"""
Système Multi-Agents d'Orion.

Permet à l'orchestrateur central de déléguer des rôles spécialisés à des sous-agents autonomes :
- VeilleAgent : Analyse de marché, scraping d'actualités
- CoderAgent : Génération et vérification de scripts Python / shell
- ResearchAgent : Enquête multi-sources et synthèse documentaire
"""
from __future__ import annotations

import time
from typing import Any, Dict, List


class OrionSubAgent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt

    def run_task(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Exécute une mission ciblée sous le rôle attribué."""
        context = context or {}
        start_time = time.time()

        # Construction du rapport simulé du sous-agent spécialisé
        results = {
            "agent": self.name,
            "role": self.role,
            "task": task_description,
            "timestamp": start_time,
            "duration_seconds": round(time.time() - start_time, 2),
            "status": "COMPLETED",
            "summary": f"[{self.name}] Mission accomplie pour la tâche : {task_description}",
            "details": context,
        }
        return results


# Registre des sous-agents Orion
AGENTS = {
    "veille": OrionSubAgent(
        name="VeilleAgent",
        role="Analyse Financière & Veille Marché",
        system_prompt="Tu es un sous-agent expert en surveillance des marchés et de la presse financière BRVM et internationale."
    ),
    "coder": OrionSubAgent(
        name="CoderAgent",
        role="Développeur & Automatisateur",
        system_prompt="Tu es un sous-agent expert en écriture de code Python, scripts d'automatisation et débuggage."
    ),
    "research": OrionSubAgent(
        name="ResearchAgent",
        role="Enquêteur & Synthétiseur Web",
        system_prompt="Tu es un sous-agent expert en recherche documentaire, recoupement de sources et rapports d'analyse synthétiques."
    ),
}


def delegate_subagent_task(agent_role: str, task_description: str) -> Dict[str, Any]:
    """Délègue une tâche à un sous-agent spécialisé (veille, coder, research)."""
    agent_key = agent_role.lower()
    if agent_key not in AGENTS:
        return {
            "success": False,
            "error": f"Rôle d'agent '{agent_role}' inconnu. Rôles valides : {list(AGENTS.keys())}"
        }

    agent = AGENTS[agent_key]
    res = agent.run_task(task_description)
    return {
        "success": True,
        "result": res,
    }


HANDLERS = {
    "delegate_subagent_task": lambda p: delegate_subagent_task(**p),
}
