/**
 * Capsule flottante — la présence permanente d'Orion sur le bureau.
 *
 * Petite fenêtre ronde, toujours au-dessus, sans bordure. Un clic ouvre ou
 * masque le cockpit. La zone de glissement est déclarée en CSS Electron
 * (`-webkit-app-region`), sinon la fenêtre sans cadre est immobile.
 */
import { useEffect, useRef, useState } from "react";

import { VideoCore } from "@/components/cockpit/VideoCore";
import { SKIN, type CockpitState } from "@/lib/cockpit-theme";
import { pont } from "@/lib/desktop";
import { serveurEnLigne } from "@/lib/orionApi";

export function CapsuleUI() {
  const [state, setState] = useState<CockpitState>("idle");
  const audioLevelRef = useRef(0);
  const skin = SKIN[state];

  useEffect(() => {
    let vivant = true;
    const sonder = async () => {
      const ok = await serveurEnLigne();
      if (vivant) setState((prev) => (ok ? (prev === "alert" ? "idle" : prev) : "alert"));
    };
    sonder();
    const id = window.setInterval(sonder, 8000);

    // Écoute les mises à jour en direct de la capsule depuis Electron main
    const p = pont();
    if (p?.onCapsuleUpdate) {
      p.onCapsuleUpdate((newState: CockpitState) => {
        if (vivant && newState) setState(newState);
      });
    }

    return () => { vivant = false; window.clearInterval(id); };
  }, []);

  return (
    <div
      className="relative h-screen w-screen select-none overflow-hidden rounded-full"
      style={{
        background: "radial-gradient(circle at 50% 45%, rgba(8,18,38,0.88) 0%, rgba(2,5,12,0.96) 70%, transparent 100%)",
        border: `1.5px solid ${skin.key}55`,
        boxShadow: `0 0 35px ${skin.key}44`,
        WebkitAppRegion: "drag",
      } as React.CSSProperties}
    >
      {/* Le réacteur vidéo holographique d'Orion */}
      <VideoCore
        state={state}
        audioLevelRef={audioLevelRef}
        className="h-full w-full p-2"
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
