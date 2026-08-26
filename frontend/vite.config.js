import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
export default defineConfig(function (_a) {
    var command = _a.command;
    return ({
        // En prod (build), tout est servi sous /voice/ par FastAPI → préfixe les paths.
        // En dev (npm run dev), reste à la racine pour que le dev server marche sur :5173/.
        base: command === "build" ? "/voice/" : "/",
        plugins: [react()],
        resolve: {
            alias: { "@": path.resolve(__dirname, "./src") },
        },
        server: {
            // PORT permet à un lanceur externe d'imposer le port. strictPort évite la
            // dérive silencieuse de Vite vers 5174, 5175… quand le port est pris :
            // il vaut mieux échouer franchement que servir sur une adresse inattendue.
            port: Number(process.env.PORT) || 5173,
            strictPort: true,
            // En dev : proxy les WebSocket et /api vers le serveur FastAPI sur 8765
            proxy: {
                "/ws": {
                    target: "ws://localhost:8765",
                    ws: true,
                    changeOrigin: true,
                    configure: function (proxy) {
                        proxy.on("error", function () { });
                        proxy.on("proxyReqWs", function (_proxyReq, req, socket) {
                            if (socket && typeof socket.on === "function") {
                                socket.on("error", function () { });
                            }
                            if (req && req.socket && typeof req.socket.on === "function") {
                                req.socket.on("error", function () { });
                            }
                        });
                        proxy.on("open", function (proxySocket) {
                            if (proxySocket && typeof proxySocket.on === "function") {
                                proxySocket.on("error", function () { });
                            }
                        });
                    },
                },
                "/api": { target: "http://localhost:8765", changeOrigin: true },
                "/assets": { target: "http://localhost:8765", changeOrigin: true },
                "/status": { target: "http://localhost:8765", changeOrigin: true },
                "/devices": { target: "http://localhost:8765", changeOrigin: true },
            },
        },
        build: {
            outDir: "dist",
            emptyOutDir: true,
            sourcemap: false,
            target: "es2020",
        },
    });
});
