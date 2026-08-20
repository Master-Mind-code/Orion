/**
 * Contrat entre le cockpit et les vues existantes.
 *
 * Les trois vues (OrionUI, VoiceUI, TradingUI) restent utilisables telles quelles
 * sur leur route dédiée. Montées dans le cockpit, elles passent en mode
 * `embedded` : elles abandonnent leur propre en-tête, leur fond et leurs décors,
 * que la coque fournit déjà, et ne gardent que leur contenu fonctionnel.
 *
 * Elles remontent aussi leur état, pour que le réacteur reflète ce que fait
 * réellement Orion plutôt qu'une animation décorative.
 */
import type { MutableRefObject } from "react";

import type { CockpitState } from "@/lib/cockpit-theme";

export interface EmbeddedViewProps {
  /** Rendu sans chrome, destiné à la zone de contenu du cockpit. */
  embedded?: boolean;
  /** Remonte l'état courant (écoute, traitement, parole...) vers la coque. */
  onStateChange?: (state: CockpitState) => void;
  /** Ref de niveau audio fournie par la coque, pour animer le réacteur. */
  audioLevelRef?: MutableRefObject<number>;
  /** Orion demande lui-même l'affichage d'un autre mode. */
  onModeChange?: (mode: string) => void;
}
