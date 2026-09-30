import { dirBg, pct } from "../lib/format";

const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

function SignalCell({ sig }) {
  if (!sig) return <td className="cell text-center text-ink-faint">-</td>;
  return (
    <td className="cell text-center">
      <div
        className={`inline-flex flex-col items-center gap-0.5 px-2 py-1 rounded border ${dirBg(
          sig.direction,
        )}`}
      >
        <span className="text-xs font-semibold">{sig.direction}</span>
        <span className="stat text-[10px] opacity-80">
          {pct(sig.confluence)} · ML {sig.ml_score || 0}
        </span>
      </div>
    </td>
  );
}

export default function SignalMatrix({ state }) {
  const signals = state?.signals || {};
  const symbols = Object.keys(signals);

  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="text-sm font-semibold">Signal matrix</h2>
        <span className="eyebrow">confluence · ml score</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-left">
              <th className="cell eyebrow font-semibold">Symbol</th>
              {TIMEFRAMES.map((tf) => (
                <th key={tf} className="cell eyebrow font-semibold text-center">
                  {tf}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {symbols.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="cell text-center text-ink-faint py-6"
                >
                  Waiting for the first scan…
                </td>
              </tr>
            )}
            {symbols.map((sym) => (
              <tr
                key={sym}
                className="border-t border-panel-800/70 hover:bg-panel-850/40"
              >
                <td className="cell font-mono font-medium">{sym}</td>
                {TIMEFRAMES.map((tf) => (
                  <SignalCell key={tf} sig={signals[sym]?.[tf]} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
