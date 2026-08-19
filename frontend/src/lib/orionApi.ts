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
