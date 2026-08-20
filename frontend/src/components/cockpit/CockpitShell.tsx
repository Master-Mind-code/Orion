/**
 * Coque du cockpit — implémentation de la maquette « Cockpit Orion ».
 *
 * Composition figée sur une scène de 1920×1080 mise à l'échelle (voir Stage) :
 * bandeau, rails latéraux, quatre cadrans de verre aux angles, réacteur au
 * centre, barre de modes en bas.
 *
 * Répartition des techniques, conforme à la maquette :
 *   - réacteur et orbe en canvas 2D (ReactorCanvas) — halo et traînées obtenus
 *     par dégradés et `shadowBlur`, sans contexte WebGL ni bloom ;
 *   - cadrans, texte et graduations en SVG/DOM, pour rester nets au pixel ;
 *   - le contenu d'un mode s'affiche au centre et le réacteur s'efface.
 *
 * La version three.js reste dans ReactorCore.tsx, inutilisée ici : elle donnait
 * du volume mais s'écartait du design.
 */
import type { ReactNode } from "react";
import { Minus, Pin, Square, X } from "lucide-react";

import { SKIN, type CockpitState } from "@/lib/cockpit-theme";
import { agirFenetre, basculerCapsule, estBureau } from "@/lib/desktop";
import { ReactorCanvas } from "./ReactorCanvas";
import { ModeDock, type ModeItem } from "./ModeDock";
import { Stage, StageFond, StageRails } from "./Stage";
import { ChargePanel, MemoirePanel, RadarPanel, SpectrePanel } from "./panels/HudPanels";

interface ShellProps {
  state?: CockpitState;
  audioLevelRef?: React.MutableRefObject<number>;
  items: ModeItem[];
  active: string;
  onSelect: (id: string) => void;
  /** Phrase sous le réacteur, en mode conversation. */
  caption?: string;
  /** Ligne d'état en bas de scène. */
  footer?: string;
  /** Réduit le réacteur quand un deck occupe le centre. */
  coreScale?: number;
  children?: ReactNode;
}

/** Commandes de fenêtre : la coque Electron est sans bordure, il n'y a donc
 *  aucun bouton système. Absentes en navigateur, où elles n'ont pas de sens. */
function WindowControls() {
  if (!estBureau()) return null;
  const btn = "rounded p-1.5 text-text-dim transition hover:bg-white/10 hover:text-text";
  return (
    <div className="flex items-center gap-1"
         style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}>
      <button className={btn} title="Capsule flottante" onClick={() => basculerCapsule()}>
        <Pin size={13} strokeWidth={1.8} />
      </button>
      <button className={btn} title="Réduire" onClick={() => agirFenetre("reduire")}>
        <Minus size={13} strokeWidth={1.8} />
      </button>
      <button className={btn} title="Agrandir" onClick={() => agirFenetre("agrandir")}>
        <Square size={11} strokeWidth={1.8} />
      </button>
      <button className="rounded p-1.5 text-text-dim transition hover:bg-red/80 hover:text-white"
              title="Fermer" onClick={() => agirFenetre("fermer")}>
        <X size={13} strokeWidth={1.8} />
      </button>
    </div>
  );
}

