/**
 * Les deux cadrans dessinés au canvas — globe de mémoire et spectre voix.
 *
 * Portage fidèle de la maquette. Ils prennent la teinte de l'état courant :
 * quand Orion passe en écoute, tout le cockpit vire au vert d'un bloc. Des
 * couleurs figées casseraient cette lecture d'un coup d'œil.
 */
import { useEffect, useRef } from "react";

import { SKIN, type CockpitState } from "@/lib/cockpit-theme";

function rgba(hex: string, a: number): string {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

/** Prépare le canvas au ratio de pixels de l'écran. Sans ça, tout est flou. */
function ajuster(cv: HTMLCanvasElement) {
  const ctx = cv.getContext("2d");
  if (!ctx) return null;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = cv.clientWidth, h = cv.clientHeight;
  if (!w || !h) return null;
  if (cv.width !== w * dpr || cv.height !== h * dpr) {
    cv.width = w * dpr; cv.height = h * dpr;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return { ctx, w, h };
}

/* ─────────────────────────── Globe de mémoire ─────────────────────────── */

const LAT = 9, LON = 16;

export function GlobeMemoire({ state = "idle" }: { state?: CockpitState }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const etat = useRef(state);
  etat.current = state;

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    let raf = 0;
    const t0 = performance.now();

    const frame = () => {
      const f = ajuster(cv);
      if (f) {
        const { ctx, w, h } = f;
        const t = (performance.now() - t0) / 1000;
        const skin = SKIN[etat.current];
        const key = skin.key;
        const cx = w / 2, cy = h / 2, R = Math.min(w, h) * 0.42;
        const rotY = t * 0.28;

        // Grille latitude/longitude : les arêtes suivent les parallèles et les
        // méridiens, ce qui donne la lecture « globe ». Une répartition en
        // spirale serait mieux distribuée mais ne dessinerait aucune maille.
        const pts: { x: number; y: number; z: number; i: number; j: number }[] = [];
        for (let i = 1; i < LAT; i++) {
          const phi = (i / LAT) * Math.PI;
          for (let j = 0; j < LON; j++) {
            const th = (j / LON) * Math.PI * 2 + rotY;
            const x = Math.sin(phi) * Math.cos(th);
            const y = Math.cos(phi);
            const z = Math.sin(phi) * Math.sin(th);
            pts.push({ x: cx + x * R, y: cy + y * R * 0.94, z, i, j });
          }
        }

        ctx.lineWidth = 0.7;
        for (const p of pts) {
          const droite = pts.find((q) => q.i === p.i && q.j === (p.j + 1) % LON);
          const bas = pts.find((q) => q.i === p.i + 1 && q.j === p.j);
          // La profondeur module l'opacité : la face arrière s'efface, ce qui
          // suffit à donner le volume sans test de visibilité.
          const dep = 0.14 + ((p.z + 1) / 2) * 0.4;
          ctx.strokeStyle = rgba(key, dep * 0.55);
          for (const q of [droite, bas]) {
            if (!q) continue;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.stroke();
          }
          if ((p.i * LON + p.j) % 11 === 0) {
            ctx.fillStyle = rgba(p.z > 0 ? skin.accent : key, 0.35 + ((p.z + 1) / 2) * 0.5);
            ctx.beginPath();
            ctx.arc(p.x, p.y, 1.7, 0, Math.PI * 2);
            ctx.fill();
          }
        }

        // Anneau incliné qui oscille autour du globe.
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(Math.sin(t * 0.4) * 0.5);
        ctx.strokeStyle = rgba(key, 0.4);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.ellipse(0, 0, R * 1.24, R * 0.3, 0.5, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, []);

  return <canvas ref={ref} style={{ width: "100%", height: "100%", display: "block" }} />;
}

/* ───────────────────────────── Spectre voix ───────────────────────────── */

const NB_BARRES = 54;

export function SpectreCanvas({ state = "idle", levelRef, live = true }: {
  state?: CockpitState;
  levelRef?: React.MutableRefObject<number>;
  live?: boolean;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const etat = useRef(state);
  etat.current = state;
  const barres = useRef<number[]>(Array(NB_BARRES).fill(0.02));

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    let raf = 0;
    const t0 = performance.now();

    const frame = () => {
      const f = ajuster(cv);
      if (f) {
        const { ctx, w, h } = f;
        const t = (performance.now() - t0) / 1000;
        const skin = SKIN[etat.current];
        const b = barres.current;
        const n = b.length, mid = h / 2, bw = w / n;
        // Niveau minimal même au repos : un spectre parfaitement plat donne
        // l'impression que le micro est mort.
        const lv = Math.max(0.12, levelRef?.current ?? 0) * (live ? 1 : 0.4);

        for (let i = 0; i < n; i++) {
          const c = 1 - Math.abs(i - n / 2) / (n / 2);
          // Trois sinusoïdes incommensurables : le motif ne se répète jamais
          // visiblement, contrairement à une seule onde.
          const bruit = Math.sin(t * 6.3 + i * 0.7) * 0.5
                      + Math.sin(t * 11.7 + i * 1.9) * 0.3
                      + Math.sin(t * 3.1 + i * 0.31) * 0.2;
          const cible = Math.max(0.02, (0.25 + c * 0.75) * lv * (0.55 + Math.abs(bruit) * 0.8));
          b[i] += (cible - b[i]) * 0.28; // lissage : évite le clignotement
          const bh = b[i] * h * 0.92;
          const x = i * bw + bw * 0.22;
          ctx.fillStyle = rgba(Math.abs(i - n / 2) < 3 ? skin.accent : skin.key, 0.55 + b[i] * 0.5);
          ctx.shadowColor = skin.key;
          ctx.shadowBlur = 8;
          ctx.fillRect(x, mid - bh / 2, Math.max(1.4, bw * 0.5), bh);
        }

        ctx.shadowBlur = 0;
        ctx.beginPath();
        for (let i = 0; i < n; i++) {
          const x = i * bw + bw / 2;
          const y = mid - b[i] * h * 0.55;
          i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
        }
        ctx.strokeStyle = rgba(skin.accent, 0.75);
        ctx.lineWidth = 1.4;
        ctx.stroke();

        ctx.beginPath();
        for (let i = 0; i < n; i++) {
          const x = i * bw + bw / 2;
          const y = mid + b[i] * h * 0.55;
          i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
        }
        ctx.strokeStyle = rgba(skin.key, 0.18);
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [levelRef, live]);

  return <canvas ref={ref} style={{ width: "100%", height: "100%", display: "block" }} />;
}
