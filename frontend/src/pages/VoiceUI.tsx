import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Header } from "@/components/Header";
import { Sphere, type SphereState } from "@/components/Sphere";
import { DecorativeRings } from "@/components/Rings";
import { SystemHud, NetworkHud, FreqHud, ShapeHud } from "@/components/HudReadout";
import { EnergyBars } from "@/components/EnergyBars";
import { MicButton } from "@/components/MicButton";
import { ConfirmModal, type ConfirmRequest } from "@/components/ConfirmModal";
import { ToastHost, useToasts } from "@/components/Toast";
import { SettingsPanel } from "@/components/SettingsPanel";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useMicRecorder } from "@/hooks/useMicRecorder";
import { useTTSStream } from "@/hooks/useTTSStream";
import { storage, wsToHttp } from "@/lib/utils";
import {
  completerDepuisBureau, ecrireDeviceId, ecrireServerUrl, ecrireToken,
  lireDeviceId, lireServerUrl, lireToken,
} from "@/lib/credentials";
import type { EmbeddedViewProps } from "@/components/cockpit/embed";
import { OrionResponseBox } from "@/components/cockpit/OrionResponseBox";

const STATE_LABELS: Record<SphereState, string> = {
  idle: "STANDBY",
  listening: "ÉCOUTE",
  processing: "TRAITEMENT",
  speaking: "PARLE",
};

