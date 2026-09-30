import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В режиме разработки Vite проксирует запросы к микросервисам — так же, как nginx в docker-compose:
//   /api/auth/*  -> auth-service       /api/*
//   /api/data/*  -> timescale-service  /*
const AUTH = process.env.AUTH_SERVICE_URL ?? "http://localhost:8001";
const DATA = process.env.TIMESCALE_SERVICE_URL ?? "http://localhost:5145";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api/auth": { target: AUTH, changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/auth/, "/api") },
      "/api/data": { target: DATA, changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/data/, "") },
    },
  },
});
