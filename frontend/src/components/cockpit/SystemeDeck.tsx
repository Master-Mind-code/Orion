/**
 * Poste système — santé des services, pont MCP, journal d'audit, coupe-circuit.
 *
 * Tout est en lecture, sauf le mode panic. Ce panneau existe pour répondre à
 * une seule question quand quelque chose cloche : qu'est-ce qui ne répond pas ?
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity, AlertTriangle, Database, Plug, RefreshCw, ShieldAlert, ShieldCheck,
} from "lucide-react";

import { CK } from "@/lib/cockpit-theme";
import {
  appelerTool, declencherPanic, lireAudit, lireStatut, relacherPanic,
  type LigneAudit, type StatsAudit, type StatutServeur,
} from "@/lib/orionApi";

function Carte({ title, children, className = "", accent = CK.cyan, right }: {
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

/** Pastille d'état : vert si le service répond, rouge sinon, ambre si dégradé. */
function Voyant({ etat, label, detail }: {
  etat: "ok" | "ko" | "tiede"; label: string; detail?: string;
}) {
  const couleur = etat === "ok" ? CK.green : etat === "ko" ? CK.crimson : CK.amber;
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-white/[0.05] bg-white/[0.02] px-3 py-2">
      <span
        className="h-2 w-2 shrink-0 rounded-full"
        style={{ background: couleur, boxShadow: `0 0 8px ${couleur}` }}
      />
      <span className="font-rajdhani min-w-0 flex-1 truncate text-xs text-text">{label}</span>
      {detail && (
        <span className="font-mono shrink-0 text-[10px]" style={{ color: couleur }}>{detail}</span>
      )}
    </div>
  );
}

function Tuile({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-xl border border-white/[0.05] bg-white/[0.02] px-3 py-2.5">
      <div className="font-orbitron text-lg leading-tight" style={{ color: tone ?? "#e8f4ff" }}>
        {value}
      </div>
      <div className="font-tech mt-0.5 text-[8px] uppercase tracking-[0.18em] text-text-dim">{label}</div>
    </div>
  );
}

interface EtatMcp {
  bridge_enabled?: boolean;
  execution_enabled?: boolean;
  tool_count?: number;
  servers?: { alias: string; alive: boolean; tools: string[] }[];
  errors?: Record<string, string>;
}

