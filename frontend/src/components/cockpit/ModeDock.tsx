/**
 * Barre de modes en bas de scène — boutons circulaires en verre.
 *
 * Remplace le menu radial : la maquette aligne les boutons sur une rangée, le
 * bouton Voix plus gros que les autres. Il porte l'action principale, sa taille
 * le dit avant même qu'on lise l'étiquette.
 */
import type { LucideIcon } from "lucide-react";

export interface ModeItem {
  id: string;
  label: string;
  icon: LucideIcon;
  /** Bouton principal : plus grand, bordure plus marquée. */
  principal?: boolean;
}

export function ModeDock({ items, actif, onSelect }: {
  items: ModeItem[];
  actif: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div
      className="absolute left-1/2 flex -translate-x-1/2 items-end"
      style={{ bottom: "5%", gap: 26 }}
      role="tablist"
      aria-label="Modes d'Orion"
    >
      {items.map((item) => {
        const Icon = item.icon;
        const estActif = item.id === actif;
        const taille = item.principal ? 92 : 82;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={estActif}
            onClick={() => onSelect(item.id)}
            className="relative flex cursor-pointer flex-col items-center justify-center rounded-full
                       transition-all duration-300 hover:brightness-125"
            style={{
              width: taille,
              height: taille,
              gap: 5,
              border: `1px solid rgba(0,229,255,${item.principal || estActif ? 0.5 : 0.28})`,
              background: item.principal
                ? "radial-gradient(circle at 50% 40%, rgba(0,229,255,.18), rgba(4,12,24,.9) 70%)"
                : "radial-gradient(circle at 50% 40%, rgba(0,229,255,.1), rgba(4,10,20,.86) 70%)",
              backdropFilter: "blur(10px)",
              color: estActif ? "#e6faff" : "rgba(180,215,240,.8)",
              boxShadow: estActif || item.principal
                ? "0 0 30px rgba(0,229,255,.22), inset 0 0 22px rgba(0,229,255,.12)"
                : "none",
            }}
          >
            <Icon size={item.principal ? 20 : 19} strokeWidth={1.6} />
            <span className="font-tech"
                  style={{ fontSize: item.principal ? 8.5 : 8, letterSpacing: ".23em" }}>
              {item.label}
            </span>
            {/* Trait sous le bouton : marque le mode courant sans changer sa
                taille, ce qui ferait sauter toute la rangée. */}
            <span
              className="absolute left-1/2 -translate-x-1/2 transition-opacity duration-300"
              style={{
                bottom: -13, width: 26, height: 2,
                background: "#00e5ff", boxShadow: "0 0 10px #00e5ff",
                opacity: estActif ? 1 : 0,
              }}
            />
          </button>
        );
      })}
    </div>
  );
}
