// REST client for the DeltaForge API.
//
// Base URL resolution:
//   - VITE_API_BASE (default "/api") is the prefix for all REST calls.
//   - In dev, vite.config.js proxies /api and /ws to the FastAPI server.
//   - In production the dashboard is served by FastAPI on the same origin,
//     so the relative "/api" prefix works without configuration.
//
// Auth: a bearer token (issued by POST /api/auth/login or /register) is stored
// in localStorage and attached to every request. A 401 clears it so the app
// falls back to the sign-in screen.

export const API_BASE = import.meta.env.VITE_API_BASE || "/api";

const TOKEN_KEY = "deltaforge_token";

export const tokenStore = {
  get: () => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token) => {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable (private mode); token stays in memory only */
    }
  },
  clear: () => tokenStore.set(null),
};

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function req(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  const url =
    path.startsWith("/api") || path.startsWith("http")
      ? path
      : `${API_BASE}${path}`;

  let res;
  try {
    res = await fetch(url, { ...options, headers });
  } catch {
    throw new ApiError(0, "Network error: is the API running?");
  }

  if (res.status === 401) {
    tokenStore.clear();
    throw new ApiError(401, "Session expired. Please sign in again.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.message || JSON.stringify(body);
    } catch {
      detail = (await res.text().catch(() => res.statusText)) || res.statusText;
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // Auth
  register: (payload) =>
    req("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) =>
    req("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => req("/auth/me"),

  // Dashboard data
  health: () => req("/health"),
  state: () => req("/state"),
  signals: () => req("/signals"),
  trades: () => req("/trades"),
  risk: () => req("/risk"),
  strategies: () => req("/strategies"),
  config: () => req("/config"),
  patchConfig: (updates) =>
    req("/config", { method: "PUT", body: JSON.stringify({ updates }) }),

  // Bot control
  start: () => req("/bot/start", { method: "POST" }),
  stop: () => req("/bot/stop", { method: "POST" }),
  backtest: (body) =>
    req("/backtest", { method: "POST", body: JSON.stringify(body) }),
};
