/**
 * Cœur "arc reactor" en WebGL — le centre volumétrique du cockpit d'Orion.
 *
 * Inspiré des références : anneaux concentriques à vitesses et sens opposés,
 * couronne segmentée, arcs brisés, halo diffus. Le bloom est appliqué ici et
 * NULLE PART ailleurs : le chrome du HUD est en SVG par-dessus, pour que le
 * texte et les traits restent nets. Du bloom sur du texte le rend illisible.
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

/** Couronne de petits blocs — la "denture" lumineuse des références. */
function SegmentedRing({
  radius, count, color, speed, thickness = 0.05, height = 0.16, opacity = 1,
}: {
  radius: number; count: number; color: string; speed: number;
  thickness?: number; height?: number; opacity?: number;
}) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  useMemo(() => {
    // Placement figé : seul le groupe tourne, pas chaque instance.
    if (!mesh.current) return;
  }, []);

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

/** Anneau plein ou arc partiel. `arc` en fraction de tour (1 = cercle entier). */
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

/** Traits radiaux fins, comme les graduations des cadrans de référence. */
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
    // Respiration lente + réaction au son. Le max évite que le cœur
    // disparaisse quand le micro est muet.
    const pulse = 1 + Math.sin(t.current * 1.6) * 0.035 + level * 0.28;
    if (core.current) core.current.scale.setScalar(pulse);
    if (halo.current) {
      halo.current.scale.setScalar(pulse * 1.9);
      (halo.current.material as THREE.MeshBasicMaterial).opacity = 0.1 + level * 0.22;
    }
    if (root.current) {
      // Léger balancement : donne le volume sans désorienter.
      root.current.rotation.y = Math.sin(t.current * 0.35) * 0.13;
      root.current.rotation.x = -0.22 + Math.cos(t.current * 0.28) * 0.05;
    }
  });

  const s = skin.spin;
  return (
    <group ref={root}>
      {/* Halo, repoussé loin derrière et resserré : large et proche, il remplissait
          tout l'intérieur d'un aplat et écrasait la structure du noyau. */}
      <mesh ref={halo} position={[0, 0, -0.9]}>
        <circleGeometry args={[0.5, 48]} />
        <meshBasicMaterial color={skin.key} transparent opacity={0.1} toneMapped={false} />
      </mesh>

      {/* Puits central opaque : c'est lui qui creuse le cœur en masquant le halo.
          Presque noir plutôt que transparent, sinon le halo transparaît. */}
      <mesh position={[0, 0, -0.02]}>
        <circleGeometry args={[0.58, 48]} />
        <meshBasicMaterial color="#020509" toneMapped={false} />
      </mesh>

      {/* Noyau évidé : une lèvre lumineuse et quatre anneaux internes fins. */}
      <group ref={core}>
        <mesh>
          <torusGeometry args={[0.56, 0.016, 8, 96]} />
          <meshBasicMaterial color={skin.key} toneMapped={false} />
        </mesh>
        {[0.19, 0.28, 0.38, 0.47].map((r, i) => (
          <mesh key={r}>
            <torusGeometry args={[r, 0.0045, 6, 72]} />
            <meshBasicMaterial
              color={i === 1 ? skin.accent : skin.key}
              transparent
              opacity={0.28 + i * 0.14}
              toneMapped={false}
            />
          </mesh>
        ))}
        {/* Point de mire : sans lui le centre paraît creux au sens de « vide ». */}
        <mesh>
          <circleGeometry args={[0.055, 24]} />
          <meshBasicMaterial color={skin.key} toneMapped={false} />
        </mesh>
      </group>

      {/* Couronnes segmentées, sens opposés */}
      <SegmentedRing radius={0.62} count={48} color={skin.key} speed={s * 2.2} height={0.1} />
      <SegmentedRing radius={0.95} count={36} color={skin.key} speed={-s * 1.4} height={0.17} opacity={0.85} />
      <SegmentedRing radius={1.6} count={72} color={skin.accent} speed={s * 0.8} thickness={0.03} height={0.08} opacity={0.6} />

      {/* Arcs brisés : le détail qui fait "machine" plutôt que "cercle" */}
      <ArcRing radius={1.2} color={skin.key} speed={-s * 1.9} arc={0.28} offset={0.4} tube={0.022} />
      <ArcRing radius={1.2} color={skin.key} speed={-s * 1.9} arc={0.16} offset={3.1} tube={0.022} />
      <ArcRing radius={1.33} color={skin.accent} speed={s * 2.6} arc={0.4} tube={0.014} opacity={0.9} />
      <ArcRing radius={1.75} color={skin.key} speed={-s * 0.6} arc={1} tube={0.006} opacity={0.45} />
      <ArcRing radius={2.05} color={skin.accent} speed={s * 1.1} arc={0.12} tube={0.03} />

      <TickRing radius={1.9} count={60} len={0.1} color={skin.key} speed={-s * 0.35} />
      <TickRing radius={2.3} count={90} len={0.06} color={skin.key} speed={s * 0.22} opacity={0.4} />
    </group>
  );
}

/** Satellites sortis du groupe principal : ils ne doivent PAS suivre le
 *  balancement du cœur, sinon tout bouge d'un bloc et la profondeur disparaît. */
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
          {/* mipmapBlur donne un halo large et doux plutôt qu'un contour dur. */}
          <Bloom intensity={skin.glow} luminanceThreshold={0.15} luminanceSmoothing={0.6} mipmapBlur />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
