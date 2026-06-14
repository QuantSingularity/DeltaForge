import { useEffect, useState } from "react";
import { api } from "../api/client";
import { heatStyle } from "../lib/format";

export default function ConfluenceHeatmap() {
  const [data, setData] = useState(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const d = await api.strategies();
        if (alive) setData(d);
      } catch {
        /* server warming */
      }
    };
    tick();
    const id = setInterval(tick, 5000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const strategies = data?.strategies || [];
  const rows = data?.rows || [];

  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="text-sm font-semibold">Strategy confluence</h2>
        <span className="eyebrow">{strategies.length} strategies</span>
      </div>
      <div className="p-3 overflow-x-auto">
        {rows.length === 0 ? (
          <div className="text-ink-faint text-sm py-6 text-center">
            Loading heatmap…
          </div>
        ) : (
          <table className="border-collapse">
            <thead>
              <tr>
                <th className="sticky left-0 bg-panel-900 z-10 px-2 py-1 text-left eyebrow">
                  Symbol
                </th>
                {strategies.map((s) => (
                  <th
                    key={s}
                    className="px-1 py-1 text-[9px] text-ink-faint font-medium align-bottom"
                    style={{ writingMode: "vertical-rl", height: 78 }}
                    title={s}
                  >
                    {s}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.symbol}>
                  <td className="sticky left-0 bg-panel-900 z-10 px-2 py-1 font-mono text-xs whitespace-nowrap">
                    {row.symbol}
                  </td>
                  {strategies.map((s) => {
                    const cell = row.strategies[s] || {
                      signal: "FLAT",
                      confidence: 0,
                    };
                    return (
                      <td key={s} className="p-0.5">
                        <div
                          className="w-4 h-4 rounded-[3px]"
                          style={heatStyle(cell.signal, cell.confidence)}
                          title={`${s}: ${cell.signal} ${cell.confidence}%`}
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="px-4 pb-3 flex items-center gap-4 text-[10px] text-ink-faint">
        <span className="flex items-center gap-1.5">
          <span
            className="w-3 h-3 rounded-sm"
            style={{ background: "rgba(38,208,124,0.7)" }}
          />{" "}
          Buy
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="w-3 h-3 rounded-sm"
            style={{ background: "rgba(255,77,94,0.7)" }}
          />{" "}
          Sell
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="w-3 h-3 rounded-sm"
            style={{ background: "rgba(74,86,103,0.12)" }}
          />{" "}
          Flat
        </span>
        <span className="ml-auto">Opacity encodes confidence</span>
      </div>
    </section>
  );
}
