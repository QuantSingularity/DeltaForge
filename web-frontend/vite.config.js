import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During development the dashboard proxies API + WebSocket traffic to the
// FastAPI server (uvicorn backend.api.server:app) running on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
