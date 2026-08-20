/**
 * Cœur "Arc Reactor / Quantum Core" 3D volumétrique en WebGL (Three.js).
 *
 * Reproduit fidèlement le modèle HUD 3D de la référence :
 * - Cœur central mécanique 3D (cylindre vannes + modules/cubes quantiques 3D en orbite)
 * - Anneaux concentriques superposés (Cyan #00e5ff et Ambre/Or #f5c518) à sens de rotation opposés
 * - Couronnes dentées segmentées, graduations radiale et arcs brisés
 * - Halo holographique et bloom haute précision
 */
import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import * as THREE from "three";

import { SKIN, type CockpitState } from "@/lib/cockpit-theme";
import { Satellites } from "./Satellites";

interface CoreProps {
  state?: CockpitState;
  /** Niveau audio 0..1, en ref pour animer sans re-render à 60 fps. */
  audioLevelRef?: React.MutableRefObject<number>;
  /** Modules périphériques (radar, jauges, spectre, molécules, globe). */
  satellites?: boolean;
  className?: string;
}

/** Bloc mécanique 3D central avec noyaux lumineux et cubes quantiques orbitaux */
function QuantumCore({ color, accent, speed }: { color: string; accent: string; speed: number }) {
  const coreRef = useRef<THREE.Group>(null);
  const cubeGroupRef = useRef<THREE.Group>(null);

  // 6 blocs/cubes méca 3D en orbite autour du réacteur central
  const modules = useMemo(() => {
    return [
      { pos: [0.34, 0.22, 0.15], rot: [0.4, 0.2, 0.1], scale: 0.14 },
      { pos: [-0.36, -0.18, 0.18], rot: [-0.2, 0.5, 0.3], scale: 0.13 },
      { pos: [-0.24, 0.34, -0.12], rot: [0.1, -0.4, 0.2], scale: 0.13 },
      { pos: [0.30, -0.28, -0.15], rot: [0.5, 0.1, -0.3], scale: 0.12 },
      { pos: [0.08, 0.42, 0.08], rot: [0.2, 0.3, 0.1], scale: 0.11 },
      { pos: [-0.08, -0.42, -0.08], rot: [-0.3, -0.1, 0.4], scale: 0.11 },
    ];
  }, []);

  useFrame((_, dt) => {
    if (coreRef.current) {
      coreRef.current.rotation.y += speed * dt * 1.2;
      coreRef.current.rotation.z += speed * dt * 0.5;
    }
    if (cubeGroupRef.current) {
      cubeGroupRef.current.rotation.y -= speed * dt * 0.9;
      cubeGroupRef.current.rotation.x += speed * dt * 0.4;
    }
  });

  return (
    <group ref={coreRef}>
      {/* Cylindre central métallique du réacteur */}
      <mesh>
        <cylinderGeometry args={[0.18, 0.18, 0.38, 16]} />
        <meshStandardMaterial color="#040c1a" roughness={0.2} metalness={0.9} wireframe toneMapped={false} />
      </mesh>
      {/* Cœur cylindrique d'énergie interne glowing */}
      <mesh>
        <cylinderGeometry args={[0.13, 0.13, 0.34, 16]} />
        <meshBasicMaterial color={color} transparent opacity={0.88} toneMapped={false} />
      </mesh>

      {/* Ensemble de cubes quantiques 3D en rotation */}
      <group ref={cubeGroupRef}>
        {modules.map((m, i) => (
          <group key={i} position={m.pos as [number, number, number]} rotation={m.rot as [number, number, number]}>
            {/* Structure du cube plein */}
            <mesh>
              <boxGeometry args={[m.scale, m.scale, m.scale]} />
              <meshStandardMaterial color="#061224" roughness={0.25} metalness={0.85} />
            </mesh>
            {/* Arêtes lumineuses glowing wireframe */}
            <lineSegments>
              <edgesGeometry args={[new THREE.BoxGeometry(m.scale * 1.04, m.scale * 1.04, m.scale * 1.04)]} />
              <lineBasicMaterial color={i % 2 === 0 ? color : accent} transparent opacity={0.95} toneMapped={false} />
            </lineSegments>
            {/* Cœur lumineux interne du cube */}
            <mesh>
              <boxGeometry args={[m.scale * 0.48, m.scale * 0.48, m.scale * 0.48]} />
              <meshBasicMaterial color={i % 2 === 0 ? color : accent} toneMapped={false} />
            </mesh>
          </group>
        ))}
      </group>
    </group>
  );
}

