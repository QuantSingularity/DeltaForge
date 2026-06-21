import { usd } from "../lib/format";

function Gauge({ label, value, max, unit = "", tone = "ember" }) {
  const ratio = max ? Math.min(1, value / max) : 0;
  const bar =
    tone === "sell" ? "bg-sell" : tone === "warn" ? "bg-warn" : "bg-ember";
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="eyebrow">{label}</span>
        <span className="stat text-xs">
          {value}
          {unit}
          {max ? (
            <span className="text-ink-faint">
              {" "}
              / {max}
              {unit}
            </span>
          ) : null}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-panel-800 overflow-hidden">
        <div className={`h-full ${bar}`} style={{ width: `${ratio * 100}%` }} />
      </div>
    </div>
  );
}

export default function RiskPanel({ state }) {
  const r = state?.risk || {};
  const dd = r.drawdown_pct || 0;

  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="text-sm font-semibold">Risk dashboard</h2>
        <span className="eyebrow">live exposure</span>
      </div>
      <div className="p-4 space-y-4">
        <Gauge
          label="Open positions"
          value={r.open_positions || 0}
          max={r.max_total_orders || 10}
        />
        <Gauge
          label="Drawdown"
          value={dd.toFixed?.(2) ?? dd}
          max={null}
          unit="%"
          tone={dd > 10 ? "sell" : dd > 5 ? "warn" : "ember"}
        />
        <div className="grid grid-cols-2 gap-3 pt-1">
          <div>
            <div className="eyebrow">Exposure</div>
            <div className="stat text-sm mt-0.5">
              ${usd(r.exposure_usd || 0)}
            </div>
          </div>
          <div>
            <div className="eyebrow">Max loss / trade</div>
            <div className="stat text-sm mt-0.5">
              ${usd(r.max_loss_per_trade || 0)}
            </div>
          </div>
          <div>
            <div className="eyebrow">Trail type</div>
            <div className="stat text-sm mt-0.5 uppercase text-warn">
              {r.trail_type || "—"}
            </div>
          </div>
          <div>
            <div className="eyebrow">Trail</div>
            <div className="stat text-sm mt-0.5">
              {r.trail_enabled ? (
                <span className="text-buy">on</span>
              ) : (
                <span className="text-ink-faint">off</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
