import { useEffect, useState } from "react";
import { api } from "../api/client";

// Edits the bot's live configuration. Writes go through PUT /api/config which
// persists and hot-reloads, so changes take effect without a restart.
const TRAIL_TYPES = ["atr", "percent", "dollar", "time", "volatility"];

export default function ConfigEditor() {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .config()
      .then(setCfg)
      .catch(() => {});
  }, []);

  if (!cfg) {
    return (
      <section className="panel">
        <div className="panel-head">
          <h2 className="text-sm font-semibold">Configuration</h2>
        </div>
        <div className="p-4 text-ink-faint text-sm">Loading config…</div>
      </section>
    );
  }

  const minMl = cfg.min_ml_score ?? 60;
  const trail = cfg.trail_stop || {};
  const risk = cfg.risk || {};

  const save = async (updates) => {
    setSaving(true);
    setSaved(false);
    try {
      const res = await api.patchConfig(updates);
      setCfg(res.config);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } finally {
      setSaving(false);
    }
  };

  const Field = ({ label, children }) => (
    <label className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-sm text-ink-muted">{label}</span>
      {children}
    </label>
  );

  const numInput = (val, onCommit) => (
    <input
      type="number"
      defaultValue={val}
      onBlur={(e) => onCommit(parseFloat(e.target.value))}
      className="w-24 bg-panel-850 border border-panel-700 rounded px-2 py-1 stat text-sm text-right focus:border-ember/60 outline-none"
    />
  );

  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="text-sm font-semibold">Configuration</h2>
        <span className="eyebrow">
          {saving
            ? "saving…"
            : saved
              ? "saved · hot-reloaded"
              : "edits apply live"}
        </span>
      </div>
      <div className="p-4 divide-y divide-panel-800/70">
        <Field label="Minimum ML score">
          {numInput(minMl, (v) => save({ min_ml_score: v }))}
        </Field>
        <Field label="Max loss per trade ($)">
          {numInput(risk.max_loss_per_trade, (v) =>
            save({ risk: { ...risk, max_loss_per_trade: v } }),
          )}
        </Field>
        <Field label="Max total orders">
          {numInput(risk.max_total_orders, (v) =>
            save({ risk: { ...risk, max_total_orders: v } }),
          )}
        </Field>
        <Field label="Max lot size">
          {numInput(risk.max_lot_size, (v) =>
            save({ risk: { ...risk, max_lot_size: v } }),
          )}
        </Field>
        <Field label="Trailing stop">
          <button
            onClick={() =>
              save({ trail_stop: { ...trail, enabled: !trail.enabled } })
            }
            className={`px-3 py-1 rounded text-xs font-semibold border ${
              trail.enabled
                ? "border-buy/40 text-buy bg-buy/10"
                : "border-panel-600 text-ink-faint"
            }`}
          >
            {trail.enabled ? "ON" : "OFF"}
          </button>
        </Field>
        <Field label="Trail type">
          <select
            value={trail.type}
            onChange={(e) =>
              save({ trail_stop: { ...trail, type: e.target.value } })
            }
            className="bg-panel-850 border border-panel-700 rounded px-2 py-1 text-sm focus:border-ember/60 outline-none capitalize"
          >
            {TRAIL_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Take profit">
          <button
            onClick={() =>
              save({
                risk: {
                  ...risk,
                  take_profit_enabled: !risk.take_profit_enabled,
                },
              })
            }
            className={`px-3 py-1 rounded text-xs font-semibold border ${
              risk.take_profit_enabled
                ? "border-buy/40 text-buy bg-buy/10"
                : "border-panel-600 text-ink-faint"
            }`}
          >
            {risk.take_profit_enabled ? "ON" : "OFF"}
          </button>
        </Field>
      </div>
    </section>
  );
}
