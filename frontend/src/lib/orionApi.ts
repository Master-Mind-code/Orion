/**
 * Appel direct d'un tool Orion, sans passer par le LLM.
 *
 * Sert au panneau de contrôle : cliquer « réduire » sur une fenêtre ne doit pas
 * coûter un aller-retour de raisonnement. Le serveur applique la même chaîne de
 * sécurité que l'orchestrateur (liste blanche, panic, rate limit, mot de passe
 * pour les tools sensibles, audit).
 */
import { storage, wsToHttp } from "./utils";

export interface ReponseTool {
  success?: boolean;
  error?: string;
  [k: string]: unknown;
}

function baseHttp(): string {
  const url = storage.get("orionServerUrl") || "ws://localhost:8765";
  return wsToHttp(url).replace(/\/$/, "");
}

export async function appelerTool(
  tool: string,
  args: Record<string, unknown> = {},
  options: { password?: string; deviceId?: string } = {},
): Promise<ReponseTool> {
  const token = storage.get("orionToken");
  if (!token) {
    return { success: false, error: "Aucun token serveur. Renseigne-le dans les paramètres." };
  }
  try {
    const r = await fetch(`${baseHttp()}/api/tool?token=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool,
        args,
        device_id: options.deviceId ?? "cockpit",
        password: options.password,
      }),
    });
    if (!r.ok) {
      // Le detail FastAPI porte le motif exact (403 liste blanche, 423 panic,
      // 429 rate limit, 401 mot de passe) : le remonter tel quel évite un
      // message générique inutilisable.
      let detail = `HTTP ${r.status}`;
      try {
        const j = await r.json();
        if (j?.detail) detail = String(j.detail);
      } catch { /* corps non JSON : on garde le code */ }
      return { success: false, error: detail };
    }
    return (await r.json()) as ReponseTool;
  } catch (exc) {
    return {
      success: false,
      error: exc instanceof Error ? exc.message : "Serveur Orion injoignable.",
    };
  }
}

/** Le serveur répond-il ? Utilisé par la capsule pour son témoin d'état. */
export async function serveurEnLigne(): Promise<boolean> {
  try {
    const r = await fetch(`${baseHttp()}/status`, { cache: "no-store" });
    return r.ok;
  } catch {
    return false;
  }
}

export interface StatutServeur {
  status?: string;
  controllers?: string[];
  workers?: { id: string; [k: string]: unknown }[];
  voice?: Record<string, unknown>;
  panic?: { active?: boolean; reason?: string; by_device?: string };
  rate_limit?: Record<string, unknown>;
  confirm?: { enabled?: boolean };
  audit_db_kb?: number;
}

/** `/status` est public : pas de token, et il répond même si le reste est verrouillé. */
export async function lireStatut(): Promise<StatutServeur | null> {
  try {
    const r = await fetch(`${baseHttp()}/status`, { cache: "no-store" });
    return r.ok ? ((await r.json()) as StatutServeur) : null;
  } catch {
    return null;
  }
}

export interface LigneAudit {
  id: number;
  ts: number;
  device_id: string;
  tool_name: string;
  input_preview: string;
  success: number;
  error: string | null;
  duration_ms: number;
  sensitive: number;
}

export interface StatsAudit {
  enabled?: boolean;
  total?: number;
  success?: number;
  failed?: number;
  sensitive?: number;
  top_tools?: { tool: string; count: number }[];
}

export async function lireAudit(heures = 24, limite = 40): Promise<
  { stats: StatsAudit; items: LigneAudit[] } | { erreur: string }
> {
  const token = storage.get("orionToken");
  if (!token) return { erreur: "Token serveur requis pour lire l'audit." };
  try {
    const r = await fetch(
      `${baseHttp()}/api/audit?token=${encodeURIComponent(token)}&hours=${heures}&limit=${limite}`,
      { cache: "no-store" },
    );
    if (!r.ok) return { erreur: r.status === 401 ? "Token refusé." : `HTTP ${r.status}` };
    return await r.json();
  } catch (exc) {
    return { erreur: exc instanceof Error ? exc.message : "Serveur injoignable." };
  }
}

/** Coupe-circuit global. Réversible via relacherPanic(). */
export async function declencherPanic(raison: string): Promise<boolean> {
  const token = storage.get("orionToken");
  if (!token) return false;
  const q = new URLSearchParams({ token, reason: raison, by: "cockpit" });
  try {
    const r = await fetch(`${baseHttp()}/api/panic?${q}`, { method: "POST" });
    return r.ok;
  } catch {
    return false;
  }
}

export async function relacherPanic(): Promise<boolean> {
  const token = storage.get("orionToken");
  if (!token) return false;
  try {
    const r = await fetch(
      `${baseHttp()}/api/panic/release?token=${encodeURIComponent(token)}`,
      { method: "POST" },
    );
    return r.ok;
  } catch {
    return false;
  }
}
