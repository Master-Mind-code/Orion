/**
 * Boîte de réponse holographique d'Orion pour le Cockpit.
 *
 * S'affiche proprement dans un conteneur en verre blindé (Glassmorphism)
 * lorsque Orion traite ou réponds à une requête, évitant que le texte ne se
 * superpose de manière désordonnée sous le réacteur.
 */
import React, { useState } from "react";
import { X, Copy, Check, Sparkles, Terminal } from "lucide-react";
import { CK } from "@/lib/cockpit-theme";

interface OrionResponseBoxProps {
  orionText: string;
  userText?: string;
  toolHint?: string;
  state: "idle" | "listening" | "processing" | "speaking";
  onClose?: () => void;
}

/** Formate le texte brut/markdown pour un affichage propre (bolds, listes, retours ligne) */
function FormattedText({ content }: { content: string }) {
  if (!content) return null;

  // Split par lignes pour préserver les paragraphes et listes
  const lines = content.split("\n");

  return (
    <div className="space-y-1.5 text-left text-sm leading-relaxed text-slate-100 font-sans">
      {lines.map((line, idx) => {
        if (!line.trim()) return <div key={idx} className="h-2" />;


        // Formatage gras basique **mot** -> <strong>
        const parts = line.split(/(\*\*.*?\*\*)/g);
        const formattedLine = parts.map((part, pIdx) => {
          if (part.startsWith("**") && part.endsWith("**")) {
            return (
              <strong key={pIdx} className="font-semibold text-cyan-300">
                {part.slice(2, -2)}
              </strong>
            );
          }
          return part;
        });

        // Détection de puces
        if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-2 text-slate-200">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400" />
              <span>{formattedLine}</span>
            </div>
          );
        }

        return <p key={idx}>{formattedLine}</p>;
      })}
    </div>
  );
}

export function OrionResponseBox({
  orionText,
  userText,
  toolHint,
  state,
  onClose,
}: OrionResponseBoxProps) {
  const [copied, setCopied] = useState(false);

  const isDefaultStatus =
    orionText === "Parle, je t'écoute." ||
    orionText === "Appuie sur le micro pour parler." ||
    orionText === "Je t'écoute.";

  // Ne pas afficher la grande boîte si c'est juste le statut d'attente initial sans réponse ni question
  const shouldShowBox = !isDefaultStatus || Boolean(userText) || state === "processing" || state === "speaking";

  if (!shouldShowBox) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-full border border-cyan-500/20 bg-slate-900/60 px-4 py-1.5 backdrop-blur-md">
        <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400" />
        <span className="font-tech text-xs tracking-wider text-cyan-200/80">
          {orionText}
        </span>
      </div>
    );
  }

  const handleCopy = () => {
    if (orionText) {
      navigator.clipboard.writeText(orionText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const stateColor =
    state === "listening"
      ? CK.crimson
      : state === "processing"
      ? CK.amber
      : state === "speaking"
      ? CK.green
      : CK.cyan;

  const stateLabel =
    state === "listening"
      ? "ÉCOUTE EN COURS"
      : state === "processing"
      ? "ANALYSE & RÉFLEXION"
      : state === "speaking"
      ? "TRANSMISSION ORION"
      : "RÉPONSE IA";

  return (
    <div
      className="relative w-full max-w-xl mx-auto overflow-hidden rounded-2xl border border-cyan-500/30 bg-slate-950/85 p-4 shadow-2xl backdrop-blur-xl transition-all duration-300 animate-in fade-in slide-in-from-bottom-4"
      style={{
        boxShadow: "0 0 30px rgba(0, 229, 255, 0.12), inset 0 0 15px rgba(0, 229, 255, 0.05)",
      }}
    >
      {/* Barre supérieure du HUD */}
      <div className="mb-3 flex items-center justify-between border-b border-white/10 pb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-cyan-400 animate-pulse" />
          <span className="font-tech text-[10px] uppercase tracking-[0.2em]" style={{ color: stateColor }}>
            {stateLabel}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleCopy}
            title="Copier le texte"
            className="rounded-md p-1 text-slate-400 transition hover:bg-white/10 hover:text-white"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              title="Fermer la réponse"
              className="rounded-md p-1 text-slate-400 transition hover:bg-red-500/20 hover:text-red-300"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Question utilisateur (si présente) */}
      {userText && (
        <div className="mb-3 rounded-lg border border-cyan-500/20 bg-cyan-950/30 px-3 py-2 text-left">
          <span className="font-tech text-[9px] uppercase tracking-wider text-cyan-400">Demande :</span>
          <p className="font-space text-xs italic text-slate-200">« {userText} »</p>
        </div>
      )}

      {/* Indication d'outil actif */}
      {toolHint && (
        <div className="mb-2 flex items-center gap-1.5 rounded border border-amber-500/30 bg-amber-950/20 px-2.5 py-1 text-[10px] font-mono text-amber-300">
          <Terminal className="h-3 w-3" />
          <span>{toolHint}</span>
        </div>
      )}

      {/* Corps du texte de réponse avec défilement propre */}
      <div className="max-h-[260px] overflow-y-auto pr-1 text-left custom-scrollbar">
        <FormattedText content={orionText} />
      </div>

      {/* Petite ligne de bas de carte */}
      <div className="mt-3 flex items-center justify-between border-t border-white/5 pt-2 font-tech text-[9px] text-slate-500">
        <span>ORION COCKPIT V2.5</span>
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: stateColor }} />
          <span className="uppercase">{state}</span>
        </div>
      </div>
    </div>
  );
}
