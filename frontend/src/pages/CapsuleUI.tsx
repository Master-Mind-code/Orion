/**
 * Capsule flottante — la présence permanente d'Orion sur le bureau.
 *
 * Petite fenêtre ronde, toujours au-dessus, sans bordure. Un clic ouvre ou
 * masque le cockpit. La zone de glissement est déclarée en CSS Electron
 * (`-webkit-app-region`), sinon la fenêtre sans cadre est immobile.
 */
import { useEffect, useRef, useState } from "react";

import { ReactorCore } from "@/components/cockpit/ReactorCore";
import { SKIN, type CockpitState } from "@/lib/cockpit-theme";
import { pont } from "@/lib/desktop";
import { serveurEnLigne } from "@/lib/orionApi";

export function CapsuleUI() {
  const [state, setState] = useState<CockpitState>("idle");
  const audioLevelRef = useRef(0);
  const skin = SKIN[state];

  // Témoin d'état : la capsule vire à l'alerte quand le serveur Orion ne répond
  // plus. Un simple ping suffit — ouvrir un WebSocket depuis une fenêtre
  // toujours affichée doublerait inutilement les connexions du cockpit.
  useEffect(() => {
    let vivant = true;
    const sonder = async () => {
      const ok = await serveurEnLigne();
      if (vivant) setState(ok ? "idle" : "alert");
    };
    sonder();
    const id = window.setInterval(sonder, 8000);
    return () => { vivant = false; window.clearInterval(id); };
  }, []);

  return (
    <div
      className="relative h-screen w-screen select-none overflow-hidden rounded-full"
      // La bordure et le fond translucide détachent la capsule du bureau ;
      // sans eux la fenêtre transparente donne un réacteur qui flotte à nu.
      style={{
        background: "radial-gradient(circle at 50% 45%, rgba(8,18,38,0.82) 0%, rgba(2,5,12,0.92) 70%, transparent 100%)",
        border: `1px solid ${skin.key}33`,
        WebkitAppRegion: "drag",
      } as React.CSSProperties}
    >
      {/* Le réacteur sans satellites : à 190 px ils seraient illisibles. */}
      <ReactorCore
        state={state}
        audioLevelRef={audioLevelRef}
        satellites={false}
        className="h-full w-full"
      />

      <button
        onClick={() => pont()?.cockpit("basculer")}
        title="Ouvrir ou masquer le cockpit"
        className="absolute inset-0 h-full w-full cursor-pointer bg-transparent"
        // Le bouton doit rester cliquable : sans no-drag, la zone de glissement
        // du parent avale l'événement.
        style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}
      >
        <span className="sr-only">Basculer le cockpit</span>
      </button>

      <div
        className="font-tech pointer-events-none absolute inset-x-0 bottom-3 text-center
                   text-[8px] uppercase tracking-[0.28em]"
        style={{ color: `${skin.key}bb` }}
      >
        Orion
      </div>
    </div>
  );
}
