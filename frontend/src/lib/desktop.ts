/**
 * Accès aux capacités natives exposées par la coque Electron.
 *
 * Tout est optionnel : l'interface doit rester utilisable dans un navigateur
 * ordinaire, où `window.orionDesktop` n'existe pas. Les appels renvoient alors
 * une valeur vide plutôt que de lever, et le mode Bureau affiche un message
 * expliquant qu'il faut la coque de bureau.
 */

export interface EcranCapture {
  id: string;
  nom: string;
  apercu: string;
  taille: { largeur: number; hauteur: number } | null;
}

export interface FenetreOuverte {
  id: string;
  titre: string;
  apercu: string | null;
}

export type ActionFenetre = "reduire" | "agrandir" | "fermer" | "epingler";

interface PontDesktop {
  disponible: true;
  captureEcran: (opts?: { maxWidth?: number }) => Promise<EcranCapture[]>;
  listerFenetres: (opts?: { vignette?: number }) => Promise<FenetreOuverte[]>;
  pressePapier: {
    lire: () => Promise<string>;
    ecrire: (texte: string) => Promise<boolean>;
  };
  fenetre: (action: ActionFenetre) => Promise<boolean>;
  capsule: (action?: "montrer" | "cacher" | "basculer") => Promise<boolean>;
  cockpit: (action?: "montrer" | "cacher" | "basculer") => Promise<boolean>;
  notifier?: (opts: { title?: string; body?: string; icon?: string }) => Promise<boolean>;
  autostart?: { set: (enabled: boolean) => Promise<boolean>; get: () => Promise<boolean> };
  capsuleState?: (state: string) => Promise<boolean>;
  onCapsuleUpdate?: (callback: (state: any) => void) => void;
  modeOverlay?: (opts: { enabled?: boolean; clickThrough?: boolean }) => Promise<boolean>;
  infos: () => Promise<{ plateforme: string; versionElectron: string; dev: boolean }>;
  /** Token et URL lus dans le .env local par la coque. */
  identifiants?: () => Promise<{ token: string; serverUrl: string }>;
}

declare global {
  interface Window {
    orionDesktop?: PontDesktop;
  }
}

export const pont = (): PontDesktop | undefined =>
  typeof window === "undefined" ? undefined : window.orionDesktop;

export const estBureau = (): boolean => Boolean(pont());

export async function captureEcran(maxWidth = 1600): Promise<EcranCapture[]> {
  return (await pont()?.captureEcran({ maxWidth })) ?? [];
}

export async function listerFenetres(vignette = 320): Promise<FenetreOuverte[]> {
  return (await pont()?.listerFenetres({ vignette })) ?? [];
}

export async function lirePressePapier(): Promise<string> {
  return (await pont()?.pressePapier.lire()) ?? "";
}

export async function ecrirePressePapier(texte: string): Promise<boolean> {
  return (await pont()?.pressePapier.ecrire(texte)) ?? false;
}

export const agirFenetre = (a: ActionFenetre) => pont()?.fenetre(a);
export const basculerCapsule = () => pont()?.capsule("basculer");
