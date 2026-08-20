/**
 * Les quatre cadrans latéraux du cockpit, repris de la maquette.
 *
 * En SVG et non en WebGL, délibérément : ces cadrans portent du texte fin et des
 * graduations d'un pixel. Rendus dans la scène 3D, ils passeraient sous le bloom
 * et deviendraient illisibles. Le canvas ne garde que le réacteur.
 */
import { useEffect, useRef, useState } from "react";

import { SKIN, type CockpitState } from "@/lib/cockpit-theme";
import { GlassCard } from "../Stage";
import { GlobeMemoire, SpectreCanvas } from "./HudCanvas";

/** Teintes de l'etat courant : tout le cockpit change de couleur ensemble. */
const teintes = (state: CockpitState) => ({
  cle: SKIN[state].key,
  accent: SKIN[state].accent,
});
const VERT = "#00ffa3";

/* ────────────────────────────── Radar ─────────────────────────────────── */

export function RadarPanel({ state = "idle", style }: {
  state?: CockpitState; style?: React.CSSProperties;
}) {
  const { cle: CYAN, accent: OR } = teintes(state);
  const [azimut, setAzimut] = useState(42);
  useEffect(() => {
    const id = window.setInterval(() => setAzimut((a) => (a + 7) % 360), 1200);
    return () => window.clearInterval(id);
  }, []);

  return (
    <GlassCard titre="RADAR — CIBLES" meta={`SCAN ${azimut}°`} style={style}>
      <div style={{ flex: 1, minHeight: 0, padding: "8px 14px 14px" }}>
        <svg viewBox="0 0 260 230" style={{ width: "100%", height: "100%", overflow: "visible" }}>
          {/* Les ellipses croisées suggèrent une demi-sphère vue en plongée :
              c'est ce qui donne la profondeur, un simple jeu de cercles reste plat. */}
          <g fill="none" stroke={`${CYAN}33`} strokeWidth="1">
            <circle cx="130" cy="112" r="96" />
            <circle cx="130" cy="112" r="72" />
            <circle cx="130" cy="112" r="48" />
            <circle cx="130" cy="112" r="24" />
            <ellipse cx="130" cy="112" rx="96" ry="34" />
            <ellipse cx="130" cy="112" rx="96" ry="66" />
            <ellipse cx="130" cy="112" rx="34" ry="96" />
            <ellipse cx="130" cy="112" rx="66" ry="96" />
            <line x1="34" y1="112" x2="226" y2="112" />
            <line x1="130" y1="16" x2="130" y2="208" />
          </g>
          <g style={{ transformOrigin: "130px 112px", animation: "ck-spin 7s linear infinite" }}>
            <path d="M130 112 L226 112 A96 96 0 0 0 198 44 Z" fill={`${CYAN}29`} />
            <line x1="130" y1="112" x2="226" y2="112" stroke={CYAN} strokeWidth="1.4" opacity=".85" />
          </g>
          <g fill="none" stroke={OR} strokeWidth="1.2">
            <circle cx="96" cy="76" r="5" />
            <circle cx="168" cy="132" r="5" />
          </g>
          <circle cx="96" cy="76" r="9" fill="none" stroke={OR} strokeWidth="1"
                  style={{ animation: "ck-blip 2.8s ease-out infinite", transformOrigin: "96px 76px" }} />
          <circle cx="168" cy="132" r="9" fill="none" stroke={OR} strokeWidth="1"
                  style={{ animation: "ck-blip 2.8s ease-out .9s infinite", transformOrigin: "168px 132px" }} />
          <circle cx="150" cy="60" r="2.4" fill={CYAN} />
          <circle cx="82" cy="150" r="2.4" fill={CYAN} />
          <g fontFamily="Share Tech Mono, monospace" fontSize="7.5"
             fill="rgba(140,190,225,.6)" letterSpacing="1">
            <text x="104" y="66">CIBLE 01</text>
            <text x="176" y="128">CIBLE 02</text>
            <text x="112" y="8">ÉLÉVATION</text>
            <text x="6" y="70">300</text>
            <text x="6" y="114">250</text>
            <text x="10" y="158">240</text>
            <text x="234" y="80">360</text>
            <text x="234" y="118">330</text>
            <text x="232" y="156">260</text>
            <text x="112" y="226">AZIMUT {String(azimut).padStart(3, "0")}</text>
          </g>
        </svg>
      </div>
    </GlassCard>
  );
}

/* ──────────────────────────── Charge système ──────────────────────────── */

function Jauge({ valeur, rayon, epaisseur, couleur, taille }: {
  valeur: number; rayon: number; epaisseur: number; couleur: string; taille: number;
}) {
  const c = 2 * Math.PI * rayon;
  const centre = taille / 2;
  return (
    <svg viewBox={`0 0 ${taille} ${taille}`} style={{ width: "100%", height: "100%" }}>
      <circle cx={centre} cy={centre} r={rayon} fill="none"
              stroke={`${couleur}22`} strokeWidth={epaisseur} />
      <circle
        cx={centre} cy={centre} r={rayon} fill="none" stroke={couleur}
        strokeWidth={epaisseur} strokeLinecap="round"
        strokeDasharray={`${(c * valeur) / 100} ${c}`}
        transform={`rotate(-90 ${centre} ${centre})`}
        style={{
          transition: "stroke-dasharray .9s cubic-bezier(.4,0,.2,1)",
          filter: `drop-shadow(0 0 6px ${couleur}b0)`,
        }}
      />
    </svg>
  );
}

