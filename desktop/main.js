/**
 * Processus principal de la coque de bureau d'Orion.
 *
 * Deux fenêtres :
 *   - cockpit : sans bordure, transparente, l'interface complète
 *   - capsule : petit réacteur toujours au-dessus, dans un coin, invoqué au
 *     raccourci clavier ; c'est la présence permanente d'Orion sur le bureau
 *
 * Les capacités natives (capture, énumération des fenêtres, presse-papier)
 * vivent ICI et non dans le rendu : desktopCapturer n'est pas accessible depuis
 * un renderer, et on veut garder `contextIsolation` actif.
 */
const {
  app, BrowserWindow, ipcMain, globalShortcut, desktopCapturer,
  clipboard, screen, shell, nativeImage,
} = require("electron");
const path = require("node:path");

const DEV_URL = process.env.ORION_DEV_URL || null;
const PRELOAD = path.join(__dirname, "preload.js");

let cockpit = null;
let capsule = null;

/** Charge une route de l'interface, depuis le serveur Vite en dev ou les
 *  fichiers empaquetés en production. */
function chargerUI(win, route) {
  if (DEV_URL) return win.loadURL(`${DEV_URL}${route}`);
  return win.loadFile(path.join(process.resourcesPath, "ui", "index.html"), {
    hash: route,
  });
}

function creerCockpit() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  cockpit = new BrowserWindow({
    width: Math.min(1600, Math.round(width * 0.86)),
    height: Math.min(1000, Math.round(height * 0.88)),
    minWidth: 1100,
    minHeight: 680,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    // Le fond du cockpit est déjà sombre ; sans cette couleur de base, un
    // rendu transparent laisse voir le bureau pendant le premier paint.
    webPreferences: {
      preload: PRELOAD,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  chargerUI(cockpit, "/cockpit");
  cockpit.once("ready-to-show", () => cockpit.show());
  cockpit.on("closed", () => { cockpit = null; });

  // Les liens externes partent dans le navigateur : sinon ils remplacent le
  // cockpit dans sa propre fenêtre, sans barre d'adresse pour revenir.
  cockpit.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

function creerCapsule() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  const T = 190;
  capsule = new BrowserWindow({
    width: T,
    height: T,
    x: width - T - 24,
    y: height - T - 24,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    focusable: false,
    show: false,
    webPreferences: {
      preload: PRELOAD,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  // "screen-saver" passe au-dessus des applications en plein écran, ce que le
  // niveau par défaut ne fait pas.
  capsule.setAlwaysOnTop(true, "screen-saver");
  capsule.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  chargerUI(capsule, "/capsule");
  // showInactive et non show : la capsule ne doit jamais voler le focus à ce
  // que fait l'utilisateur. Sans cet appel elle resterait invisible, `show`
  // étant à false pour éviter un cadre blanc pendant le premier rendu.
  capsule.once("ready-to-show", () => capsule.showInactive());
  capsule.on("closed", () => { capsule = null; });
}

/* ───────────────────────── Capacités natives ───────────────────────── */

ipcMain.handle("orion:capture-ecran", async (_e, { maxWidth = 1600 } = {}) => {
  const displays = screen.getAllDisplays();
  const sources = await desktopCapturer.getSources({
    types: ["screen"],
    thumbnailSize: { width: maxWidth, height: Math.round(maxWidth * 0.62) },
  });
  return sources.map((s, i) => ({
    id: s.id,
    nom: s.name,
    apercu: s.thumbnail.toDataURL(),
    taille: displays[i]
      ? { largeur: displays[i].size.width, hauteur: displays[i].size.height }
      : null,
  }));
});

ipcMain.handle("orion:lister-fenetres", async (_e, { vignette = 320 } = {}) => {
  const sources = await desktopCapturer.getSources({
    types: ["window"],
    thumbnailSize: { width: vignette, height: Math.round(vignette * 0.62) },
  });
  return sources
    // Les fenêtres sans titre sont des surfaces techniques : elles polluent
    // la liste sans rien apporter.
    .filter((s) => s.name && s.name.trim() && s.name !== "Orion")
    .map((s) => ({
      id: s.id,
      titre: s.name,
      apercu: s.thumbnail.isEmpty() ? null : s.thumbnail.toDataURL(),
    }));
});

ipcMain.handle("orion:presse-papier-lire", () => clipboard.readText());
ipcMain.handle("orion:presse-papier-ecrire", (_e, texte) => {
  clipboard.writeText(String(texte ?? ""));
  return true;
});

ipcMain.handle("orion:fenetre", (e, action) => {
  const win = BrowserWindow.fromWebContents(e.sender);
  if (!win) return false;
  switch (action) {
    case "reduire":   win.minimize(); break;
    case "agrandir":  win.isMaximized() ? win.unmaximize() : win.maximize(); break;
    case "fermer":    win.close(); break;
    case "epingler":  win.setAlwaysOnTop(!win.isAlwaysOnTop(), "screen-saver"); break;
    default: return false;
  }
  return true;
});

ipcMain.handle("orion:capsule", (_e, action) => {
  if (!capsule) return false;
  if (action === "montrer") capsule.showInactive();
  else if (action === "cacher") capsule.hide();
  else capsule.isVisible() ? capsule.hide() : capsule.showInactive();
  return capsule.isVisible();
});

ipcMain.handle("orion:cockpit", (_e, action) => {
  if (!cockpit) return false;
  if (action === "montrer") { cockpit.show(); cockpit.focus(); }
  else if (action === "cacher") cockpit.hide();
  else cockpit.isVisible() ? cockpit.hide() : (cockpit.show(), cockpit.focus());
  return cockpit.isVisible();
});

ipcMain.handle("orion:infos", () => ({
  plateforme: process.platform,
  versionElectron: process.versions.electron,
  dev: Boolean(DEV_URL),
}));

/* ──────────────────────────── Cycle de vie ─────────────────────────── */

app.whenReady().then(() => {
  creerCockpit();
  creerCapsule();

  // Raccourci global : rappeler ou masquer le cockpit sans quitter ce qu'on fait.
  const ok = globalShortcut.register("Control+Alt+O", () => {
    if (!cockpit) return creerCockpit();
    cockpit.isVisible() ? cockpit.hide() : (cockpit.show(), cockpit.focus());
  });
  if (!ok) console.warn("[orion] raccourci Ctrl+Alt+O indisponible (déjà pris ?)");

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) creerCockpit();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("will-quit", () => globalShortcut.unregisterAll());
