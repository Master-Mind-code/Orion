/**
 * Palette partagée entre le WebGL (three.js) et le SVG du cockpit.
 *
 * Un seul endroit pour les couleurs : sans ça, le halo du réacteur et les
 * traits du châssis dérivent l'un de l'autre et l'ensemble perd sa cohérence.
 * Les valeurs reprennent les tokens Tailwind existants (voir tailwind.config.js).
 */

export const CK = {
  cyan: "#00e5ff",
  cyanDeep: "#0088c4",
  blue: "#1b6dff",
  amber: "#ffab2e",
  gold: "#f5c518",
  crimson: "#ff3b5c",
  green: "#00ffa3",
  steel: "#7fa8c9",
  ink: "#04060d",
  ink2: "#080e1e",
} as const;

/** États d'Orion — même vocabulaire que Sphere.tsx pour rester interchangeable. */
export type CockpitState = "idle" | "listening" | "processing" | "speaking" | "alert";

interface StateSkin {
  /** Teinte dominante du réacteur et des accents actifs. */
  key: string;
  /** Accent secondaire (arcs ambre/cramoisi des vidéos de référence). */
  accent: string;
  /** Vitesse de rotation de base, en tours/seconde. */
  spin: number;
  /** Intensité du bloom : monte quand Orion travaille. */
  glow: number;
  label: string;
}

export const SKIN: Record<CockpitState, StateSkin> = {
  idle:       { key: CK.cyan,    accent: CK.amber,   spin: 0.05, glow: 0.85, label: "STANDBY" },
  listening:  { key: CK.green,   accent: CK.cyan,    spin: 0.14, glow: 1.35, label: "ÉCOUTE" },
  processing: { key: CK.gold,    accent: CK.crimson, spin: 0.28, glow: 1.55, label: "TRAITEMENT" },
  speaking:   { key: CK.cyan,    accent: CK.green,   spin: 0.18, glow: 1.45, label: "PARLE" },
  alert:      { key: CK.crimson, accent: CK.amber,   spin: 0.40, glow: 1.8,  label: "ALERTE" },
};