export function CockpitShell({
  state = "idle", audioLevelRef, items, active, onSelect,
  caption, footer = "CTRL+ALT+O · RAPPEL COCKPIT · MCP PRÊT", coreScale = 1, children,
}: ShellProps) {
  const skin = SKIN[state];
  const modeVoix = active === "voice";

  return (
    <Stage>
      <StageFond />

      {/* ── Bandeau ── */}
      <div className="pointer-events-none absolute left-0 right-0 flex items-center justify-between"
           style={{ top: 34, padding: "0 52px" }}>
        <div className="pointer-events-auto flex items-center" style={{ gap: 14 }}>
          <span style={{
            width: 9, height: 9, borderRadius: "50%", background: skin.key,
            boxShadow: `0 0 12px ${skin.key}`, animation: "ck-pulse 2.6s ease-in-out infinite",
          }} />
          <span className="font-orbitron"
                style={{ fontSize: 19, letterSpacing: ".44em", color: "#d8f4ff",
                         textShadow: "0 0 18px rgba(0,229,255,.55)" }}>
            ORION
          </span>
          <span className="font-tech"
                style={{ fontSize: 10, letterSpacing: ".3em", color: "rgba(120,170,210,.5)" }}>
            {skin.label}
          </span>
        </div>
        <div className="pointer-events-auto flex items-center" style={{ gap: 38 }}>
          {[["MODE", active.toUpperCase(), skin.key],
            ["ÉTAT", skin.label, skin.accent]].map(([libelle, valeur, couleur]) => (
            <div key={libelle} className="flex flex-col items-end" style={{ gap: 3 }}>
              <span className="font-tech"
                    style={{ fontSize: 9, letterSpacing: ".24em", color: "rgba(120,170,210,.45)" }}>
                {libelle}
              </span>
              <span className="font-orbitron"
                    style={{ fontSize: 13, letterSpacing: ".14em", color: couleur }}>
                {valeur}
              </span>
            </div>
          ))}
          <WindowControls />
        </div>
      </div>

      {/* Zone de glissement de la fenêtre sans bordure (ignorée en navigateur). */}
      {estBureau() && (
        <div className="absolute left-0 top-0" style={{ right: 420, height: 78,
             WebkitAppRegion: "drag" } as React.CSSProperties} />
      )}

      <StageRails />

      {/* ── Réacteur ── */}
      <div
        className="pointer-events-none absolute"
        style={{
          left: "50%", top: "44%", width: 660, height: 660,
          transform: `translate(-50%,-50%) scale(${coreScale})`,
          opacity: coreScale < 0.6 ? 0.35 : 1,
          transition: "transform .9s cubic-bezier(.4,0,.2,1), opacity .9s ease",
        }}
      >
        <ReactorCanvas state={state} audioLevelRef={audioLevelRef}
                       className="h-full w-full" />
      </div>

      {/* ── Cadrans ── */}
      <RadarPanel state={state} style={{ left: "2.4%", top: "6.2%", width: "25.5%", height: "35%" }} />
      <ChargePanel state={state} style={{ right: "2.4%", top: "8.5%", width: "25.5%", height: "31%" }} />
      <MemoirePanel state={state} style={{ left: "2.4%", top: "48.5%", width: "25.5%", height: "31%" }} />
      <SpectrePanel state={state} levelRef={audioLevelRef}
                    meta={state === "listening" ? "ENTRÉE MICRO"
                          : state === "speaking" ? "SORTIE TTS" : "VEILLE"}
                    style={{ right: "2.4%", top: "48.5%", width: "25.5%", height: "28%" }} />

      {/* ── Phrase de conversation ── */}
      {modeVoix && (caption ?? skin.caption) && (
        <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 text-center"
             style={{ top: "68.5%" }}>
          <div className="font-space"
               style={{ fontSize: 19, fontWeight: 300, letterSpacing: ".1em",
                        color: "#cfeeff", textShadow: "0 0 22px rgba(0,229,255,.5)" }}>
            {caption ?? skin.caption}
          </div>
        </div>
      )}

      {/* ── Contenu du mode : au centre, entre les cadrans ── */}
      {children && (
        <main className="pointer-events-none absolute"
              style={{ left: "30.5%", right: "30.5%", top: "7%", bottom: "17%" }}>
          {children}
        </main>
      )}

      {/* Orbe de veille — présent dans la maquette, en retrait du dock. */}
      <div className="pointer-events-none absolute"
           style={{ right: "14%", bottom: "6.5%", width: 108, height: 108 }}>
        <ReactorCanvas state={state} live={false} className="h-full w-full" />
      </div>

      <ModeDock items={items} actif={active} onSelect={onSelect} />

      <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 font-mono"
           style={{ bottom: "2.2%", fontSize: 9, letterSpacing: ".22em",
                    color: "rgba(120,170,210,.4)" }}>
        {footer}
      </div>
    </Stage>
  );
}
