// Thin REST client for the DeltaForge API. In dev, Vite proxies /api and /ws
// to the FastAPI server; in production the dashboard is served by FastAPI on
// the same origin, so relative paths work in both cases.

async function req(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json();
}

export const api = {
  health: () => req("/api/health"),
  state: () => req("/api/state"),
  strategies: () => req("/api/strategies"),
  config: () => req("/api/config"),
  patchConfig: (updates) =>
    req("/api/config", { method: "PUT", body: JSON.stringify({ updates }) }),
  start: () => req("/api/bot/start", { method: "POST" }),
  stop: () => req("/api/bot/stop", { method: "POST" }),
  backtest: (body) =>
    req("/api/backtest", { method: "POST", body: JSON.stringify(body) }),
};
