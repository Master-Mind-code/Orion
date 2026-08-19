/**
 * Poste de trading, version cockpit.
 *
 * Widgets vectoriels dans l'esprit des références : grand cadran à dégradé,
 * tuiles sombres à gros chiffres, courbe de P&L, anneaux de confiance.
 *
 * Purement présentationnel : toute la logique (WebSocket, état, commandes)
 * reste dans TradingUI, qui alimente ce composant par ses props. On peut donc
 * refondre l'apparence sans risquer de casser l'exécution.
 */
import { useId } from "react";

import { CK } from "@/lib/cockpit-theme";
import type {
  HistoryTrade, LogEntry, OpenPosition, SignalData, TradingStats,
} from "@/hooks/useTradingState";

const GRAD = { from: "#ff8a3d", mid: "#ff4d8d", to: "#8b5cf6" };

const fmt = (v: number | undefined, digits = 2, suffix = "") =>
  v === undefined || v === null || Number.isNaN(v) ? "—" : v.toFixed(digits) + suffix;

/* ─────────────────────────── Carte de base ─────────────────────────── */

function Card({ title, children, className = "", accent = CK.cyan, right }: {
  title?: string; children?: React.ReactNode; className?: string;
  accent?: string; right?: React.ReactNode;
}) {
  return (
    <div
      className={`relative flex flex-col overflow-hidden rounded-2xl border border-white/[0.06] ${className}`}
      style={{ background: "linear-gradient(158deg, rgba(15,23,42,0.86) 0%, rgba(6,11,24,0.92) 100%)" }}
    >
      {title && (
        <div className="flex shrink-0 items-center justify-between px-4 pt-3">
          <span className="font-tech text-[9px] uppercase tracking-[0.24em]" style={{ color: accent }}>
            {title}
          </span>
          {right}
        </div>
      )}
      <div className="min-h-0 flex-1 p-4 pt-2">{children}</div>
    </div>
  );
}

/* ─────────────────── Grand cadran à dégradé (ouvert en bas) ─────────────── */

export function ArcGauge({ value, max = 100, label, sub, size = 210 }: {
  value: number; max?: number; label: string; sub?: string; size?: number;
}) {
  const uid = useId();
  const r = size / 2 - 16;
  const cx = size / 2;
  const cy = size / 2;
  // Arc ouvert de 260°, comme les cadrans de référence : l'ouverture en bas
  // laisse la place au chiffre et évite l'effet « camembert ».
  const SPAN = 260;
  const start = 90 + (360 - SPAN) / 2;
  const pct = Math.max(0, Math.min(1, (value || 0) / max));

  const pol = (deg: number) => {
    const a = (deg * Math.PI) / 180;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  };
  const arc = (frac: number) => {
    const [x1, y1] = pol(start);
    const [x2, y2] = pol(start + SPAN * frac);
    return `M ${x1} ${y1} A ${r} ${r} 0 ${SPAN * frac > 180 ? 1 : 0} 1 ${x2} ${y2}`;
  };

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="absolute inset-0">
        <defs>
          <linearGradient id={`g-${uid}`} x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor={GRAD.from} />
            <stop offset="55%" stopColor={GRAD.mid} />
            <stop offset="100%" stopColor={GRAD.to} />
          </linearGradient>
        </defs>
        <path d={arc(1)} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="10" strokeLinecap="round" />
        <path
          d={arc(Math.max(pct, 0.001))}
          fill="none" stroke={`url(#g-${uid})`} strokeWidth="10" strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 8px ${GRAD.mid}66)`, transition: "d 400ms" }}
        />
      </svg>
      <div className="relative flex flex-col items-center">
        <span className="font-orbitron text-3xl text-white">{label}</span>
        {sub && (
          <span className="font-tech mt-1 text-[9px] uppercase tracking-[0.2em] text-text-dim">{sub}</span>
        )}
      </div>
    </div>
  );
}

/* ───────────────────────────── Tuile chiffrée ──────────────────────────── */

function Tile({ label, value, tone = "neutral" }: {
  label: string; value: string; tone?: "neutral" | "up" | "down";
}) {
  const color = tone === "up" ? CK.green : tone === "down" ? CK.crimson : "#e8f4ff";
  return (
    <div className="rounded-xl border border-white/[0.05] bg-white/[0.02] px-3 py-2.5">
      <div className="font-orbitron text-lg leading-tight" style={{ color }}>{value}</div>
      <div className="font-tech mt-0.5 text-[8px] uppercase tracking-[0.18em] text-text-dim">{label}</div>
    </div>
  );
}

/* ──────────────────────────── Courbe de P&L ────────────────────────────── */

function Sparkline({ points, height = 96 }: { points: number[]; height?: number }) {
  const uid = useId();
  if (points.length < 2) {
    return (
      <div className="font-tech flex h-24 items-center justify-center text-[9px]
                      uppercase tracking-[0.2em] text-text-dim">
        Pas encore assez de trades
      </div>
    );
  }
  const W = 100, H = height;
  const min = Math.min(...points, 0);
  const max = Math.max(...points, 0);
  const span = max - min || 1;
  const xy = points.map((p, i) => [
    (i / (points.length - 1)) * W,
    H - ((p - min) / span) * (H - 8) - 4,
  ]);
  const line = xy.map(([x, y], i) => `${i ? "L" : "M"} ${x} ${y}`).join(" ");
  const area = `${line} L ${W} ${H} L 0 ${H} Z`;
  const positif = points[points.length - 1] >= 0;
  const teinte = positif ? CK.green : CK.crimson;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="h-24 w-full">
      <defs>
        <linearGradient id={`s-${uid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={teinte} stopOpacity="0.35" />
          <stop offset="100%" stopColor={teinte} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#s-${uid})`} />
      <path d={line} fill="none" stroke={teinte} strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

/* ─────────────────────────── Anneau de confiance ───────────────────────── */

function Donut({ pct, color, size = 74 }: { pct: number; color: string; size?: number }) {
  const r = size / 2 - 6;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="6" />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="6"
        strokeLinecap="round"
        strokeDasharray={`${(c * Math.max(0, Math.min(100, pct))) / 100} ${c}`}
        style={{ filter: `drop-shadow(0 0 6px ${color}88)`, transition: "stroke-dasharray 400ms" }}
      />
    </svg>
  );
}