/** Couronne de petits blocs — la denture lumineuse du cadran */
function SegmentedRing({
  radius, count, color, speed, thickness = 0.05, height = 0.16, opacity = 1,
}: {
  radius: number; count: number; color: string; speed: number;
  thickness?: number; height?: number; opacity?: number;
}) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  useFrame((_, dt) => {
    const m = mesh.current;
    if (!m) return;
    m.rotation.z += speed * dt;
    for (let i = 0; i < count; i++) {
      const a = (i / count) * Math.PI * 2;
      dummy.position.set(Math.cos(a) * radius, Math.sin(a) * radius, 0);
      dummy.rotation.set(0, 0, a);
      dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
    }
    m.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, count]}>
      <boxGeometry args={[thickness, height, 0.02]} />
      <meshBasicMaterial color={color} transparent opacity={opacity} toneMapped={false} />
    </instancedMesh>
  );
}

/** Anneau plein ou arc partiel. `arc` en fraction de tour (1 = cercle entier) */
function ArcRing({
  radius, tube = 0.012, color, speed, arc = 1, offset = 0, opacity = 1,
}: {
  radius: number; tube?: number; color: string; speed: number;
  arc?: number; offset?: number; opacity?: number;
}) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.z += speed * dt;
  });
  return (
    <mesh ref={ref} rotation={[0, 0, offset]}>
      <torusGeometry args={[radius, tube, 8, 128, Math.PI * 2 * arc]} />
      <meshBasicMaterial color={color} transparent opacity={opacity} toneMapped={false} />
    </mesh>
  );
}

/** Traits radiaux fins (graduations du cadran) */
function TickRing({ radius, count, len, color, speed, opacity = 0.7 }: {
  radius: number; count: number; len: number; color: string;
  speed: number; opacity?: number;
}) {
  const group = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    if (group.current) group.current.rotation.z += speed * dt;
  });
  const ticks = useMemo(
    () => Array.from({ length: count }, (_, i) => (i / count) * Math.PI * 2),
    [count],
  );
  return (
    <group ref={group}>
      {ticks.map((a, i) => (
        <mesh key={i} position={[Math.cos(a) * radius, Math.sin(a) * radius, 0]} rotation={[0, 0, a]}>
          <boxGeometry args={[len, 0.012, 0.01]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={i % 5 === 0 ? opacity : opacity * 0.4}
            toneMapped={false}
          />
        </mesh>
      ))}
    </group>
  );
}

