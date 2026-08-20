import { useEffect, useState } from "react";
import { VoiceUI } from "./pages/VoiceUI";
import { OrionUI } from "./pages/OrionUI";
import { TradingUI } from "./pages/TradingUI";
import { CockpitUI } from "./pages/CockpitUI";
import { CapsuleUI } from "./pages/CapsuleUI";

type Route = "orion" | "voice" | "trading" | "cockpit" | "capsule";

/**
 * En production la coque Electron charge un fichier local et passe la route
 * dans le hash : `index.html#/cockpit`. Le chemin vaut alors toujours
 * `/index.html`, d'où la lecture du hash en priorité.
 *
 * La racine mène au cockpit. L'ancienne interface de chat texte, avec sa grille
 * de mot de passe, reste accessible sur `/chat` — elle n'est plus le point
 * d'entrée par défaut.
 */
function routeCourante(): Route {
  if (typeof window === "undefined") return "cockpit";
  const brut = window.location.hash.replace(/^#/, "") || window.location.pathname;
  if (brut.startsWith("/voice")) return "voice";
  if (brut.startsWith("/trading")) return "trading";
  if (brut.startsWith("/capsule")) return "capsule";
  if (brut.startsWith("/chat") || brut.startsWith("/orion")) return "orion";
  return "cockpit";
}

export default function App() {
  const [route, setRoute] = useState<Route>(routeCourante);

  useEffect(() => {
    const relire = () => setRoute(routeCourante());
    window.addEventListener("popstate", relire);
    window.addEventListener("hashchange", relire);
    return () => {
      window.removeEventListener("popstate", relire);
      window.removeEventListener("hashchange", relire);
    };
  }, []);

  switch (route) {
    case "voice":   return <VoiceUI />;
    case "trading": return <TradingUI />;
    case "orion":   return <OrionUI />;
    case "capsule": return <CapsuleUI />;
    default:        return <CockpitUI />;
  }
}
