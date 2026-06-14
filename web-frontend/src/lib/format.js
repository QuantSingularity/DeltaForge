// Display formatting + the single source of truth for trading color semantics.
// Color coding for actions/statuses is a product requirement, so it lives here
// rather than being sprinkled across components.

export const usd = (n, dp = 2) =>
  (n ?? 0).toLocaleString("en-US", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });

export const signed = (n, dp = 2) => `${n >= 0 ? "+" : ""}${usd(n, dp)}`;

export const pct = (n, dp = 1) => `${(n ?? 0).toFixed(dp)}%`;

export const ago = (ts) => {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
};

// Direction / side -> semantic class
export const dirClass = (d) =>
  d === "BUY" ? "text-buy" : d === "SELL" ? "text-sell" : "text-flat";

export const dirBg = (d) =>
  d === "BUY"
    ? "bg-buy/15 text-buy border-buy/30"
    : d === "SELL"
      ? "bg-sell/15 text-sell border-sell/30"
      : "bg-panel-800/60 text-ink-faint border-panel-700/60";

export const pnlClass = (n) => (n >= 0 ? "text-buy" : "text-sell");

// Event type -> color (mirrors the backend event log palette)
export const eventColor = (type) =>
  ({
    ENTRY: "text-ember-bright",
    EXIT_WIN: "text-buy",
    EXIT_LOSS: "text-sell",
    BUY_SIGNAL: "text-buy",
    SELL_SIGNAL: "text-sell",
    TRAIL: "text-warn",
    ANOMALY: "text-sell",
    HTF_REJECT: "text-ink-faint",
    ML_REJECT: "text-ink-faint",
    WARN: "text-warn",
    INFO: "text-ink-muted",
  })[type] || "text-ink-muted";

// Confluence strength -> heatmap intensity (0..100)
export const heatStyle = (signal, confidence) => {
  if (signal === "FLAT" || !confidence)
    return { background: "rgba(74,86,103,0.12)" };
  const a = Math.min(0.85, 0.18 + (confidence / 100) * 0.6);
  const rgb = signal === "BUY" ? "38,208,124" : "255,77,94";
  return { background: `rgba(${rgb},${a.toFixed(2)})` };
};
