import { useOutletContext } from "react-router-dom";
import OpenTrades from "../components/OpenTrades";
import PageHeader from "../components/PageHeader";
import { ago, dirClass, pnlClass, signed, usd } from "../lib/format";

function Summary({ closed }) {
  const wins = closed.filter((t) => (t.pnl ?? 0) >= 0).length;
  const total = closed.length;
  const net = closed.reduce((s, t) => s + (t.pnl ?? 0), 0);
  const winRate = total ? (wins / total) * 100 : 0;

  const cards = [
    { label: "Closed trades", value: total, accent: "text-ink" },
    { label: "Win rate", value: `${winRate.toFixed(1)}%`, accent: "text-ink" },
    { label: "Wins", value: wins, accent: "text-buy" },
    { label: "Net P&L", value: `$${signed(net)}`, accent: pnlClass(net) },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
      {cards.map((c) => (
        <div key={c.label} className="panel px-4 py-3">
          <div className="eyebrow">{c.label}</div>
          <div className={`stat text-lg mt-1 ${c.accent}`}>{c.value}</div>
        </div>
      ))}
    </div>
  );
}

export default function Trades() {
  const { state } = useOutletContext();
  const closed = [...(state?.closed_trades || [])].reverse();

  return (
    <div>
      <PageHeader
        title="Trades"
        subtitle="Open positions and the closed-trade history for this session."
      />

      <Summary closed={state?.closed_trades || []} />

      <div className="mb-4">
        <OpenTrades state={state} />
      </div>

      <section className="panel">
        <div className="panel-head">
          <h2 className="text-sm font-semibold">Closed trades</h2>
          <span className="eyebrow">{closed.length} this session</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="text-left eyebrow">
                <th className="cell font-semibold">Symbol</th>
                <th className="cell font-semibold">Side</th>
                <th className="cell font-semibold text-right">Entry</th>
                <th className="cell font-semibold text-right">Exit</th>
                <th className="cell font-semibold text-right">Reason</th>
                <th className="cell font-semibold text-right">P&L</th>
                <th className="cell font-semibold text-right">When</th>
              </tr>
            </thead>
            <tbody>
              {closed.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="cell text-center text-ink-faint py-6"
                  >
                    No closed trades yet. They appear here as positions hit
                    their stop or target.
                  </td>
                </tr>
              ) : (
                closed.map((t, i) => (
                  <tr
                    key={t.id || i}
                    className="border-t border-panel-800/70 hover:bg-panel-850/40"
                  >
                    <td className="cell font-mono font-medium">{t.symbol}</td>
                    <td className={`cell font-semibold ${dirClass(t.side)}`}>
                      {t.side}
                    </td>
                    <td className="cell stat text-right">{usd(t.entry)}</td>
                    <td className="cell stat text-right">
                      {usd(t.exit ?? t.entry)}
                    </td>
                    <td className="cell text-right">
                      <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-panel-800 text-ink-muted">
                        {t.reason || "-"}
                      </span>
                    </td>
                    <td
                      className={`cell stat text-right font-semibold ${pnlClass(t.pnl ?? 0)}`}
                    >
                      ${signed(t.pnl ?? 0)}
                    </td>
                    <td className="cell text-right text-[11px] font-mono text-ink-faint">
                      {t.opened_at ? ago(t.opened_at) : "-"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
