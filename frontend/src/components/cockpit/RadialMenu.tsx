/**
 * Sélecteur de mode en arc — les menus radiaux des références.
 *
 * Les items sont posés sur un arc de cercle dont le centre est SOUS le
 * conteneur : ils remontent en éventail depuis le bas de l'écran, ce qui laisse
 * le cœur du réacteur dégagé au centre.
 */
import { useId } from "react";
import type { LucideIcon } from "lucide-react";

import { CK } from "@/lib/cockpit-theme";

export interface RadialItem {
  id: string;
  label: string;
  icon: LucideIcon;
  /** Badge court : nombre de positions ouvertes, état d'un service... */
  badge?: string;
}

interface RadialMenuProps {
  items: RadialItem[];
  active: string;
  onSelect: (id: string) => void;
  color?: string;
  accent?: string;
  /** Rayon de l'arc en px. Plus il est grand, plus l'éventail est plat. */
  radius?: number;
  /** Ouverture totale de l'éventail, en degrés. */
  spread?: number;
}

export function RadialMenu({
  items, active, onSelect,
  color = CK.cyan, accent = CK.amber,
  radius = 230, spread = 104,
}: RadialMenuProps) {
  const uid = useId();
  const n = items.length;
  // Un seul item : on le pose droit devant plutôt que de diviser par zéro.
  const step = n > 1 ? spread / (n - 1) : 0;
  const start = -spread / 2;

  // Géométrie de l'éventail. On mesure tout depuis le SOMMET de l'arc (θ=0)
  // plutôt que depuis le centre du cercle, qui tombe hors du conteneur.
  const half = ((spread / 2) * Math.PI) / 180;
  const MARGE = 46;
  const H = MARGE * 2 + radius * (1 - Math.cos(half));
  const W = 2 * radius * Math.sin(half) + 120;
  const cy = MARGE + radius; // centre du cercle, en coordonnées locales

  return (
    <div
      className="pointer-events-none absolute bottom-4 left-1/2 z-30 -translate-x-1/2"
      style={{ width: W, height: H }}
      role="tablist"
      aria-label="Modes d'Orion"
    >
      {/* Arc de guidage qui relie les items */}
      <svg className="absolute inset-0 overflow-visible" width={W} height={H} aria-hidden>
        <defs>
          <linearGradient id={`arc-${uid}`} x1="0" x2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0" />
            <stop offset="50%" stopColor={color} stopOpacity="0.55" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path
          d={arcPath(W / 2, cy, radius, spread + 22)}
          fill="none"
          stroke={`url(#arc-${uid})`}
          strokeWidth="1.5"
        />
      </svg>

      {items.map((item, i) => {
        const deg = start + step * i;
        const rad = (deg * Math.PI) / 180;
        const x = Math.sin(rad) * radius;
        const y = MARGE + radius * (1 - Math.cos(rad));
        const isActive = item.id === active;
        const Icon = item.icon;

        return (
          <button
            key={item.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onSelect(item.id)}
            title={item.label}
            className="pointer-events-auto absolute flex h-16 w-16 -translate-x-1/2 -translate-y-1/2
                       flex-col items-center justify-center rounded-full transition-all duration-200
                       hover:scale-110 focus:outline-none focus-visible:ring-2"
            style={{
              left: `calc(50% + ${x}px)`,
              top: `${y}px`,
              background: isActive
                ? `radial-gradient(circle, ${color}33 0%, transparent 72%)`
                : "rgba(6,14,32,0.55)",
              border: `1px solid ${isActive ? color : "rgba(0,229,255,0.18)"}`,
              boxShadow: isActive ? `0 0 22px ${color}55, inset 0 0 14px ${color}22` : "none",
              color: isActive ? color : "rgba(150,195,225,0.72)",
            }}
          >
            <Icon size={20} strokeWidth={1.6} />
            <span className="font-tech mt-0.5 text-[8px] uppercase tracking-[0.14em]">
              {item.label}
            </span>
            {item.badge && (
              <span
                className="font-tech absolute -right-1 -top-1 rounded-full px-1.5 text-[9px] leading-4"
                style={{ background: accent, color: CK.ink }}
              >
                {item.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/** Arc passant par les items, en coordonnées SVG locales du conteneur. */
function arcPath(cx: number, cy: number, r: number, spreadDeg: number): string {
  const half = (spreadDeg / 2) * (Math.PI / 180);
  const p = (sign: number): [number, number] => [
    cx + Math.sin(sign * half) * r,
    cy - Math.cos(sign * half) * r,
  ];
  const [x1, y1] = p(-1);
  const [x2, y2] = p(1);
  return `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`;
}
