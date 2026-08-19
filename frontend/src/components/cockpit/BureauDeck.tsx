/**
 * Poste de contrôle du bureau — le pendant du poste de trading.
 *
 * Aperçu de l'écran en direct, fenêtres ouvertes avec vignettes, presse-papier.
 * Tout passe par la coque Electron : dans un navigateur ordinaire ces capacités
 * n'existent pas, et le composant le dit au lieu d'afficher des cadres vides.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, Clipboard, Copy, Minimize2, Monitor, Pin, RefreshCw, X } from "lucide-react";

import { CK } from "@/lib/cockpit-theme";
import {
  agirFenetre, captureEcran, ecrirePressePapier, estBureau,
  listerFenetres, lirePressePapier,
  type EcranCapture, type FenetreOuverte,
} from "@/lib/desktop";
import { appelerTool } from "@/lib/orionApi";

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

function BoutonHud({ icon: Icon, label, onClick, actif }: {
  icon: typeof Camera; label: string; onClick: () => void; actif?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className="font-tech flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5
                 text-[9px] uppercase tracking-[0.16em] transition hover:brightness-125"
      style={{
        borderColor: actif ? CK.cyan : "rgba(255,255,255,0.08)",
        color: actif ? CK.cyan : "rgba(150,195,225,0.75)",
        background: actif ? `${CK.cyan}14` : "rgba(255,255,255,0.02)",
      }}
    >
      <Icon size={12} strokeWidth={1.8} />
      {label}
    </button>
  );
}

export function BureauDeck() {
  const dispo = estBureau();
  const [ecrans, setEcrans] = useState<EcranCapture[]>([]);
  const [fenetres, setFenetres] = useState<FenetreOuverte[]>([]);
  const [presse, setPresse] = useState("");
  const [auto, setAuto] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState<string | null>(null);
  const minuteur = useRef<number | null>(null);

  const rafraichir = useCallback(async () => {
    if (!dispo) return;
    try {
      const [e, f, p] = await Promise.all([
        captureEcran(1400), listerFenetres(320), lirePressePapier(),
      ]);
      setEcrans(e);
      setFenetres(f);
      setPresse(p);
      setErreur(null);
    } catch (exc) {
      setErreur(exc instanceof Error ? exc.message : String(exc));
    }
  }, [dispo]);

  useEffect(() => {
    rafraichir();
  }, [rafraichir]);

  // Rafraîchissement périodique. 2 s : plus court, la capture de tous les
  // écrans devient coûteuse et fait chuter le rendu du réacteur.
  useEffect(() => {
    if (!auto || !dispo) return;
    minuteur.current = window.setInterval(rafraichir, 2000);
    return () => { if (minuteur.current) window.clearInterval(minuteur.current); };
  }, [auto, dispo, rafraichir]);

  /** Electron sait ENUMERER les fenetres mais pas les piloter : activer,
   *  reduire ou fermer la fenetre d'une autre application demande l'API Win32.
   *  On passe donc par les tools d'Orion (server/tools/windows_ctrl.py). */
  const agirSurFenetre = useCallback(
    async (titre: string, action: "focus" | "reduire" | "fermer") => {
      setEnCours(titre + action);
      const r = action === "focus"
        ? await appelerTool("focus_window", { title_contains: titre })
        : await appelerTool("window_control", {
            title_contains: titre,
            action: action === "reduire" ? "minimize" : "close",
          });
      setEnCours(null);
      if (r.success === false) setErreur(String(r.error ?? "Action refusée"));
      else { setErreur(null); rafraichir(); }
    },
    [rafraichir],
  );

  if (!dispo) {
    return (
      <Carte title="Pilotage du bureau" accent={CK.amber} className="h-full">
        <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
          <Monitor size={30} strokeWidth={1.2} className="text-text-dim" />
          <p className="font-rajdhani text-sm text-text">
            Ce mode a besoin de la coque de bureau d'Orion.
          </p>
          <p className="font-tech max-w-md text-[10px] uppercase leading-relaxed tracking-[0.16em] text-text-dim/70">
            Un navigateur ne peut ni capturer l'écran ni lister les fenêtres.
            Lance Orion en application : npm --prefix desktop run dev
          </p>
        </div>
      </Carte>
    );
  }

  return (
    <div className="grid h-full auto-rows-min grid-cols-12 gap-3 overflow-y-auto pr-1">
      {/* ── Barre d'actions ── */}
      <div className="col-span-12 flex flex-wrap items-center gap-2">
        <BoutonHud icon={RefreshCw} label="Rafraîchir" onClick={rafraichir} />
        <BoutonHud icon={Camera} label="Auto 2s" onClick={() => setAuto((a) => !a)} actif={auto} />
        <BoutonHud icon={Pin} label="Épingler" onClick={() => agirFenetre("epingler")} />
        <span className="font-tech ml-auto text-[9px] uppercase tracking-[0.16em] text-text-dim">
          {ecrans.length} écran{ecrans.length > 1 ? "s" : ""} · {fenetres.length} fenêtres
        </span>
      </div>

      {erreur && (
        <div className="col-span-12 rounded-lg border px-3 py-2 font-mono text-[11px]"
             style={{ borderColor: `${CK.crimson}44`, color: CK.crimson }}>
          {erreur}
        </div>
      )}

      {/* ── Écran en direct ── */}
      <Carte title="Écran" accent={CK.cyan} className="col-span-12 lg:col-span-7">
        {ecrans.length === 0 ? (
          <div className="font-tech flex h-40 items-center justify-center text-[9px]
                          uppercase tracking-[0.2em] text-text-dim">
            Capture en cours…
          </div>
        ) : (
          <div className="space-y-2">
            {ecrans.map((e) => (
              <figure key={e.id} className="overflow-hidden rounded-lg border border-white/[0.06]">
                <img src={e.apercu} alt={e.nom} className="block w-full" />
                <figcaption className="font-tech flex justify-between px-2 py-1
                                       text-[8px] uppercase tracking-[0.16em] text-text-dim">
                  <span>{e.nom}</span>
                  {e.taille && <span>{e.taille.largeur}×{e.taille.hauteur}</span>}
                </figcaption>
              </figure>
            ))}
          </div>
        )}
      </Carte>

      {/* ── Presse-papier ── */}
      <Carte
        title="Presse-papier" accent={CK.amber} className="col-span-12 lg:col-span-5"
        right={
          <span className="font-tech text-[9px] tracking-[0.14em] text-text-dim">
            {presse.length} car.
          </span>
        }
      >
        <textarea
          value={presse}
          onChange={(ev) => setPresse(ev.target.value)}
          spellCheck={false}
          className="h-24 w-full resize-none rounded-lg border border-white/[0.06]
                     bg-black/30 p-2 font-mono text-[11px] text-text outline-none
                     focus:border-cyan/40"
        />
        <div className="mt-2 flex gap-2">
          <BoutonHud icon={Copy} label="Écrire" onClick={() => ecrirePressePapier(presse)} />
          <BoutonHud icon={Clipboard} label="Relire" onClick={async () => setPresse(await lirePressePapier())} />
        </div>
      </Carte>

      {/* ── Fenêtres ── */}
      <Carte title="Fenêtres ouvertes" accent={CK.cyan} className="col-span-12">
        {fenetres.length === 0 ? (
          <div className="font-tech flex h-24 items-center justify-center text-[9px]
                          uppercase tracking-[0.2em] text-text-dim">
            Aucune fenêtre détectée
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-4">
            {fenetres.map((f) => (
              <div key={f.id}
                   className="overflow-hidden rounded-lg border border-white/[0.06] bg-white/[0.02]">
                {f.apercu
                  ? <img src={f.apercu} alt={f.titre} className="block h-24 w-full object-cover" />
                  : <div className="h-24 w-full bg-black/40" />}
                <div className="flex items-center gap-1 px-2 py-1.5">
                  <span className="font-rajdhani min-w-0 flex-1 truncate text-[11px] text-text"
                        title={f.titre}>
                    {f.titre}
                  </span>
                  <button
                    className="rounded p-1 text-text-dim transition hover:bg-white/10 hover:text-cyan disabled:opacity-40"
                    title="Mettre au premier plan"
                    disabled={enCours === f.titre + "focus"}
                    onClick={() => agirSurFenetre(f.titre, "focus")}
                  >
                    <Monitor size={11} strokeWidth={1.8} />
                  </button>
                  <button
                    className="rounded p-1 text-text-dim transition hover:bg-white/10 hover:text-cyan disabled:opacity-40"
                    title="Réduire"
                    disabled={enCours === f.titre + "reduire"}
                    onClick={() => agirSurFenetre(f.titre, "reduire")}
                  >
                    <Minimize2 size={11} strokeWidth={1.8} />
                  </button>
                  <button
                    className="rounded p-1 text-text-dim transition hover:bg-red/70 hover:text-white disabled:opacity-40"
                    title="Fermer (le travail non enregistré peut être perdu)"
                    disabled={enCours === f.titre + "fermer"}
                    onClick={() => agirSurFenetre(f.titre, "fermer")}
                  >
                    <X size={11} strokeWidth={1.8} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Carte>
    </div>
  );
}