export function SystemeDeck() {
  const [statut, setStatut] = useState<StatutServeur | null>(null);
  const [mcp, setMcp] = useState<EtatMcp | null>(null);
  const [stats, setStats] = useState<StatsAudit>({});
  const [lignes, setLignes] = useState<LigneAudit[]>([]);
  const [erreurAudit, setErreurAudit] = useState<string | null>(null);
  const [armePanic, setArmePanic] = useState(false);
  const minuteur = useRef<number | null>(null);

  const rafraichir = useCallback(async () => {
    const s = await lireStatut();
    setStatut(s);

    // Le pont MCP passe par /api/tool : c'est le seul chemin qui expose
    // mcp_status, et il applique déjà la liste blanche et l'audit.
    const r = await appelerTool("mcp_status");
    setMcp(r.success === false ? null : (r as EtatMcp));

    const a = await lireAudit(24, 40);
    if ("erreur" in a) {
      setErreurAudit(a.erreur);
    } else {
      setErreurAudit(null);
      setStats(a.stats ?? {});
      setLignes(a.items ?? []);
    }
  }, []);

  useEffect(() => {
    rafraichir();
    minuteur.current = window.setInterval(rafraichir, 10000);
    return () => { if (minuteur.current) window.clearInterval(minuteur.current); };
  }, [rafraichir]);

  const enLigne = Boolean(statut);
  const panicActif = Boolean(statut?.panic?.active);

  return (
    <div className="grid h-full auto-rows-min grid-cols-12 gap-3 overflow-y-auto pr-1">
      {/* ── Bandeau ── */}
      <div className="col-span-12 flex flex-wrap items-center gap-2">
        <button
          onClick={rafraichir}
          className="font-tech flex items-center gap-1.5 rounded-lg border border-white/[0.08]
                     bg-white/[0.02] px-2.5 py-1.5 text-[9px] uppercase tracking-[0.16em]
                     text-text-dim transition hover:brightness-125"
        >
          <RefreshCw size={12} strokeWidth={1.8} /> Rafraîchir
        </button>
        <span className="font-tech ml-auto text-[9px] uppercase tracking-[0.16em] text-text-dim">
          sondage auto 10 s
        </span>
      </div>

      {/* ── Santé ── */}
      <Carte title="Services" accent={CK.cyan} className="col-span-12 lg:col-span-5">
        <div className="space-y-1.5">
          <Voyant
            etat={enLigne ? "ok" : "ko"} label="Serveur Orion"
            detail={enLigne ? (statut?.status ?? "en ligne") : "injoignable"}
          />
          <Voyant
            etat={(statut?.controllers?.length ?? 0) > 0 ? "ok" : "tiede"}
            label="Interfaces connectées"
            detail={String(statut?.controllers?.length ?? 0)}
          />
          <Voyant
            etat={(statut?.workers?.length ?? 0) > 0 ? "ok" : "tiede"}
            label="Appareils distants"
            detail={String(statut?.workers?.length ?? 0)}
          />
          <Voyant
            etat={statut?.confirm?.enabled ? "ok" : "tiede"}
            label="Confirmation par mot de passe"
            detail={statut?.confirm?.enabled ? "active" : "désactivée"}
          />
          <Voyant
            etat={panicActif ? "ko" : "ok"} label="Mode panic"
            detail={panicActif ? "ACTIF" : "au repos"}
          />
        </div>
      </Carte>

      {/* ── Pont MCP ── */}
      <Carte
        title="Pont MCP" accent={CK.amber} className="col-span-12 lg:col-span-7"
        right={
          <span className="font-tech flex items-center gap-1 text-[9px] tracking-[0.14em] text-text-dim">
            <Plug size={11} strokeWidth={1.8} /> {mcp?.tool_count ?? 0} outils
          </span>
        }
      >
        {!mcp ? (
          <div className="font-tech flex h-24 items-center justify-center text-[9px]
                          uppercase tracking-[0.2em] text-text-dim">
            Pont indisponible — token serveur requis
          </div>
        ) : (
          <>
            <div className="mb-2 grid grid-cols-2 gap-2">
              <Tuile
                label="Pont" value={mcp.bridge_enabled ? "OUVERT" : "FERMÉ"}
                tone={mcp.bridge_enabled ? CK.green : CK.steel}
              />
              <Tuile
                label="Exécution d'ordres"
                value={mcp.execution_enabled ? "ARMÉE" : "VERROUILLÉE"}
                tone={mcp.execution_enabled ? CK.crimson : CK.green}
              />
            </div>
            <div className="space-y-1.5">
              {(mcp.servers ?? []).map((s) => (
                <Voyant
                  key={s.alias} etat={s.alive ? "ok" : "ko"}
                  label={s.alias} detail={`${s.tools.length} outils`}
                />
              ))}
              {Object.entries(mcp.errors ?? {}).map(([alias, msg]) => (
                <div key={alias} className="rounded-lg border px-3 py-1.5 font-mono text-[10px]"
                     style={{ borderColor: `${CK.crimson}44`, color: CK.crimson }}>
                  {alias} : {msg}
                </div>
              ))}
            </div>
          </>
        )}
      </Carte>

      {/* ── Audit ── */}
      <Carte
        title="Audit — 24 h" accent={CK.cyan} className="col-span-12 lg:col-span-8"
        right={
          <span className="font-tech flex items-center gap-1 text-[9px] tracking-[0.14em] text-text-dim">
            <Database size={11} strokeWidth={1.8} /> {statut?.audit_db_kb ?? 0} Ko
          </span>
        }
      >
        {erreurAudit ? (
          <div className="font-tech flex h-24 items-center justify-center gap-2 text-[9px]
                          uppercase tracking-[0.2em]" style={{ color: CK.amber }}>
            <AlertTriangle size={13} /> {erreurAudit}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-4 gap-2">
              <Tuile label="Appels" value={String(stats.total ?? 0)} />
              <Tuile label="Réussis" value={String(stats.success ?? 0)} tone={CK.green} />
              <Tuile label="Échoués" value={String(stats.failed ?? 0)}
                     tone={(stats.failed ?? 0) > 0 ? CK.crimson : undefined} />
              <Tuile label="Sensibles" value={String(stats.sensitive ?? 0)} tone={CK.amber} />
            </div>
            <div className="mt-3 max-h-40 space-y-0.5 overflow-y-auto font-mono text-[10px]">
              {lignes.length === 0 && (
                <div className="font-tech py-6 text-center text-[9px] uppercase
                                tracking-[0.2em] text-text-dim">
                  Aucun appel sur la période
                </div>
              )}
              {lignes.map((l) => (
                <div key={l.id} className="flex items-center gap-2">
                  <span className="shrink-0 text-text-dim/60">
                    {new Date(l.ts * 1000).toLocaleTimeString("fr-FR")}
                  </span>
                  <span className="shrink-0" style={{ color: l.success ? CK.green : CK.crimson }}>
                    {l.success ? "✓" : "✗"}
                  </span>
                  <span className="shrink-0 text-text">{l.tool_name}</span>
                  {l.sensitive === 1 && (
                    <ShieldAlert size={10} style={{ color: CK.amber }} className="shrink-0" />
                  )}
                  <span className="min-w-0 flex-1 truncate text-text-dim/70">
                    {l.error || l.input_preview}
                  </span>
                  <span className="shrink-0 text-text-dim/50">{l.duration_ms}ms</span>
                </div>
              ))}
            </div>
          </>
        )}
      </Carte>

      {/* ── Coupe-circuit ── */}
      <Carte title="Coupe-circuit" accent={panicActif ? CK.crimson : CK.steel}
             className="col-span-12 lg:col-span-4">
        <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
          {panicActif ? (
            <>
              <ShieldAlert size={26} strokeWidth={1.4} style={{ color: CK.crimson }} />
              <p className="font-rajdhani text-xs text-text">
                Mode panic actif. Toute action est bloquée.
              </p>
              <button
                onClick={async () => { await relacherPanic(); rafraichir(); }}
                className="font-tech rounded-lg border px-4 py-2 text-[10px] uppercase tracking-[0.18em] transition"
                style={{ borderColor: `${CK.green}66`, color: CK.green }}
              >
                Relâcher
              </button>
            </>
          ) : (
            <>
              <ShieldCheck size={26} strokeWidth={1.4} style={{ color: CK.green }} />
              <p className="font-rajdhani text-xs text-text-dim">
                Coupe tout : outils, workers, briefings.
              </p>
              {/* Double détente : un coupe-circuit déclenché par mégarde
                  déconnecte tous les appareils d'un coup. */}
              <button
                onClick={async () => {
                  if (!armePanic) return setArmePanic(true);
                  await declencherPanic("Déclenché depuis le cockpit");
                  setArmePanic(false);
                  rafraichir();
                }}
                onBlur={() => setArmePanic(false)}
                className="font-tech rounded-lg border px-4 py-2 text-[10px] uppercase tracking-[0.18em] transition"
                style={{
                  borderColor: armePanic ? CK.crimson : "rgba(255,255,255,0.12)",
                  color: armePanic ? CK.crimson : "rgba(150,195,225,0.7)",
                  background: armePanic ? `${CK.crimson}18` : "transparent",
                }}
              >
                {armePanic ? "Confirmer l'arrêt" : "Déclencher"}
              </button>
            </>
          )}
          <Activity size={12} className="mt-1 text-text-dim/40" />
        </div>
      </Carte>
    </div>
  );
}
