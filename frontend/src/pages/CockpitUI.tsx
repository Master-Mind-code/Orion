/**
 * Vue cockpit — coque 3D commune, avec ses modes.
 *
 * Voix et Trading montent les vues existantes en mode `embedded` : elles
 * abandonnent leur chrome, que la coque fournit, et remontent leur état pour
 * piloter le réacteur.
 *
 * Pas de mode Chat : la conversation se fait à la voix, sans panneau. Un
 * panneau de discussion recouvrait le cockpit et vidait de son sens la coque 3D.
 * La vue texte reste accessible sur sa route dédiée `/`.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, LineChart, Mic, MonitorCog } from "lucide-react";

import { CockpitShell } from "@/components/cockpit/CockpitShell";
import type { ModeItem } from "@/components/cockpit/ModeDock";
import { CK, SKIN, type CockpitState } from "@/lib/cockpit-theme";
import { VoiceUI } from "./VoiceUI";
import { TradingUI } from "./TradingUI";
import { BureauDeck } from "@/components/cockpit/BureauDeck";
import { SystemeDeck } from "@/components/cockpit/SystemeDeck";

const MODES: ModeItem[] = [
  { id: "voice",   label: "Voix",    icon: Mic, principal: true },
  { id: "trading", label: "Trading", icon: LineChart },
  { id: "desktop", label: "Bureau",  icon: MonitorCog },
  { id: "system",  label: "Système", icon: Activity },
];

/** Place du réacteur selon la densité du mode : plus le contenu est dense,
 *  plus le cœur s'efface pour ne pas gêner la lecture. */
const CORE_SCALE: Record<string, number> = {
  voice: 1, trading: 0.42, desktop: 0.45, system: 0.45,
};

/** Panneau de verre biseauté — la brique de base des vidéos de référence. */
export function GlassPanel({
  title, children, className = "", accent = CK.cyan, style,
}: {
  title?: string; children?: React.ReactNode; className?: string;
  accent?: string; style?: React.CSSProperties;
}) {
  // Le positionnement vient du className de l'appelant ; l'intérieur porte son
  // propre `relative`. Mettre `relative` sur l'enveloppe le ferait gagner contre
  // un `absolute` passé en prop : Tailwind émet .relative APRÈS .absolute, donc
  // l'ordre dans l'attribut class ne décide de rien.
  return (
    <div className={className} style={style}>
      <div
        className="relative flex h-full flex-col overflow-hidden backdrop-blur-panel"
        style={{
          background: "linear-gradient(160deg, rgba(8,18,38,0.82) 0%, rgba(4,8,18,0.7) 100%)",
          border: `1px solid ${accent}26`,
          // Coins coupés : c'est ce biseau qui donne l'allure "panneau blindé".
          clipPath:
            "polygon(0 14px, 14px 0, calc(100% - 14px) 0, 100% 14px, 100% calc(100% - 14px), calc(100% - 14px) 100%, 14px 100%, 0 calc(100% - 14px))",
        }}
      >
        <div className="absolute left-0 top-0 h-[2px] w-16" style={{ background: accent, opacity: 0.8 }} />
        {title && (
          <div
            className="font-tech shrink-0 border-b px-4 py-2 text-[10px] uppercase tracking-[0.24em]"
            style={{ borderColor: `${accent}1f`, color: accent }}
          >
            {title}
          </div>
        )}
        <div className="min-h-0 flex-1">{children}</div>
      </div>
    </div>
  );
}

function Readout({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="flex flex-col items-end">
      <span className="font-tech text-[9px] uppercase tracking-[0.2em] text-text-dim">{label}</span>
      <span className="font-orbitron text-sm" style={{ color: accent }}>{value}</span>
    </div>
  );
}

export function CockpitUI() {
  const [mode, setMode] = useState("voice");
  const [state, setState] = useState<CockpitState>("idle");
  const audioLevelRef = useRef(0);
  const skin = SKIN[state];

  // Identité stable : passée en dépendance du useEffect de remontée d'état côté
  // vues, une fonction recréée à chaque rendu y déclencherait une boucle.
  const handleState = useCallback((s: CockpitState) => setState(s), []);

  // Enchaînement d'états repris de la maquette. Les minuteries sont gardées en
  // ref pour être annulées : sans ça, deux clics rapprochés laissent la
  // première séquence remettre l'état à idle en plein milieu de la seconde.
  const chaine = useRef<number[]>([]);
  const couperChaine = () => {
    chaine.current.forEach(window.clearTimeout);
    chaine.current = [];
  };
  useEffect(() => couperChaine, []);

  /** Clic sur Voix : écoute → traitement → parole → repos. */
  const basculerVoix = useCallback(() => {
    couperChaine();
    const suivant: CockpitState =
      mode !== "voice" ? "listening" : state === "listening" ? "processing" : "listening";
    setMode("voice");
    setState(suivant);
    if (suivant === "processing") {
      chaine.current.push(
        window.setTimeout(() => setState("speaking"), 1500),
        window.setTimeout(() => setState("idle"), 4600),
      );
    }
  }, [mode, state]);

  /** Changement de mode : Orion réfléchit, répond, puis retombe au repos. */
  const choisirMode = useCallback((id: string) => {
    if (id === "voice") return basculerVoix();
    couperChaine();
    setMode(id);
    setState("processing");
    chaine.current.push(
      window.setTimeout(() => setState("speaking"), 1400),
      window.setTimeout(() => setState("idle"), 4200),
    );
  }, [basculerVoix]);

  return (
    <CockpitShell
      state={state}
      audioLevelRef={audioLevelRef}
      items={MODES}
      active={mode}
      onSelect={choisirMode}
      coreScale={CORE_SCALE[mode] ?? 0.9}
    >
      {/* ── Voix : sous le réacteur, hors de la colonne centrale réservée
             aux decks. Pas de -translate-x-1/2 : un ancêtre transformé devient
             le bloc conteneur des enfants `fixed` (toasts, modal). ── */}
      {mode === "voice" && (
        <div className="pointer-events-auto absolute inset-x-0 mx-auto text-center"
             style={{ top: "58%", width: "50%", maxWidth: "680px" }}>
          <VoiceUI embedded onStateChange={handleState} onModeChange={setMode}
                   audioLevelRef={audioLevelRef} />
        </div>
      )}


      {/* ── Trading : pleine surface, les cartes du deck portent deja leur
             propre chrome ; un panneau de verre par-dessus ferait doublon. ── */}
      {mode === "trading" && (
        <div className="pointer-events-auto h-full"><TradingUI embedded /></div>
      )}

      {/* ── Bureau : poste de contrôle natif ── */}
      {mode === "desktop" && (
        <div className="pointer-events-auto h-full"><BureauDeck /></div>
      )}

      {/* ── Système : santé, pont MCP, audit, coupe-circuit ── */}
      {mode === "system" && (
        <div className="pointer-events-auto h-full"><SystemeDeck /></div>
      )}

    </CockpitShell>
  );
}
