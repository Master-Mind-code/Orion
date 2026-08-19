/**
 * Modules satellites gravitant autour du réacteur — radar, jauges, spectre,
 * molécules, globe filaire.
 *
 * Ils vivent dans LE MÊME canvas que le cœur : ils partagent son bloom et son
 * repère de profondeur. Des canvas séparés multiplieraient les contextes WebGL
 * et casseraient la cohérence du halo.
 *
 * Le placement est exprimé en fraction du viewport 3D (et non en unités fixes) :
 * sur un écran étroit, des positions figées enverraient les satellites hors
 * champ. En dessous d'une certaine largeur ils s'effacent d'eux-mêmes.
 */
import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/* ────────────────────────── Briques réutilisables ───────────────────────── */

/** Cercle en fil de fer — la base de tous les cadrans. */
function Circle({ r, color, opacity = 0.5, segments = 64 }: {
  r: number; color: string; opacity?: number; segments?: number;
}) {
  const pts = useMemo(() => {
    const p: THREE.Vector3[] = [];
    for (let i = 0; i <= segments; i++) {
      const a = (i / segments) * Math.PI * 2;
      p.push(new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r, 0));
    }
    return p;
  }, [r, segments]);
  const geo = useMemo(() => new THREE.BufferGeometry().setFromPoints(pts), [pts]);
  return (
    <line>
      <primitive object={geo} attach="geometry" />
      <lineBasicMaterial color={color} transparent opacity={opacity} toneMapped={false} />
    </line>
  );
}

/* ──────────────────────────────── Radar ─────────────────────────────────── */

function Radar({ r = 1.02, color, speed = 0.9 }: { r?: number; color: string; speed?: number }) {
  const sweep = useRef<THREE.Mesh>(null);
  const blips = useRef<THREE.Group>(null);

  useFrame((_, dt) => {
    if (sweep.current) sweep.current.rotation.z -= speed * dt;
    if (blips.current) blips.current.rotation.z -= speed * dt * 0.12;
  });

  const spokes = useMemo(
    () => Array.from({ length: 12 }, (_, i) => (i / 12) * Math.PI * 2),
    [],
  );
  const echos = useMemo(
    () => [0.62, 2.4, 4.1, 5.6].map((a, i) => ({
      a, d: r * (0.32 + i * 0.17),
    })),
    [r],
  );

  return (
    <group>
      {[0.34, 0.62, 0.85, 1].map((f) => (
        <Circle key={f} r={r * f} color={color} opacity={f === 1 ? 0.75 : 0.28} />
      ))}
      {spokes.map((a, i) => (
        <mesh key={i} rotation={[0, 0, a]} position={[Math.cos(a) * r * 0.5, Math.sin(a) * r * 0.5, 0]}>
          <boxGeometry args={[r, 0.004, 0.002]} />
          <meshBasicMaterial color={color} transparent opacity={0.16} toneMapped={false} />
        </mesh>
      ))}

      {/* Balayage : un secteur dégradé, comme sur un vrai écran radar */}
      <mesh ref={sweep} position={[0, 0, 0.002]}>
        <ringGeometry args={[0, r, 40, 1, 0, Math.PI * 0.42]} />
        <meshBasicMaterial color={color} transparent opacity={0.22} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>

      <group ref={blips}>
        {echos.map(({ a, d }, i) => (
          <mesh key={i} position={[Math.cos(a) * d, Math.sin(a) * d, 0.004]}>
            <circleGeometry args={[0.028, 10]} />
            <meshBasicMaterial color={color} toneMapped={false} />
          </mesh>
        ))}
      </group>
    </group>
  );
}

/* ─────────────────────────────── Jauge ──────────────────────────────────── */

const GAUGE_SEG = 48;

function RingGauge({ r = 0.34, value = 0.68, color, accent }: {
  r?: number; value?: number; color: string; accent: string;
}) {
  const arc = useRef<THREE.Mesh>(null);
  const t = useRef(Math.random() * 10);

  // Anneau complet construit UNE fois ; l'arc visible est obtenu en limitant le
  // nombre d'indices dessinés. Reconstruire la géométrie à chaque frame
  // rechargerait le GPU et ferait travailler le ramasse-miettes en continu.
  const geo = useMemo(
    () => new THREE.RingGeometry(r * 0.74, r, GAUGE_SEG, 1),
    [r],
  );

  useFrame((_, dt) => {
    t.current += dt;
    if (!arc.current) return;
    // La valeur oscille autour de sa consigne : une jauge parfaitement figée
    // trahit immédiatement la maquette.
    const v = THREE.MathUtils.clamp(value + Math.sin(t.current * 0.7) * 0.09, 0.04, 0.99);
    arc.current.geometry.setDrawRange(0, Math.max(6, Math.round(GAUGE_SEG * v) * 6));
  });

  return (
    <group>
      <mesh>
        <ringGeometry args={[r * 0.74, r, GAUGE_SEG]} />
        <meshBasicMaterial color={color} transparent opacity={0.1} toneMapped={false} />
      </mesh>
      <mesh ref={arc} geometry={geo} position={[0, 0, 0.002]}>
        <meshBasicMaterial color={accent} transparent opacity={0.95} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>
      <Circle r={r * 1.16} color={color} opacity={0.3} />
    </group>
  );
}

/* ─────────────────────────────── Spectre ────────────────────────────────── */

