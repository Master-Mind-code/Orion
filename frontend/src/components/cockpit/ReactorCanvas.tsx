/**
 * Réacteur du cockpit — portage fidèle de la maquette « Cockpit Orion ».
 *
 * Canvas 2D et non WebGL, conformément au design : arcs ambre extérieurs,
 * anneaux cyan, 96 graduations, six plaques orbitales, trois arcs internes,
 * cœur en dégradé radial et nuée de particules. Tous les rayons sont exprimés
 * en fraction de R pour que le rendu soit identique à toute taille.
 *
 * Un canvas 2D suffit ici : le halo, le flou et les traînées sont obtenus par
 * `shadowBlur` et des dégradés, sans le coût d'un contexte WebGL — et le trait
 * reste net, ce qu'un bloom de post-traitement aurait empâté.
 */
import { useEffect, useRef } from "react";

import { SKIN, type CockpitState } from "@/lib/cockpit-theme";

interface Props {
  state?: CockpitState;
  audioLevelRef?: React.MutableRefObject<number>;
  /** `false` fige l'animation : utile pour la capsule, ou en mode sobre. */
  live?: boolean;
  className?: string;
}

/** Convertit #rrggbb en rgba() — le canvas n'accepte pas l'alpha hexadécimal
 *  sur toutes les plateformes, contrairement au CSS. */
function rgba(hex: string, a: number): string {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

interface RingOpts {
  color: string; w?: number; cap?: CanvasLineCap; from?: number; to?: number;
  rot?: number; dash?: number[]; glow?: number;
}

function ring(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number, o: RingOpts) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(o.rot ?? 0);
  ctx.beginPath();
  ctx.arc(0, 0, r, o.from ?? 0, o.to ?? Math.PI * 2);
  ctx.strokeStyle = o.color;
  ctx.lineWidth = o.w ?? 1;
  ctx.lineCap = o.cap ?? "butt";
  if (o.dash) ctx.setLineDash(o.dash);
  if (o.glow) { ctx.shadowColor = o.color; ctx.shadowBlur = o.glow; }
  ctx.stroke();
  ctx.restore();
}