export function ChargePanel({ state = "idle", style }: {
  state?: CockpitState; style?: React.CSSProperties;
}) {
  const { cle: CYAN, accent: OR } = teintes(state);
  const [cpu, setCpu] = useState(38);
  const [ram, setRam] = useState(61);
  const [gpu, setGpu] = useState(24);
  useEffect(() => {
    const id = window.setInterval(() => {
      const bruit = (v: number, a: number, b: number) =>
        Math.max(a, Math.min(b, v + (Math.random() - 0.5) * 12));
      setCpu((v) => Math.round(bruit(v, 12, 92)));
      setRam((v) => Math.round(bruit(v, 40, 85)));
      setGpu((v) => Math.round(bruit(v, 8, 70)));
    }, 2200);
    return () => window.clearInterval(id);
  }, []);

  const petite = (v: number, couleur: string, libelle: string, detail: string) => (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{ position: "relative", width: 62, height: 62, flexShrink: 0 }}>
        <Jauge valeur={v} rayon={32} epaisseur={6} couleur={couleur} taille={80} />
        <div className="font-orbitron absolute inset-0 flex items-center justify-center"
             style={{ fontSize: 13, color: couleur }}>{v}</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <span className="font-tech" style={{ fontSize: 9, letterSpacing: ".2em", color: "rgba(120,170,210,.6)" }}>
          {libelle}
        </span>
        <span className="font-mono" style={{ fontSize: 10, color: "#b8d8f0" }}>{detail}</span>
      </div>
    </div>
  );

  return (
    <GlassCard
      titre="CHARGE SYSTÈME" meta="LOCAL · WORKER" style={style}
      accentGradient="linear-gradient(210deg, rgba(0,229,255,.28), rgba(0,229,255,.05) 55%, rgba(255,171,46,.18))"
    >
      <div style={{ flex: 1, minHeight: 0, display: "flex", alignItems: "center",
                    gap: 18, padding: "10px 26px 16px" }}>
        <div style={{ position: "relative", width: "44%", aspectRatio: "1", flexShrink: 0 }}>
          <Jauge valeur={cpu} rayon={50} epaisseur={8} couleur={CYAN} taille={120} />
          <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ gap: 2 }}>
            <span className="font-orbitron" style={{ fontSize: 22, color: "#e6faff" }}>{cpu}</span>
            <span className="font-tech" style={{ fontSize: 9, letterSpacing: ".2em", color: "rgba(120,170,210,.6)" }}>
              CPU %
            </span>
          </div>
        </div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 14 }}>
          {petite(ram, OR, "RAM", `${(ram * 0.32).toFixed(1)} / 32 Go`)}
          {petite(gpu, VERT, "GPU", `${44 + Math.round(gpu * 0.35)} °C`)}
        </div>
      </div>
    </GlassCard>
  );
}

/* ─────────────────────────── Mémoire — RAG ────────────────────────────── */

export function MemoirePanel({ state = "idle", vecteurs = "12 843", rappel = 94, style }: {
  state?: CockpitState; vecteurs?: string; rappel?: number;
  style?: React.CSSProperties;
}) {
  const { cle: CYAN, accent: OR } = teintes(state);
  const carte = (couleur: string, titre: string, valeur: string) => (
    <div style={{
      padding: "8px 12px",
      background: `${couleur}12`,
      border: `1px solid ${couleur}50`,
      clipPath: "polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)",
    }}>
      <div className="font-tech" style={{ fontSize: 8.5, letterSpacing: ".16em", color: couleur }}>{titre}</div>
      <div className="font-mono" style={{ fontSize: 10, color: "#d5ecff", marginTop: 3 }}>{valeur}</div>
    </div>
  );
  return (
    <GlassCard titre="MÉMOIRE — RAG" meta={`${vecteurs} vecteurs`} style={style}>
      <div style={{ flex: 1, minHeight: 0, display: "flex", gap: 10, padding: "12px 20px 16px" }}>
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "center",
                      gap: 10, width: "44%" }}>
          {carte(OR, "JOURNAL DU JOUR", "18 entrées")}
          {carte(CYAN, "ÉPISODIQUE", `rappel ${rappel} %`)}
          {carte(CYAN, "INDEXATION", "en veille")}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}><GlobeMemoire state={state} /></div>
      </div>
    </GlassCard>
  );
}

/* ─────────────────────────── Spectre voix ─────────────────────────────── */

export function SpectrePanel({ state = "idle", levelRef, meta = "VEILLE", style }: {
  state?: CockpitState; levelRef?: React.MutableRefObject<number>;
  meta?: string; style?: React.CSSProperties;
}) {
  const { cle: CYAN, accent: OR } = teintes(state);
  return (
    <GlassCard
      titre="SPECTRE VOIX" meta={meta} style={style}
      accentGradient="linear-gradient(210deg, rgba(0,229,255,.26), rgba(255,171,46,.14) 60%, rgba(0,229,255,.16))"
    >
      <div style={{ flex: 1, minHeight: 0, padding: "10px 18px 14px" }}>
        <SpectreCanvas state={state} levelRef={levelRef} />
      </div>
    </GlassCard>
  );
}
