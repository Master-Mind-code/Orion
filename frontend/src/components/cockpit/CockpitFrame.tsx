/**
 * Châssis du cockpit — tout le chrome vectoriel qui encadre le réacteur.
 *
 * En SVG et non en WebGL, délibérément : ces traits doivent rester d'une
 * netteté parfaite à toute résolution. Le bloom du réacteur passe DESSOUS.
 *
 * Chaque pièce est positionnée en absolu plutôt que dans un seul SVG plein
 * écran : un viewBox unique obligerait à `preserveAspectRatio="none"`, qui
 * écrase les angles des équerres dès que la fenêtre n'est pas au bon ratio.
 */
import { CK } from "@/lib/cockpit-theme";

interface FrameProps {
  color?: string;
  accent?: string;
  /** Coupe les décors non essentiels — utile sur petit écran. */
  compact?: boolean;
}

/** Équerre d'angle biseautée, façon panneau blindé. */
function Corner({ flipX, flipY, color }: { flipX?: boolean; flipY?: boolean; color: string }) {
  return (
    <svg
      width="132" height="132" viewBox="0 0 132 132" fill="none"
      className="pointer-events-none absolute"
      style={{
        transform: `scale(${flipX ? -1 : 1}, ${flipY ? -1 : 1})`,
        transformOrigin: "center",
        [flipX ? "right" : "left"]: 0,
        [flipY ? "bottom" : "top"]: 0,
      } as React.CSSProperties}
    >
      <path d="M2 44 L2 18 L18 2 L44 2" stroke={color} strokeWidth="2" opacity="0.95" />
      <path d="M10 52 L10 24 L24 10 L52 10" stroke={color} strokeWidth="1" opacity="0.4" />
      <path d="M2 60 L2 96" stroke={color} strokeWidth="3" opacity="0.75" />
      <path d="M60 2 L96 2" stroke={color} strokeWidth="3" opacity="0.75" />
      <circle cx="22" cy="22" r="2.5" fill={color} opacity="0.9" />
      {[0, 1, 2, 3].map((i) => (
        <rect key={i} x={64 + i * 9} y="8" width="5" height="2" fill={color} opacity={0.5 - i * 0.1} />
      ))}
    </svg>
  );
}

/** Rail de graduations vertical — les échelles latérales des références. */
function TickRail({ side, color, accent }: { side: "left" | "right"; color: string; accent: string }) {
  const ticks = Array.from({ length: 34 });
  return (
    <div
      className="pointer-events-none absolute top-1/2 -translate-y-1/2 flex flex-col justify-between"
      style={{ [side]: 18, height: "56%" } as React.CSSProperties}
    >
      {ticks.map((_, i) => {
        const major = i % 6 === 0;
        return (
          <span
            key={i}
            style={{
              width: major ? 16 : 7,
              height: major ? 2 : 1,
              background: major ? accent : color,
              opacity: major ? 0.85 : 0.3,
              alignSelf: side === "left" ? "flex-start" : "flex-end",
            }}
          />
        );
      })}
    </div>
  );
}

/** Bande de danger diagonale — l'accent rouge des références. */
function HazardBar({ side }: { side: "left" | "right" }) {
  return (
    <div
      className="pointer-events-none absolute top-[22%] h-[16%] w-[6px] overflow-hidden opacity-70"
      style={{ [side]: 34 } as React.CSSProperties}
    >
      <div
        className="h-full w-full"
        style={{
          background: `repeating-linear-gradient(135deg, ${CK.crimson} 0 5px, transparent 5px 11px)`,
        }}
      />
    </div>
  );
}

export function CockpitFrame({ color = CK.cyan, accent = CK.amber, compact = false }: FrameProps) {
  return (
    <div className="pointer-events-none absolute inset-0 z-20 overflow-hidden">
      <Corner color={color} />
      <Corner color={color} flipX />
      <Corner color={color} flipY />
      <Corner color={color} flipX flipY />

      {/* Liseré intérieur : referme le cadre entre les équerres */}
      <div
        className="absolute inset-3 rounded-[10px]"
        style={{ border: `1px solid ${color}`, opacity: 0.12 }}
      />

      {!compact && (
        <>
          <TickRail side="left" color={color} accent={accent} />
          <TickRail side="right" color={color} accent={accent} />
          <HazardBar side="left" />
          <HazardBar side="right" />
        </>
      )}

      {/* Vignettage : concentre le regard sur le cœur */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 45%, rgba(2,4,10,0.55) 100%)",
        }}
      />
    </div>
  );
}
