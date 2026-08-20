/**
 * Cœur animé vidéo holographique d'Orion.
 *
 * Utilise la vidéo haute-technologie `orion_animated_core.mp4` avec masque radial,
 * anneaux HUD rotatifs, réactivité audio et lueurs holographiques réactives (cyan, magenta, or, rouge).
 */
import { useEffect, useRef } from "react";
import { SKIN, type CockpitState } from "@/lib/cockpit-theme";

interface VideoCoreProps {
  state?: CockpitState;
  audioLevelRef?: React.MutableRefObject<number>;
  satellites?: boolean;
  className?: string;
}

export function VideoCore({
  state = "idle",
  audioLevelRef,
  className = "",
}: VideoCoreProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const skin = SKIN[state];

  useEffect(() => {
    let animId: number;

    const animer = () => {
      const level = audioLevelRef?.current ?? 0;
      if (containerRef.current) {
        const scale = 1 + level * 0.18 + Math.sin(Date.now() * 0.003) * 0.02;
        containerRef.current.style.transform = `scale(${scale})`;
      }
      animId = requestAnimationFrame(animer);
    };

    animer();
    return () => cancelAnimationFrame(animId);
  }, [audioLevelRef]);

  return (
    <div className={`relative flex items-center justify-center overflow-hidden ${className}`}>
      {/* Halo de lueur diffuse externe */}
      <div
        className="absolute inset-0 rounded-full transition-all duration-700 blur-2xl"
        style={{
          background: `radial-gradient(circle at 50% 50%, ${skin.key}55 0%, ${skin.accent}22 50%, transparent 75%)`,
          opacity: state === "speaking" || state === "listening" ? 0.9 : 0.6,
        }}
      />

      {/* Conteneur principal de la vidéo de réacteur */}
      <div
        ref={containerRef}
        className="relative h-[82%] w-[82%] transition-transform duration-100 ease-out"
      >
        {/* Anneau HUD externe rotatif rapide */}
        <div
          className="absolute -inset-6 rounded-full border border-dashed animate-spin-slow pointer-events-none"
          style={{
            borderColor: `${skin.key}44`,
            animationDuration: state === "processing" ? "4s" : "20s",
          }}
        />

        {/* Anneau d'arcs HUD concentriques */}
        <svg className="absolute -inset-10 h-[120%] w-[120%] animate-spin-reverse pointer-events-none opacity-80" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="46"
            fill="none"
            stroke={skin.key}
            strokeWidth="0.5"
            strokeDasharray="4 8 12 8"
          />
          <circle
            cx="50"
            cy="50"
            r="48"
            fill="none"
            stroke={skin.accent}
            strokeWidth="0.3"
            strokeDasharray="1 4 2 4"
          />
        </svg>

        {/* Masque circulaire avec vidéo animée */}
        <div
          className="relative h-full w-full overflow-hidden rounded-full shadow-2xl"
          style={{
            boxShadow: `0 0 45px ${skin.key}66, inset 0 0 25px ${skin.key}44`,
            border: `1.5px solid ${skin.key}88`,
          }}
        >
          <video
            ref={videoRef}
            src="/orion_animated_core.mp4"
            autoPlay
            loop
            muted
            playsInline
            className="h-full w-full object-cover mix-blend-screen scale-110"
            style={{
              filter: `contrast(1.15) brightness(1.1) drop-shadow(0 0 12px ${skin.key})`,
            }}
          />

          {/* Grille de balayage holographique */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: `linear-gradient(180deg, transparent 0%, ${skin.key}15 50%, transparent 100%)`,
              backgroundSize: "100% 6px",
            }}
          />
        </div>
      </div>

      {/* Libellé d'état HUD central bas */}
      <div
        className="font-tech absolute bottom-2 rounded-full px-3 py-0.5 text-[9px] uppercase tracking-[0.3em] backdrop-blur-md"
        style={{
          color: skin.key,
          border: `1px solid ${skin.key}44`,
          background: "rgba(4, 6, 13, 0.75)",
        }}
      >
        {state.toUpperCase()}
      </div>
    </div>
  );
}