/* ───────────────────────────────── Deck ────────────────────────────────── */

export function TradingDeck({ stats, positions, signal, history, log, controls }: {
  stats: TradingStats;
  positions: OpenPosition[];
  signal: SignalData;
  history: HistoryTrade[];
  log: LogEntry[];
  controls?: React.ReactNode;
}) {
  // Courbe de P&L cumulé : plus parlant que les profits trade par trade.
  const cumul: number[] = [];
  history.reduce((acc, t) => {
    const v = acc + (t.profit ?? 0);
    cumul.push(v);
    return v;
  }, 0);

  const decision = signal.decision ?? "WAIT";
  const decisionColor =
    decision === "BUY" ? CK.green : decision === "SELL" ? CK.crimson : CK.amber;
  const pnl = stats.net_pnl ?? 0;

  return (
    // auto-rows-min plutôt qu'un gabarit de rangées figé : le contenu occupe
    // quatre rangées, en déclarer trois écrasait les cartes à 47 px de haut.
    <div className="grid h-full auto-rows-min grid-cols-12 gap-3 overflow-y-auto pr-1">
      {/* ── Bandeau de commande ── */}
      {controls && <div className="col-span-12">{controls}</div>}

      {/* ── Cadran principal ── */}
      <Card title="Performance" accent={GRAD.mid} className="col-span-12 lg:col-span-4">
        <div className="flex flex-col items-center">
          <ArcGauge
            value={stats.winrate ?? 0}
            label={stats.winrate === undefined ? "—" : `${Math.round(stats.winrate)}%`}
            sub="Taux de réussite"
          />
          <div className="mt-1 grid w-full grid-cols-2 gap-2">
            <Tile label="Trades" value={stats.total_trades?.toString() ?? "—"} />
            <Tile label="RR moyen" value={fmt(stats.avg_rr)} />
          </div>
        </div>
      </Card>

      {/* ── Courbe + tuiles ── */}
      <Card
        title="P&L cumulé" accent={CK.cyan} className="col-span-12 lg:col-span-8"
        right={
          <span className="font-orbitron text-lg" style={{ color: pnl >= 0 ? CK.green : CK.crimson }}>
            {pnl >= 0 ? "+" : ""}{fmt(pnl)}$
          </span>
        }
      >
        <Sparkline points={cumul} />
        <div className="mt-3 grid grid-cols-4 gap-2">
          <Tile label="Profit total" value={`+${fmt(stats.total_profit)}$`} tone="up" />
          <Tile label="Perte totale" value={`${fmt(stats.total_loss)}$`} tone="down" />
          <Tile label="Meilleur" value={`+${fmt(stats.best_trade)}$`} tone="up" />
          <Tile label="Pire" value={`${fmt(stats.worst_trade)}$`} tone="down" />
        </div>
      </Card>

      {/* ── Positions ── */}
      <Card
        title="Positions ouvertes" accent={CK.cyan} className="col-span-12 lg:col-span-7"
        right={
          <span className="font-tech text-[9px] tracking-[0.14em] text-text-dim">
            {positions.length} · {fmt(positions.reduce((a, p) => a + (p.profit ?? 0), 0))}$
          </span>
        }
      >
        {positions.length === 0 ? (
          <div className="font-tech flex h-24 items-center justify-center text-[9px]
                          uppercase tracking-[0.2em] text-text-dim">
            Aucune position
          </div>
        ) : (
          <div className="space-y-1.5">
            {positions.map((p) => {
              const gain = (p.profit ?? 0) >= 0;
              return (
                <div key={p.ticket}
                     className="flex items-center gap-3 rounded-lg border border-white/[0.05] bg-white/[0.02] px-3 py-2">
                  <span
                    className="font-tech rounded px-1.5 py-0.5 text-[9px] tracking-[0.12em]"
                    style={{
                      background: p.type === "BUY" ? `${CK.green}22` : `${CK.crimson}22`,
                      color: p.type === "BUY" ? CK.green : CK.crimson,
                    }}
                  >
                    {p.type}
                  </span>
                  <span className="font-rajdhani text-xs text-text">{p.volume} lot</span>
                  <span className="font-mono text-[11px] text-text-dim">@{fmt(p.open_price, 3)}</span>
                  <span className="font-orbitron ml-auto text-sm"
                        style={{ color: gain ? CK.green : CK.crimson }}>
                    {gain ? "+" : ""}{fmt(p.profit)}$
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* ── Signal ── */}
      <Card title="Signal IA" accent={decisionColor} className="col-span-12 lg:col-span-5">
        <div className="flex items-center gap-4">
          <div className="relative flex items-center justify-center">
            <Donut pct={signal.confidence ?? 0} color={decisionColor} />
            <span className="font-orbitron absolute text-sm" style={{ color: decisionColor }}>
              {Math.round(signal.confidence ?? 0)}%
            </span>
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-orbitron text-2xl tracking-[0.1em]" style={{ color: decisionColor }}>
              {decision}
            </div>
            <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1">
              {[["Entrée", signal.entry], ["Stop", signal.sl], ["TP1", signal.tp1], ["R/R", signal.rr]]
                .map(([k, v]) => (
                  <div key={k as string} className="flex justify-between gap-2">
                    <span className="font-tech text-[8px] uppercase tracking-[0.16em] text-text-dim">{k}</span>
                    <span className="font-mono text-[11px] text-text">{fmt(v as number, 3)}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
        {(signal.analysis?.reasoning || signal.wait_reason) && (
          <p className="font-rajdhani mt-3 line-clamp-2 text-[11px] leading-snug text-text-dim">
            {signal.analysis?.reasoning || signal.wait_reason}
          </p>
        )}
      </Card>

      {/* ── Journal ── */}
      <Card title="Journal" accent={CK.steel} className="col-span-12">
        <div className="max-h-24 space-y-0.5 overflow-y-auto font-mono text-[10px]">
          {log.slice(0, 8).map((e) => (
            <div key={e.id} className="flex gap-2">
              <span className="text-text-dim/60">{e.time}</span>
              <span
                style={{
                  color: e.level === "error" ? CK.crimson
                    : e.level === "success" ? CK.green
                    : e.level === "warning" ? CK.amber : "rgba(150,195,225,0.8)",
                }}
              >
                {e.msg}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
