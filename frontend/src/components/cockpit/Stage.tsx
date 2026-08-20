/**
 * Scène à dimensions fixes, mise à l'échelle pour tenir dans la fenêtre.
 *
 * Reprise de la maquette : tout est positionné en pourcentages d'un cadre de
 * 1920×1080, puis le cadre entier est réduit par un `scale`. Un HUD dense se
 * disloque dès qu'on le laisse se recomposer librement — cadrans qui débordent,
 * étiquettes qui se chevauchent. En figeant les proportions, la composition est
 * identique sur un portable et sur un écran large ; seule la taille change.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";

export const STAGE_W = 1920;
export const STAGE_H = 1080;

export function Stage({ children }: { children: ReactNode }) {
  const hote = useRef<HTMLDivElement>(null);
  const [echelle, setEchelle] = useState(1);

  useEffect(() => {
    const el = hote.current;
    if (!el) return;
    const recalculer = () => {
      const { width, height } = el.getBoundingClientRect();
      if (!width || !height) return;
      // `min` et non `max` : on veut la scène entière visible, quitte à laisser
      // des marges, plutôt qu'un débordement qui coupe les cadrans du bord.
      setEchelle(Math.min(width / STAGE_W, height / STAGE_H));
    };
    recalculer();
    const ro = new ResizeObserver(recalculer);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div
      ref={hote}
      className="fixed inset-0 flex items-center justify-center overflow-hidden"
      style={{ background: "#04060d" }}
    >
      <div
        className="relative flex-none overflow-hidden font-space text-text"
        style={{
          width: STAGE_W,
          height: STAGE_H,
          transform: `scale(${echelle})`,
          transformOrigin: "center center",
          background:
            "radial-gradient(ellipse 70% 60% at 50% 46%, #072033 0%, #04101c 45%, #04060d 100%)",
        }}
      >
        {children}
      </div>
    </div>
  );
}

/** Fond : grille qui dérive lentement + vignettage qui concentre le regard. */
export function StageFond() {
  return (
    <>
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,229,255,.028) 1px, transparent 1px)," +
            "linear-gradient(90deg, rgba(0,229,255,.028) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          animation: "ck-drift 14s linear infinite",
        }}
      />
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 38%, rgba(2,4,10,.92) 100%)",
        }}
      />
      <div
        className="pointer-events-none absolute"
        style={{
          inset: 14,
          border: "1px solid rgba(0,229,255,.13)",
          clipPath:
            "polygon(0 26px, 26px 0, calc(100% - 26px) 0, 100% 26px, 100% calc(100% - 26px), calc(100% - 26px) 100%, 26px 100%, 0 calc(100% - 26px))",
        }}
      />
    </>
  );
}

/** Rails de graduations latéraux, avec leurs repères rouges. */
export function StageRails() {
  const ticks = Array.from({ length: 14 });
  const rail = (cote: "left" | "right") => (
    <div
      className="pointer-events-none absolute flex flex-col justify-between"
      style={{ [cote]: 26, top: "16%", bottom: "16%",
               alignItems: cote === "right" ? "flex-end" : "flex-start" }}
    >
      {ticks.map((_, i) => (
        <span key={i} style={{ width: 14, height: 2, background: "rgba(0,229,255,.34)" }} />
      ))}
    </div>
  );
  const repere = (cote: "left" | "right", top: string) => (
    <div
      className="pointer-events-none absolute"
      style={{ [cote]: 26, top, width: 14, height: 2,
               background: "#ff3b5c", boxShadow: "0 0 8px rgba(255,59,92,.8)" }}
    />
  );
  return (
    <>
      {rail("left")}
      {rail("right")}
      {repere("left", "34%")}
      {repere("left", "38%")}
      {repere("right", "29%")}
      {repere("right", "33%")}
    </>
  );
}

const BISEAU =
  "polygon(0 22px, 22px 0, calc(100% - 22px) 0, 100% 22px, 100% calc(100% - 22px), calc(100% - 22px) 100%, 22px 100%, 0 calc(100% - 22px))";

/**
 * Panneau de verre biseauté.
 *
 * La bordure est un dégradé : un `border` uni ne peut pas suivre un `clip-path`
 * en gardant une épaisseur constante. On empile donc deux couches — l'extérieure
 * porte le dégradé, l'intérieure le verre, décalée d'un pixel.
 */
export function GlassCard({
  titre, meta, accentGradient, children, style, className = "",
}: {
  titre: string;
  meta?: ReactNode;
  accentGradient?: string;
  children: ReactNode;
  style?: React.CSSProperties;
  className?: string;
}) {
  return (
    <div
      className={`absolute ${className}`}
      style={{
        padding: 1,
        background: accentGradient
          ?? "linear-gradient(150deg, rgba(0,229,255,.28), rgba(0,229,255,.05) 55%, rgba(0,229,255,.16))",
        clipPath: BISEAU,
        ...style,
      }}
    >
      <div
        className="flex h-full w-full flex-col"
        style={{
          background: "linear-gradient(158deg, rgba(8,26,48,.9), rgba(4,10,22,.78))",
          backdropFilter: "blur(14px)",
          clipPath: BISEAU,
        }}
      >
        <div
          className="flex shrink-0 items-center justify-between"
          style={{ padding: "14px 22px 10px 30px", borderBottom: "1px solid rgba(0,229,255,.12)" }}
        >
          <span className="font-tech" style={{ fontSize: 10, letterSpacing: ".26em", color: "#00e5ff" }}>
            {titre}
          </span>
          {meta && (
            <span className="font-mono" style={{ fontSize: 9, letterSpacing: ".14em", color: "rgba(120,170,210,.55)" }}>
              {meta}
            </span>
          )}
        </div>
        <div className="min-h-0 flex-1">{children}</div>
      </div>
    </div>
  );
}