export function ReactorCanvas({ state = "idle", audioLevelRef, live = true, className }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  // L'état passe par une ref : le redémarrer à chaque changement relancerait la
  // boucle et ferait sauter l'animation.
  const etat = useRef(state);
  etat.current = state;

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    const depart = performance.now();

    const frame = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = cv.clientWidth, h = cv.clientHeight;
      if (w && h) {
        if (cv.width !== w * dpr || cv.height !== h * dpr) {
          cv.width = w * dpr; cv.height = h * dpr;
        }
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, w, h);

        const t = (performance.now() - depart) / 1000;
        const skin = SKIN[etat.current];
        const key = skin.key, acc = skin.accent;
        const cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2;
        const s = skin.spin * (live ? 1 : 0.25);
        const niveau = audioLevelRef?.current ?? 0;
        const pulse = 1 + Math.sin(t * 2.1) * 0.03 * skin.glow + niveau * 0.18;

        // ── Halo ──
        ctx.save();
        const halo = ctx.createRadialGradient(cx, cy, 0, cx, cy, R);
        halo.addColorStop(0, rgba(key, 0.22 * skin.glow));
        halo.addColorStop(0.35, rgba(key, 0.07));
        halo.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = halo;
        ctx.fillRect(0, 0, w, h);
        ctx.restore();

        // ── Arcs ambre extérieurs ──
        ring(ctx, cx, cy, R * 0.94, { color: rgba(acc, 0.9), w: 5, cap: "round",
                                      from: -0.4, to: 1.5, rot: t * s * 1.6, glow: 16 });
        ring(ctx, cx, cy, R * 0.94, { color: rgba(acc, 0.35), w: 2,
                                      from: 2.4, to: 3.4, rot: t * s * 1.6 });
        ring(ctx, cx, cy, R * 0.86, { color: rgba(acc, 0.75), w: 2,
                                      dash: [3, 9], rot: -t * s * 1.1 });

        // ── Anneaux cyan ──
        ring(ctx, cx, cy, R * 0.78, { color: rgba(key, 0.5), w: 1, dash: [1, 6] });
        ring(ctx, cx, cy, R * 0.7, { color: rgba(key, 0.85), w: 3, cap: "round",
                                     from: 0.6, to: 4.2, rot: t * s * 2.2, glow: 14 });
        ring(ctx, cx, cy, R * 0.62, { color: rgba(key, 0.3), w: 1 });

        // ── 96 graduations ──
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(t * s * 0.8);
        for (let i = 0; i < 96; i++) {
          const a = (i / 96) * Math.PI * 2;
          const longue = i % 8 === 0;
          const r1 = R * 0.56, r2 = R * (longue ? 0.51 : 0.535);
          ctx.beginPath();
          ctx.moveTo(Math.cos(a) * r1, Math.sin(a) * r1);
          ctx.lineTo(Math.cos(a) * r2, Math.sin(a) * r2);
          ctx.strokeStyle = rgba(key, longue ? 0.75 : 0.3);
          ctx.lineWidth = longue ? 1.6 : 1;
          ctx.stroke();
        }
        ctx.restore();

        // ── Six plaques orbitales ──
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(-t * s * 1.4);
        for (let i = 0; i < 6; i++) {
          const a = (i / 6) * Math.PI * 2;
          const r = R * 0.42;
          ctx.save();
          ctx.translate(Math.cos(a) * r, Math.sin(a) * r);
          ctx.rotate(a + Math.PI / 2 + t * 0.6);
          ctx.strokeStyle = rgba(key, 0.85);
          ctx.lineWidth = 1.4;
          ctx.shadowColor = key;
          ctx.shadowBlur = 10;
          const sz = R * 0.075;
          ctx.strokeRect(-sz / 2, -sz / 2, sz, sz);
          ctx.strokeStyle = rgba(key, 0.35);
          ctx.strokeRect(-sz * 0.8, -sz * 0.8, sz * 1.6, sz * 1.6);
          ctx.restore();
        }
        ctx.restore();

        // ── Trois arcs internes lumineux ──
        for (let i = 0; i < 3; i++) {
          const r = R * (0.3 - i * 0.07) * pulse;
          ring(ctx, cx, cy, r, {
            color: rgba(key, 0.95 - i * 0.2), w: 3 - i * 0.6, cap: "round",
            from: i * 1.3, to: i * 1.3 + 4.6 + Math.sin(t + i) * 0.5,
            rot: t * (s * (3 + i * 2)) * (i % 2 ? -1 : 1), glow: 18,
          });
        }

        // ── Cœur ──
        const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.2 * pulse);
        core.addColorStop(0, "rgba(255,255,255,.95)");
        core.addColorStop(0.25, rgba(key, 0.85));
        core.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = core;
        ctx.beginPath();
        ctx.arc(cx, cy, R * 0.2 * pulse, 0, Math.PI * 2);
        ctx.fill();

        // ── Particules ──
        if (live) {
          for (let i = 0; i < 60; i++) {
            const graine = i * 12.9898;
            const a = (graine % (Math.PI * 2)) + t * (0.15 + (i % 5) * 0.05) * (i % 2 ? 1 : -1);
            const rr = R * (0.5 + ((i * 37) % 55) / 100);
            // Ellipse aplatie (1.12 / 0.62) : suggère un plan orbital vu en
            // plongée plutôt qu'un nuage sphérique.
            const x = cx + Math.cos(a) * rr * 1.12;
            const y = cy + Math.sin(a) * rr * 0.62;
            ctx.fillStyle = rgba(i % 7 === 0 ? acc : key, 0.15 + ((i * 13) % 60) / 140);
            ctx.fillRect(x, y, 1.6, 1.6);
          }
        }
      }
      raf = requestAnimationFrame(frame);
    };

    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [audioLevelRef, live]);

  return <canvas ref={ref} className={className}
                 style={{ width: "100%", height: "100%", display: "block" }} />;
}