export function VoiceUI({ embedded, onStateChange, onModeChange,
                         audioLevelRef: hostAudioRef }: EmbeddedViewProps = {}) {
  // ─── Config (persistée) ───
  const [serverUrl, setServerUrl] = useState(lireServerUrl);
  const [token, setToken] = useState(lireToken);
  const [deviceId, setDeviceId] = useState(() => lireDeviceId("voice-browser"));
  const [settingsOpen, setSettingsOpen] = useState(false);
  useEffect(() => ecrireServerUrl(serverUrl), [serverUrl]);
  useEffect(() => ecrireToken(token), [token]);
  useEffect(() => ecrireDeviceId(deviceId), [deviceId]);

  // ─── État UI ───
  const [state, setState] = useState<SphereState>("idle");
  useEffect(() => { onStateChange?.(state); }, [state, onStateChange]);
  const [orionText, setOrionText] = useState(embedded ? "Parle, je t'écoute." : "Appuie sur le micro pour parler.");
  const [userText, setUserText] = useState("");
  const [toolHint, setToolHint] = useState("");
  const [shapeLabel, setShapeLabel] = useState("SPHÈRE");
  const [confirmReq, setConfirmReq] = useState<ConfirmRequest | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [enabled, setEnabled] = useState(!!token);

  // La coque de bureau lit le .env : on complète ce qui manque puis on se
  // connecte seul. Sans ça il fallait ressaisir le token à chaque lancement.
  useEffect(() => {
    let vivant = true;
    (async () => {
      await completerDepuisBureau();
      if (!vivant) return;
      const t = lireToken();
      if (t) {
        setToken(t);
        setServerUrl(lireServerUrl());
        setEnabled(true);
      } else if (!embedded) {
        // Hors cockpit, sans token, la saisie manuelle reste la seule voie.
        setSettingsOpen(true);
      }
    })();
    return () => { vivant = false; };
  }, [embedded]);

  const { toasts, push: toast, dismiss } = useToasts();
  const autoResumeTimeoutRef = useRef<number | null>(null);
  const micStartRef = useRef<(() => Promise<void>) | null>(null);

  const handleTTSFinished = useCallback(() => {
    if (autoResumeTimeoutRef.current) window.clearTimeout(autoResumeTimeoutRef.current);
    autoResumeTimeoutRef.current = window.setTimeout(() => {
      window.speechSynthesis?.cancel();
      setUserText("");
      setToolHint("");
      setOrionText("Je t'écoute.");
      setState("listening");
      void micStartRef.current?.();
    }, 400);
  }, []);

  const tts = useTTSStream(handleTTSFinished);

  // Audio level via ref (la sphère lit en boucle, pas de re-render)
  const localAudioRef = useRef(0);
  // Fournie par la coque dans le cockpit, locale sinon (alimente la Sphere).
  const audioLevelRef = hostAudioRef ?? localAudioRef;
  const [voicePct, setVoicePct] = useState(0);

  // ─── WebSocket ───
  const wsUrl = useMemo(() => {
    if (!enabled || !token) return "";
    return `${serverUrl}/ws/${encodeURIComponent(deviceId)}?token=${encodeURIComponent(token)}`;
  }, [enabled, serverUrl, deviceId, token]);

  // ─── Streaming TTS phrase-par-phrase ───
  const streamHadFirstChunkRef = useRef(false);
  const handleResponseChunk = useCallback((text: string) => {
    if (!text) return;
    if (!streamHadFirstChunkRef.current) {
      streamHadFirstChunkRef.current = true;
      setState("speaking");
      setToolHint("");
    }
    setOrionText(prev => prev + text);
    tts.appendChunk(text);
  }, [tts]);

  const handleResponseFinal = useCallback((fullContent: string) => {
    if (!streamHadFirstChunkRef.current && fullContent) {
      setState("speaking");
      setOrionText(fullContent);
      tts.appendChunk(fullContent);
    }
    tts.flush(fullContent);
    if (fullContent) setOrionText(fullContent);
    streamHadFirstChunkRef.current = false;
    window.setTimeout(() => setState(s => (s === "speaking" ? "idle" : s)), 500);
  }, [tts]);

  const onWSMessage = useCallback((data: any) => {
    if (data.type === "connected") return;
    if (data.type === "tool_action") {
      const ok = data.result?.success !== false ? "✓" : "✗";
      setToolHint(`${ok} ${data.tool}`);
      // Orion pilote l'affichage : il bascule le cockpit sur le mode qui
      // correspond à ce qu'il s'apprête à faire. On passe par le message
      // tool_action déjà émis pour chaque outil, sans canal supplémentaire.
      if (data.tool === "cockpit_set_mode" && data.result?.success && data.result?.mode) {
        onModeChange?.(String(data.result.mode));
      }
    } else if (data.type === "response_chunk") {
      handleResponseChunk(data.text || "");
    } else if (data.type === "response") {
      handleResponseFinal(data.content || "");
    } else if (data.type === "error") {
      setState("idle");
      setOrionText("Erreur : " + (data.content || "inconnue"));
      toast(data.content || "erreur", true);
    } else if (data.type === "info") {
      toast(data.message || "");
    } else if (data.type === "confirm_request") {
      setConfirmError(null);
      setConfirmReq(data);
    } else if (data.type === "confirm_result") {
      if (data.accepted) {
        setConfirmReq(null);
        setConfirmError(null);
        toast("Action autorisée.");
      } else {
        setConfirmError(data.error || "Mot de passe incorrect.");
      }
    } else if (data.type === "audit_alert") {
      const ok = data.success ? "✓" : "✗";
      const conf = data.confirmed ? " [conf]" : "";
      toast(`${ok}${conf} ${data.tool_name} · ${data.device_id || "?"}`, !data.success);
    }
  }, [handleResponseChunk, handleResponseFinal, toast, onModeChange]);

  const ws = useWebSocket({ url: wsUrl, onMessage: onWSMessage, enabled });
  const isConnected = ws.status === "open";

  // ─── Micro / transcription ───
  const mic = useMicRecorder({
    onAudioLevel: (lvl) => {
      audioLevelRef.current = lvl;
      setVoicePct(Math.round(lvl * 100));
    },
  });
  micStartRef.current = mic.start;

  // Quand on a un nouveau blob → upload
  useEffect(() => {
    if (!mic.lastBlob) return;
    const blob = mic.lastBlob;
    if (blob.size < 500) {
      toast("Trop court ou silence.", true);
      setState("idle");
      return;
    }
    void uploadAudio(blob);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mic.lastBlob]);

  // Erreurs micro
  useEffect(() => {
    if (mic.lastError) {
      toast(mic.lastError, true);
    }
  }, [mic.lastError, toast]);

  const uploadAudio = useCallback(async (blob: Blob) => {
    setState("processing");
    setOrionText("Transcription…");
    const url = `${wsToHttp(serverUrl)}/api/transcribe?token=${encodeURIComponent(token)}&language=fr`;
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": blob.type || "audio/webm" },
        body: blob,
      });
      if (!resp.ok) {
        toast("HTTP " + resp.status, true);
        setState("idle"); setOrionText("Erreur transcription.");
        return;
      }
      const data = await resp.json();
      if (!data.success || !data.text?.trim()) {
        toast(data.error || "Je n'ai rien compris.", true);
        setState("idle"); setOrionText("Je n'ai rien compris.");
        return;
      }
      const text = data.text.trim();
      setUserText(text);
      // Reset stream + envoie au serveur
      tts.reset();
      streamHadFirstChunkRef.current = false;
      setOrionText("Réflexion…");
      const sent = ws.send({ type: "message", content: text });
      if (sent) setState("processing");
      else { toast("Pas connecté.", true); setState("idle"); }
    } catch (err) {
      toast("Échec : " + (err as Error).message, true);
      setState("idle"); setOrionText("Erreur réseau.");
    }
  }, [serverUrl, token, tts, ws, toast]);

  const toggleMic = useCallback(() => {
    if (!isConnected) {
      toast("Pas connecté au serveur.", true);
      return;
    }
    if (mic.isRecording) mic.stop();
    else {
      window.speechSynthesis?.cancel();
      setUserText("");
      setToolHint("");
      setOrionText("Je t'écoute.");
      setState("listening");
      void mic.start();
    }
  }, [isConnected, mic, toast]);

  // Confirm modal handlers
  const onApprove = useCallback((pwd: string) => {
    if (!confirmReq) return;
    ws.send({ type: "confirm_response", request_id: confirmReq.request_id, password: pwd });
  }, [confirmReq, ws]);
  const onDeny = useCallback(() => {
    if (!confirmReq) return;
    ws.send({ type: "confirm_response", request_id: confirmReq.request_id, refused: true });
    setConfirmReq(null);
    setConfirmError(null);
  }, [confirmReq, ws]);

  // Raccourcis : Espace = parler / Échap = stop
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target?.tagName === "INPUT") return;
      if (e.code === "Space") { e.preventDefault(); toggleMic(); }
      if (e.code === "Escape" && mic.isRecording) { e.preventDefault(); mic.stop(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggleMic, mic]);

  // Dans le cockpit il n'y a plus de bouton micro : on ouvre l'écoute dès que
  // la connexion est établie. Le navigateur exige un geste utilisateur pour la
  // PREMIÈRE autorisation du micro ; une fois accordée, elle est mémorisée pour
  // l'origine et les démarrages suivants sont automatiques.
  const ecouteAmorcee = useRef(false);
  useEffect(() => {
    if (!embedded || !isConnected || ecouteAmorcee.current) return;
    if (mic.isRecording) return;
    ecouteAmorcee.current = true;
    const t = window.setTimeout(() => toggleMic(), 400);
    return () => window.clearTimeout(t);
  }, [embedded, isConnected, mic.isRecording, toggleMic]);

  // Hint micro
  const micHint = state === "listening"
    ? "J'écoute…"
    : state === "processing"
    ? "Réflexion…"
    : state === "speaking"
    ? "Je réponds…"
    : "Espace pour parler · Échap pour stop";

  // Couleur état
  const stateColor =
    state === "listening"  ? "text-red"
    : state === "processing" ? "text-gold"
    : state === "speaking"  ? "text-green"
    :                          "text-cyan";

  return (
    <div className={embedded ? "flex h-full flex-col" : "h-screen flex flex-col"}>
      {!embedded && <Header
        connected={isConnected}
        onOpenSettings={() => setSettingsOpen(s => !s)}
      />}

      {!embedded && <>
        <SystemHud  position="top-left" />
        <NetworkHud position="top-right" />
        <FreqHud    position="bot-left" rotation={0} />
        <ShapeHud   position="bot-right" label={shapeLabel} />
      </>}

      <main className={embedded
        ? "relative z-[5] flex flex-col items-center px-5"
        : "relative z-[5] flex-1 flex flex-col items-center justify-center px-5"}>
        {!embedded && <DecorativeRings />}

        {!embedded && <Sphere
          state={state}
          audioLevelRef={audioLevelRef}
          onShapeChange={(name) => {
            // Mappe shape name → label déjà capitalisé
            const labels: Record<string, string> = {
              sphere: "SPHÈRE", star: "ÉTOILE", cube: "CUBE",
              arcreactor: "ARC REACTOR", atom: "ATOME", hub: "HUB NEURONAL",
              tore: "TORE", face: "VISAGE IA", letterO: "LETTRE O", orion: "ORION",
            };
            setShapeLabel(labels[name] ?? name.toUpperCase());
          }}
        />}

        {!embedded && <div className="relative z-[4] flex flex-col items-center gap-1.5 -mt-10">
          <div className="font-orbitron text-[9px] tracking-[4px] text-text-dim uppercase">
            Réseau neuronal IA
          </div>
          <div className={`font-orbitron text-sm tracking-[6px] uppercase h-5
                          transition-colors ${stateColor}`}>
            {STATE_LABELS[state]}
          </div>
        </div>}

        <div className="relative z-[10] mt-4 w-full max-w-[680px]">
          <OrionResponseBox
            orionText={orionText}
            userText={userText}
            toolHint={toolHint}
            state={state}
            onClose={() => {
              setUserText("");
              setToolHint("");
              setOrionText("Parle, je t'écoute.");
            }}
          />
        </div>

      </main>

      {!embedded && <MicButton
        isListening={mic.isRecording}
        onClick={toggleMic}
        hint={micHint}
        inline={embedded}
      />}

      {!embedded && <EnergyBars voiceLevel={voicePct / 100} />}

      <ToastHost toasts={toasts} onDismiss={dismiss} />

      <ConfirmModal
        request={confirmReq}
        error={confirmError}
        onApprove={onApprove}
        onDeny={onDeny}
      />

      {!embedded && <SettingsPanel
        open={settingsOpen}
        serverUrl={serverUrl} setServerUrl={setServerUrl}
        token={token} setToken={setToken}
        deviceId={deviceId} setDeviceId={setDeviceId}
        onConnect={() => { setEnabled(true); setSettingsOpen(false); }}
        onDisconnect={() => { setEnabled(false); ws.close(); }}
      />}
    </div>
  );
}