function Assembly({ state, audioLevelRef }: { state: CockpitState; audioLevelRef?: React.MutableRefObject<number> }) {
  const skin = SKIN[state];
  const root = useRef<THREE.Group>(null);
  const core = useRef<THREE.Group>(null);
  const halo = useRef<THREE.Mesh>(null);
  const t = useRef(0);

  useFrame((_, dt) => {
    t.current += dt;
    const level = audioLevelRef?.current ?? 0;
    const pulse = 1 + Math.sin(t.current * 1.6) * 0.035 + level * 0.28;
    if (core.current) core.current.scale.setScalar(pulse);
    if (halo.current) {
      halo.current.scale.setScalar(pulse * 1.9);
      (halo.current.material as THREE.MeshBasicMaterial).opacity = 0.1 + level * 0.22;
    }
    if (root.current) {
      // Inclinaison 3D caractéristique du cockpit (vue isométrique 3D)
      root.current.rotation.x = -0.36 + Math.cos(t.current * 0.28) * 0.04;
      root.current.rotation.y = Math.sin(t.current * 0.35) * 0.12;
    }
  });

  const s = skin.spin;
  const cyanColor = skin.key; // Cyan #00e5ff
  const amberColor = skin.accent; // Ambre/Or #f5c518

  return (
    <group ref={root}>
      {/* Halo de lueur diffuse arrière */}
      <mesh ref={halo} position={[0, 0, -0.9]}>
        <circleGeometry args={[0.55, 48]} />
        <meshBasicMaterial color={cyanColor} transparent opacity={0.12} toneMapped={false} />
      </mesh>

      {/* Puits central opaque */}
      <mesh position={[0, 0, -0.02]}>
        <circleGeometry args={[0.58, 48]} />
        <meshBasicMaterial color="#020509" toneMapped={false} />
      </mesh>

      {/* Cœur mécanique 3D central et cubes quantiques */}
      <group ref={core}>
        <QuantumCore color={cyanColor} accent={amberColor} speed={s * 1.5} />
      </group>

      {/* Anneaux intérieurs cyan et ambre */}
      <mesh>
        <torusGeometry args={[0.56, 0.016, 8, 96]} />
        <meshBasicMaterial color={cyanColor} toneMapped={false} />
      </mesh>

      {/* Anneau Ambre/Gold intermédiaire concentrique (focalisation visuelle) */}
      <ArcRing radius={0.82} color={amberColor} speed={s * 1.8} arc={0.75} tube={0.018} opacity={0.9} />
      <ArcRing radius={0.88} color={amberColor} speed={-s * 1.2} arc={0.45} tube={0.012} opacity={0.8} />

      {/* Couronnes segmentées cyan et ambre à vitesses opposées */}
      <SegmentedRing radius={0.68} count={48} color={cyanColor} speed={s * 2.2} height={0.1} />
      <SegmentedRing radius={1.02} count={36} color={amberColor} speed={-s * 1.4} height={0.17} opacity={0.9} />
      <SegmentedRing radius={1.55} count={72} color={cyanColor} speed={s * 0.8} thickness={0.03} height={0.08} opacity={0.7} />

      {/* Arcs brisés et détails HUD */}
      <ArcRing radius={1.22} color={cyanColor} speed={-s * 1.9} arc={0.28} offset={0.4} tube={0.022} />
      <ArcRing radius={1.22} color={amberColor} speed={-s * 1.9} arc={0.16} offset={3.1} tube={0.022} />
      <ArcRing radius={1.38} color={cyanColor} speed={s * 2.6} arc={0.4} tube={0.014} opacity={0.9} />
      <ArcRing radius={1.78} color={amberColor} speed={-s * 0.6} arc={1} tube={0.006} opacity={0.5} />
      <ArcRing radius={2.08} color={cyanColor} speed={s * 1.1} arc={0.12} tube={0.03} />

      {/* Graduations radiale HUD */}
      <TickRing radius={1.92} count={60} len={0.1} color={cyanColor} speed={-s * 0.35} />
      <TickRing radius={2.32} count={90} len={0.06} color={amberColor} speed={s * 0.22} opacity={0.45} />
    </group>
  );
}

function Orbit({ state, audioLevelRef }: {
  state: CockpitState; audioLevelRef?: React.MutableRefObject<number>;
}) {
  const skin = SKIN[state];
  return <Satellites color={skin.key} accent={skin.accent} levelRef={audioLevelRef} />;
}

export function ReactorCore({
  state = "idle", audioLevelRef, satellites = true, className,
}: CoreProps) {
  const skin = SKIN[state];
  return (
    <div className={className}>
      <Canvas
        camera={{ position: [0, 0, 7.2], fov: 46 }}
        gl={{ antialias: true, alpha: true }}
        dpr={[1, 2]}
      >
        <Assembly state={state} audioLevelRef={audioLevelRef} />
        {satellites && <Orbit state={state} audioLevelRef={audioLevelRef} />}
        <EffectComposer>
          <Bloom intensity={skin.glow} luminanceThreshold={0.15} luminanceSmoothing={0.6} mipmapBlur />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
