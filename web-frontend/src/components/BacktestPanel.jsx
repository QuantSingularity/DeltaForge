import { useState } from "react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { api } from "../api/client";
import { pct, signed, usd } from "../lib/format";

const SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"];
const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

function Metric({ label, value, accent }) {
  return (
    <div className="bg-panel-850/60 rounded-md px-3 py-2">
      <div className="eyebrow">{label}</div>
      <div className={`stat text-sm mt-0.5 ${accent || "text-ink"}`}>
        {value}
      </div>
    </div>
  );
}

export default function BacktestPanel() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      setResult(await api.backtest({ symbol, timeframe, bars: 600 }));
    } catch (e) {
      setError("Backtest failed. Is the API running?");
    } finally {
      setRunning(false);
    }
  };

  const curve = (result?.equity_curve || []).map((v, i) => ({ i, equity: v }));

  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="text-sm font-semibold">Backtest</h2>
        <span className="eyebrow">walk-forward sandbox</span>
      </div>
      <div className="p-4 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-panel-850 border border-panel-700 rounded px-2 py-1.5 text-sm focus:border-ember/60 outline-none"
          >
            {SYMBOLS.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="bg-panel-850 border border-panel-700 rounded px-2 py-1.5 text-sm focus:border-ember/60 outline-none"
          >
            {TIMEFRAMES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          <button
            onClick={run}
            disabled={running}
            className="ml-auto px-4 py-1.5 rounded-md text-sm font-semibold border border-ember/50 text-ember hover:bg-ember/10 disabled:opacity-50"
          >
            {running ? "Running…" : "Run backtest"}
          </button>
        </div>

        {error && <div className="text-sell text-sm">{error}</div>}

        {result && (
          <>
            <div className="grid grid-cols-3 gap-2">
              <Metric label="Trades" value={result.total_trades} />
              <Metric label="Win rate" value={pct(result.win_rate)} />
              <Metric
                label="Net P&L"
                value={`$${signed(result.total_pnl)}`}
                accent={result.total_pnl >= 0 ? "text-buy" : "text-sell"}
              />
              <Metric
                label="Max DD"
                value={pct(result.max_drawdown)}
                accent="text-warn"
              />
              <Metric label="Sharpe" value={result.sharpe} />
              <Metric
                label="Profit factor"
                value={result.profit_factor ?? "∞"}
              />
            </div>
            {curve.length > 1 && (
              <div className="h-20">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={curve}
                    margin={{ top: 4, right: 0, bottom: 0, left: 0 }}
                  >
                    <defs>
                      <linearGradient id="bteq" x1="0" y1="0" x2="0" y2="1">
                        <stop
                          offset="0%"
                          stopColor="#ff7a18"
                          stopOpacity={0.3}
                        />
                        <stop
                          offset="100%"
                          stopColor="#ff7a18"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke="#ff7a18"
                      strokeWidth={1.5}
                      fill="url(#bteq)"
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
