/**
 * Source unique des identifiants de connexion au serveur Orion.
 *
 * Chaque vue avait ses propres clés de stockage — `orionToken` pour le chat,
 * `orionVoiceToken` pour la voix, `orion_trading_token` pour le trading. Il
 * fallait donc saisir le même token une fois par mode. Tout passe désormais par
 * les clés ci-dessous, et les anciennes sont récupérées automatiquement.
 *
 * Ordre de résolution, du plus fort au plus faible :
 *   1. ce que l'utilisateur a saisi (localStorage)
 *   2. le .env local, transmis par la coque Electron
 *   3. VITE_ORION_TOKEN, pour un déploiement web maîtrisé
 *   4. les anciennes clés, migrées une fois
 */
import { pont } from "./desktop";
import { storage } from "./utils";

const CLE_URL = "orion.serverUrl";
const CLE_TOKEN = "orion.token";
const CLE_DEVICE = "orion.deviceId";

// Anciennes clés, par ordre de préférence, pour la reprise en douceur.
const LEGACY_URL = ["orionServerUrl", "orionVoiceServerUrl"];
const LEGACY_TOKEN = ["orionToken", "orionVoiceToken", "orion_trading_token"];

function premierNonVide(cles: string[]): string {
  for (const c of cles) {
    const v = storage.get(c);
    if (v) return v;
  }
  return "";
}

function urlParDefaut(): string {
  if (typeof window === "undefined") return "ws://localhost:8765";
  const { protocol, host } = window.location;
  // Servie par FastAPI : le serveur est à la même adresse que la page.
  if (protocol === "http:" || protocol === "https:") {
    return `${protocol === "https:" ? "wss:" : "ws:"}//${host}`;
  }
  return "ws://localhost:8765";
}

export function lireToken(): string {
  return storage.get(CLE_TOKEN) || premierNonVide(LEGACY_TOKEN)
    || (import.meta.env.VITE_ORION_TOKEN ?? "");
}

export function lireServerUrl(): string {
  return storage.get(CLE_URL) || premierNonVide(LEGACY_URL) || urlParDefaut();
}

export function lireDeviceId(defaut = "cockpit"): string {
  return storage.get(CLE_DEVICE) || defaut;
}

export function ecrireToken(v: string) { storage.set(CLE_TOKEN, v); }
export function ecrireServerUrl(v: string) { storage.set(CLE_URL, v); }
export function ecrireDeviceId(v: string) { storage.set(CLE_DEVICE, v); }

/**
 * Complète les identifiants manquants depuis la coque de bureau.
 *
 * Asynchrone parce que le pont Electron l'est. Ne remplace jamais une valeur
 * déjà saisie : l'utilisateur garde la main s'il pointe vers un autre serveur.
 * Renvoie true si quelque chose a été rempli, pour que l'appelant se reconnecte.
 */
export async function completerDepuisBureau(): Promise<boolean> {
  const p = pont();
  if (!p?.identifiants) return false;
  try {
    const { token, serverUrl } = await p.identifiants();
    let change = false;
    if (token && !lireToken()) { ecrireToken(token); change = true; }
    if (serverUrl && !storage.get(CLE_URL)) { ecrireServerUrl(serverUrl); change = true; }
    return change;
  } catch {
    return false;
  }
}

/** Le serveur est-il joignable sans saisie supplémentaire ? */
export function pretAConnecter(): boolean {
  return Boolean(lireToken());
}