function BarField({ count = 26, width = 2.05, color, accent, levelRef }: {
  count?: number; width?: number; color: string; accent: string;
  levelRef?: React.MutableRefObject<number>;
}) {
  const group = useRef<THREE.Group>(null);
  const t = useRef(0);
  const seeds = useMemo(
    () => Array.from({ length: count }, () => 0.35 + Math.random() * 0.65),
    [count],
  );
  const step = width / count;

  useFrame((_, dt) => {
    t.current += dt;
    const lvl = levelRef?.current ?? 0;
    group.current?.children.forEach((c, i) => {
      const h = seeds[i] * (0.45 + Math.abs(Math.sin(t.current * 2.1 + i * 0.55)) * 0.55) * (1 + lvl);
      c.scale.y = Math.max(0.06, h);
      c.position.y = (c.scale.y * 0.34) / 2;
    });
  });

  return (
    <group ref={group} position={[-width / 2, 0, 0]}>
      {seeds.map((_, i) => (
        <mesh key={i} position={[i * step, 0, 0]}>
          <boxGeometry args={[step * 0.55, 0.34, 0.02]} />
          <meshBasicMaterial
            color={i % 5 === 0 ? accent : color}
            transparent
            opacity={0.9}
            toneMapped={false}
          />
        </mesh>
      ))}
    </group>
  );
}

/* ───────────────────────── Molécules hexagonales ────────────────────────── */

function HexCluster({ color, accent }: { color: string; accent: string }) {
  const group = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    if (!group.current) return;
    group.current.rotation.z += dt * 0.18;
    group.current.rotation.y = Math.sin(performance.now() * 0.0004) * 0.5;
  });
  const nodes = useMemo(
    () => [
      { p: [0, 0, 0], s: 0.23 },
      { p: [0.46, 0.28, 0.05], s: 0.16 },
      { p: [-0.42, 0.35, -0.04], s: 0.14 },
      { p: [0.09, -0.53, 0.03], s: 0.18 },
    ] as { p: [number, number, number]; s: number }[],
    [],
  );
  return (
    <group ref={group}>
      {nodes.map((n, i) => (
        <group key={i} position={n.p}>
          {/* ringGeometry à 6 segments = hexagone régulier */}
          <mesh>
            <ringGeometry args={[n.s * 0.8, n.s, 6]} />
            <meshBasicMaterial
              color={i === 0 ? accent : color}
              transparent opacity={0.85} side={THREE.DoubleSide} toneMapped={false}
            />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/* ─────────────────────────────── Globe ──────────────────────────────────── */

function WireGlobe({ r = 0.54, color }: { r?: number; color: string }) {
  const mesh = useRef<THREE.Mesh>(null);
  useFrame((_, dt) => {
    if (mesh.current) mesh.current.rotation.y += dt * 0.28;
  });
  return (
    <group rotation={[0.42, 0, 0.18]}>
      <mesh ref={mesh}>
        <sphereGeometry args={[r, 12, 8]} />
        <meshBasicMaterial color={color} wireframe transparent opacity={0.55} toneMapped={false} />
      </mesh>
      <Circle r={r * 1.35} color={color} opacity={0.45} />
    </group>
  );
}

/* ───────────────────────── Placement autour du cœur ─────────────────────── */

/** Flottement lent : sans lui, les satellites paraissent collés à la vitre. */
function Float({ children, seed = 0, position }: {
  children: React.ReactNode; seed?: number; position: [number, number, number];
}) {
  const g = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    if (!g.current) return;
    const t = clock.elapsedTime + seed;
    g.current.position.y = position[1] + Math.sin(t * 0.6) * 0.045;
    g.current.rotation.x = Math.sin(t * 0.4) * 0.12;
    g.current.rotation.y = Math.cos(t * 0.33) * 0.16;
  });
  return <group ref={g} position={position}>{children}</group>;
}

export function Satellites({ color, accent, levelRef }: {
  color: string; accent: string; levelRef?: React.MutableRefObject<number>;
}) {
  const { viewport } = useThree();
  const halfW = viewport.width / 2;
  const halfH = viewport.height / 2;

  // Sous cette largeur, le cœur occupe déjà tout : on n'ajoute rien plutôt que
  // d'empiler les satellites par-dessus les anneaux.
  if (viewport.width < 9.4) return null;

  const x = Math.min(halfW - 1.5, 4.5);
  const y = Math.min(halfH - 0.95, 1.95);

  return (
    <group>
      <Float position={[-x, y * 0.72, -0.6]} seed={0}>
        <group scale={1.12}><Radar color={color} /></group>
      </Float>

      <Float position={[x, y * 0.78, -0.5]} seed={1.7}>
        <group scale={1.05}>
          <RingGauge r={0.4} value={0.72} color={color} accent={accent} />
          <group position={[0.98, 0, 0]}>
            <RingGauge r={0.27} value={0.46} color={color} accent={color} />
          </group>
        </group>
      </Float>

      <Float position={[x * 0.98, -y * 0.82, -0.55]} seed={3.1}>
        <BarField color={color} accent={accent} levelRef={levelRef} />
      </Float>

      <Float position={[-x * 0.99, -y * 0.86, -0.5]} seed={4.6}>
        <HexCluster color={color} accent={accent} />
      </Float>

      <Float position={[-x * 0.78, -y * 1.06, -1.1]} seed={6.2}>
        <WireGlobe color={color} />
      </Float>

      <Float position={[x * 0.6, y * 1.06, -1.2]} seed={7.9}>
        <group scale={0.95}><RingGauge r={0.3} value={0.35} color={color} accent={accent} /></group>
      </Float>
    </group>
  );
}
