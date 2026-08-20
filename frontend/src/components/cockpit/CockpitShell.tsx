/**
 * Coque commune à tous les modes d'Orion.
 *
 * Empilement, du fond vers l'avant :
 *   z-0   fond (grille + lueur)
 *   z-10  réacteur WebGL (seule couche avec du bloom)
 *   z-20  châssis SVG
 *   z-30  menu radial + barres d'état
 *   z-40  contenu du mode (children)
 *
 * Le contenu passe au-dessus du réacteur, qui reste visible en arrière-plan :
 * c'est ce qui donne la sensation de profondeur des références.
 */
import type { ReactNode } from "react";
import { Minus, Pin, Square, X } from "lucide-react";

import { CK, SKIN, type CockpitState } from "@/lib/cockpit-theme";
import { agirFenetre, basculerCapsule, estBureau } from "@/lib/desktop";
import { CockpitFrame } from "./CockpitFrame";
import { VideoCore } from "./VideoCore";
import { RadialMenu, type RadialItem } from "./RadialMenu";

interface ShellProps {
  state?: CockpitState;
  audioLevelRef?: React.MutableRefObject<number>;
  items: RadialItem[];
  active: string;
  onSelect: (id: string) => void;
  /** Ligne d'état à gauche du bandeau supérieur. */
  status?: ReactNode;
  /** Ligne d'état à droite (latence, device, provider...). */
  meta?: ReactNode;
  /** Réduit le réacteur pour laisser la place à un contenu dense. */
  coreScale?: number;
  children?: ReactNode;
}

/** Commandes de fenêtre : la coque Electron est sans bordure, il n'y a donc
 *  aucun bouton système. Absentes dans un navigateur, où elles n'ont pas de sens. */
function WindowControls() {
  if (!estBureau()) return null;
  const btn = "rounded p-1.5 text-text-dim transition hover:bg-white/10 hover:text-text";
  return (
    <div className="flex items-center gap-1" style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}>
      <button className={btn} title="Capsule flottante" onClick={() => basculerCapsule()}>
        <Pin size={13} strokeWidth={1.8} />
      </button>
      <button className={btn} title="Réduire" onClick={() => agirFenetre("reduire")}>
        <Minus size={13} strokeWidth={1.8} />
      </button>
      <button className={btn} title="Agrandir" onClick={() => agirFenetre("agrandir")}>
        <Square size={11} strokeWidth={1.8} />
      </button>
      <button
        className="rounded p-1.5 text-text-dim transition hover:bg-red/80 hover:text-white"
        title="Fermer" onClick={() => agirFenetre("fermer")}
      >
        <X size={13} strokeWidth={1.8} />
      </button>
    </div>
  );
}

export function CockpitShell({
  state = "idle", audioLevelRef, items, active, onSelect,
  status, meta, coreScale = 1, children,
}: ShellProps) {
  const skin = SKIN[state];

  return (
    <div
      className="relative h-screen w-screen overflow-hidden bg-bg text-text"
      // Marge latérale unique, partagée par le bandeau et les panneaux des
      // modes : figée en px, le cockpit se disloquait sous 1100px de large.
      style={{ ["--ck-inset" as string]: "clamp(14px, 6vw, 132px)" }}
    >
      {/* ── Fond ── */}
      <div className="absolute inset-0 z-0">
        <div
          className="absolute inset-0 opacity-[0.16]"
          style={{
            backgroundImage:
              `linear-gradient(${CK.cyan}18 1px, transparent 1px),
               linear-gradient(90deg, ${CK.cyan}18 1px, transparent 1px)`,
            backgroundSize: "58px 58px",
            maskImage: "radial-gradient(ellipse at center, #000 20%, transparent 78%)",
          }}
        />
        <div
          className="absolute inset-0 transition-colors duration-700"
          style={{
            background: `radial-gradient(ellipse 70% 55% at 50% 48%, ${skin.key}14 0%, transparent 70%)`,
          }}
        />
      </div>

      {/* ── Réacteur ──
          Centré dans la zone HAUTE, pas dans la fenêtre entière : le bas est
          réservé à l'éventail de modes, qui sinon se superpose aux anneaux. */}
      <div
        className="absolute inset-x-0 top-0 z-10 transition-transform duration-500"
        style={{ bottom: 168, transform: `scale(${coreScale})` }}
      >
        <VideoCore state={state} audioLevelRef={audioLevelRef} className="h-full w-full" />
      </div>

      {/* ── Châssis ── */}
      <CockpitFrame color={skin.key} accent={skin.accent} />

      {/* ── Bandeau supérieur ── */}
      <header
        className="pointer-events-none absolute inset-x-0 top-0 z-30 flex items-start justify-between py-6"
        style={{ paddingLeft: "var(--ck-inset)", paddingRight: "var(--ck-inset)" }}
      >
        <div className="pointer-events-auto flex items-center gap-3">
          <span
            className="inline-block h-2 w-2 rounded-full animate-pulse-dot"
            style={{ background: skin.key, boxShadow: `0 0 10px ${skin.key}` }}
          />
          <span className="font-orbitron text-lg tracking-[0.34em]" style={{ color: skin.key }}>
            ORION
          </span>
          <span className="font-tech text-[10px] uppercase tracking-[0.2em] text-text-dim">
            {skin.label}
          </span>
        </div>
        <div className="pointer-events-auto flex items-center gap-4 text-right">
          {status}
          {meta}
          <WindowControls />
        </div>
      </header>

      {/* Zone de glissement de la fenêtre sans bordure. Purement Electron :
          dans un navigateur, -webkit-app-region est ignoré. Elle s'arrête avant
          les boutons, sinon ils deviennent inertes. */}
      {estBureau() && (
        <div
          className="absolute left-0 right-64 top-0 z-20 h-14"
          style={{ WebkitAppRegion: "drag" } as React.CSSProperties}
        />
      )}

      {/* ── Contenu du mode ── */}
      {/* Le contenu se place lui-même : le cœur doit rester dégagé, ce qu'un
          centrage automatique empêcherait. pointer-events-none sur le conteneur,
          réactivé par chaque panneau, pour ne pas bloquer le menu en dessous. */}
      {children && (
        <main className="pointer-events-none absolute inset-0 z-40">{children}</main>
      )}

      {/* ── Sélecteur de mode ── */}
      <RadialMenu
        items={items}
        active={active}
        onSelect={onSelect}
        color={skin.key}
        accent={skin.accent}
      />
    </div>
  );
}
