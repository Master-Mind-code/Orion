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

/** Page de secours : sans elle, un serveur Vite absent donne une fenêtre noire
 *  et une erreur uniquement dans la console, illisible pour qui lance l'app. */
function pageErreur(message) {
  const html = `<!doctype html><meta charset="utf-8">
<style>
  html,body{height:100%;margin:0;background:#04060d;color:#b8d8f0;
    font:14px/1.6 "Segoe UI",system-ui,sans-serif;display:grid;place-items:center}
  .b{max-width:560px;padding:32px;border:1px solid rgba(0,229,255,.18);border-radius:16px;
    background:linear-gradient(160deg,rgba(8,18,38,.9),rgba(4,8,18,.9))}
  h1{margin:0 0 12px;font-size:15px;letter-spacing:.28em;color:#00e5ff;text-transform:uppercase}
  code{display:block;margin-top:14px;padding:10px 12px;border-radius:8px;
    background:rgba(0,0,0,.45);color:#7ee787;font-family:Consolas,monospace;font-size:13px}
  p{margin:8px 0;color:rgba(150,195,225,.8)}
</style>
<div class="b"><h1>Orion — interface injoignable</h1>
<p>${message}</p>
<p>Lance le serveur d'interface dans un autre terminal :</p>
<code>npm --prefix frontend run dev</code>
<p>Puis relance cette fenêtre. Le script <code>npm --prefix desktop run dev</code>
   démarre normalement les deux ensemble.</p></div>`;
  return `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;
}

/** Attend que le serveur de développement réponde.
 *
 *  Vite met une seconde ou deux à se lever ; sans cette attente, la coque
 *  lancée en parallèle tombe systématiquement sur ERR_CONNECTION_REFUSED. */
async function attendreServeur(url, essais = 60, delaiMs = 500) {
  for (let i = 0; i < essais; i++) {
    try {
      const r = await fetch(url, { method: "GET" });
      if (r.ok || r.status === 404) return true;
    } catch {
      /* pas encore levé */
    }
    await new Promise((r) => setTimeout(r, delaiMs));
  }
  return false;
}

/** Charge une route de l'interface, depuis le serveur Vite en dev ou les
 *  fichiers empaquetés en production. */
async function chargerUI(win, route) {
  if (!DEV_URL) {
    return win.loadFile(path.join(process.resourcesPath, "ui", "index.html"), {
      hash: route,
    });
  }
  try {
    await win.loadURL(`${DEV_URL}${route}`);
  } catch {
    if (!win.isDestroyed()) {
      await win.loadURL(pageErreur(`Aucune réponse sur ${DEV_URL}.`));
    }
  }
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

app.whenReady().then(async () => {
  // On attend le serveur d'interface AVANT de créer les fenêtres : sinon elles
  // s'ouvrent sur une page d'erreur et il faut les recharger à la main.
  if (DEV_URL) {
    const pret = await attendreServeur(DEV_URL);
    if (!pret) console.warn(`[orion] ${DEV_URL} ne répond pas — page de secours.`);
  }

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
