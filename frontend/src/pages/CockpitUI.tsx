/**
 * Vue cockpit — coque 3D commune, avec ses cinq modes.
 *
 * Pour l'instant chaque mode affiche son panneau ; le branchement sur les vues
 * existantes (OrionUI, VoiceUI, TradingUI) se fera mode par mode.
 */
import { useRef, useState } from "react";
import { Activity, Bot, LineChart, Mic, MonitorCog } from "lucide-react";

import { CockpitShell } from "@/components/cockpit/CockpitShell";
import type { RadialItem } from "@/components/cockpit/RadialMenu";
import { CK, SKIN, type CockpitState } from "@/lib/cockpit-theme";

const MODES: RadialItem[] = [
  { id: "chat",    label: "Chat",    icon: Bot },
  { id: "voice",   label: "Voix",    icon: Mic },
  { id: "trading", label: "Trading", icon: LineChart },
  { id: "desktop", label: "Bureau",  icon: MonitorCog },
  { id: "system",  label: "Système", icon: Activity },
];

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
        className="relative h-full backdrop-blur-panel"
        style={{
          background: "linear-gradient(160deg, rgba(8,18,38,0.78) 0%, rgba(4,8,18,0.62) 100%)",
          border: `1px solid ${accent}26`,
          // Coins coupés : c'est ce biseau qui donne l'allure "panneau blindé".
          clipPath:
            "polygon(0 14px, 14px 0, calc(100% - 14px) 0, 100% 14px, 100% calc(100% - 14px), calc(100% - 14px) 100%, 14px 100%, 0 calc(100% - 14px))",
        }}
      >
        <div
          className="absolute left-0 top-0 h-[2px] w-16"
          style={{ background: accent, opacity: 0.8 }}
        />
        {title && (
          <div
            className="font-tech border-b px-4 py-2 text-[10px] uppercase tracking-[0.24em]"
            style={{ borderColor: `${accent}1f`, color: accent }}
          >
            {title}
          </div>
        )}
        <div className="p-4">{children}</div>
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
  const [mode, setMode] = useState("chat");
  const [state, setState] = useState<CockpitState>("idle");
  const audioLevelRef = useRef(0);
  const skin = SKIN[state];

  return (
    <CockpitShell
      state={state}
      audioLevelRef={audioLevelRef}
      items={MODES}
      active={mode}
      onSelect={setMode}
      coreScale={mode === "chat" ? 1 : 0.82}
      meta={
        <div className="flex gap-6">
          <Readout label="Mode" value={mode.toUpperCase()} accent={skin.key} />
          <Readout label="Provider" value="ANTHROPIC" accent={skin.accent} />
        </div>
      }
    >
      {/* Sélecteur d'état, provisoire : sert à valider le rendu de chaque skin. */}
      <div className="pointer-events-auto absolute top-20 flex gap-2"
        style={{ left: "var(--ck-inset)" }}>
        {(Object.keys(SKIN) as CockpitState[]).map((s) => (
          <button
            key={s}
            onClick={() => setState(s)}
            className="font-tech rounded px-3 py-1 text-[9px] uppercase tracking-[0.18em] transition"
            style={{
              border: `1px solid ${s === state ? SKIN[s].key : "rgba(0,229,255,0.16)"}`,
              color: s === state ? SKIN[s].key : "rgba(150,195,225,0.6)",
              background: s === state ? `${SKIN[s].key}14` : "transparent",
            }}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Panneaux collés aux bords : le réacteur reste entièrement visible. */}
      <GlassPanel
        title="Flux" accent={skin.key}
        className="pointer-events-auto absolute bottom-[188px] w-[min(16rem,24vw)]"
        style={{ left: "var(--ck-inset)" }}
      >
        <div className="space-y-2.5">
          {[["Bureau", 82], ["MetaTrader 5", 64], ["TradingView", 48], ["Voix", 30]].map(
            ([n, pct]) => (
              <div key={n as string} className="flex items-center justify-between gap-3">
                <span className="font-rajdhani whitespace-nowrap text-xs text-text">{n}</span>
                <span className="h-1 w-24 rounded bg-white/5">
                  <span
                    className="block h-full rounded"
                    style={{ width: `${pct}%`, background: skin.key, boxShadow: `0 0 8px ${skin.key}` }}
                  />
                </span>
              </div>
            ),
          )}
        </div>
      </GlassPanel>

      <GlassPanel
        title="Marché" accent={skin.accent}
        className="pointer-events-auto absolute bottom-[188px] w-[min(16rem,24vw)]"
        style={{ right: "var(--ck-inset)" }}
      >
        <div className="space-y-2.5">
          {[["XAUUSDc", "4335.34"], ["EURUSDc", "1.0842"], ["Positions", "0"]].map(([k, v]) => (
            <div key={k} className="flex items-center justify-between">
              <span className="font-rajdhani text-xs text-text-dim">{k}</span>
              <span className="font-orbitron text-xs" style={{ color: skin.accent }}>{v}</span>
            </div>
          ))}
        </div>
      </GlassPanel>
    </CockpitShell>
  );
}
