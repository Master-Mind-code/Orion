/**
 * Pont entre le rendu et les capacités natives.
 *
 * `contextIsolation` reste actif : on n'expose PAS Node au rendu, seulement
 * cette surface nommée et fermée. L'interface web doit continuer de
 * fonctionner sans elle — d'où le test `window.orionDesktop` côté React,
 * qui fait basculer le mode Bureau en dégradé dans un simple navigateur.
 */
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("orionDesktop", {
  disponible: true,

  /** Capture de chaque écran, en data URL. */
  captureEcran: (opts) => ipcRenderer.invoke("orion:capture-ecran", opts),

  /** Fenêtres ouvertes, avec vignette. */
  listerFenetres: (opts) => ipcRenderer.invoke("orion:lister-fenetres", opts),

  pressePapier: {
    lire: () => ipcRenderer.invoke("orion:presse-papier-lire"),
    ecrire: (texte) => ipcRenderer.invoke("orion:presse-papier-ecrire", texte),
  },

  /** Agit sur la fenêtre qui appelle : reduire | agrandir | fermer | epingler. */
  fenetre: (action) => ipcRenderer.invoke("orion:fenetre", action),

  /** montrer | cacher | basculer */
  capsule: (action = "basculer") => ipcRenderer.invoke("orion:capsule", action),
  cockpit: (action = "basculer") => ipcRenderer.invoke("orion:cockpit", action),

  infos: () => ipcRenderer.invoke("orion:infos"),
});
