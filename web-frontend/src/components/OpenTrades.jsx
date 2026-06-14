import { dirClass, pnlClass, signed, usd } from "../lib/format";

export default function OpenTrades({ state }) {
  const trades = state?.open_trades || [];

  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="text-sm font-semibold">Open positions</h2>
        <span className="eyebrow">{trades.length} active</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="text-left eyebrow">
              <th className="cell font-semibold">Symbol</th>
              <th className="cell font-semibold">Side</th>
              <th className="cell font-semibold text-right">Entry</th>
              <th className="cell font-semibold text-right">Price</th>
              <th className="cell font-semibold text-right">SL</th>
              <th className="cell font-semibold text-right">TP</th>
              <th className="cell font-semibold text-right">Trail</th>
              <th className="cell font-semibold text-right">P&L</th>
            </tr>
          </thead>
          <tbody>
            {trades.length === 0 && (
              <tr>
                <td
                  colSpan={8}
                  className="cell text-center text-ink-faint py-6"
                >
                  No open positions. The bot opens trades when ML score clears
                  the threshold.
                </td>
              </tr>
            )}
            {trades.map((t) => (
              <tr
                key={t.id}
                className="border-t border-panel-800/70 hover:bg-panel-850/40"
              >
                <td className="cell font-mono font-medium">{t.symbol}</td>
                <td className={`cell font-semibold ${dirClass(t.side)}`}>
                  {t.side}
                </td>
                <td className="cell stat text-right">{usd(t.entry)}</td>
                <td className="cell stat text-right">
                  {usd(t.price ?? t.entry)}
                </td>
                <td className="cell stat text-right text-sell/90">
                  {usd(t.sl)}
                </td>
                <td className="cell stat text-right text-buy/90">
                  {usd(t.tp)}
                </td>
                <td className="cell text-right">
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-warn/10 text-warn">
                    {t.trail}
                  </span>
                </td>
                <td
                  className={`cell stat text-right font-semibold ${pnlClass(t.pnl ?? 0)}`}
                >
                  ${signed(t.pnl ?? 0)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
