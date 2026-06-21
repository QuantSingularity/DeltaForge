import { Area, AreaChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import { usd } from "../lib/format";

export default function EquityCurve({ state }) {
  const curve = state?.equity_curve || [];
  const data = curve.map((v, i) => ({ i, equity: v }));
  const start = curve[0] ?? 0;
  const last = curve[curve.length - 1] ?? start;
  const up = last >= start;
  const stroke = up ? "#26d07c" : "#ff4d5e";

  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="text-sm font-semibold">Equity curve</h2>
        <span className="stat text-xs text-ink-muted">${usd(last)}</span>
      </div>
      <div className="h-44 px-2 py-2">
        {data.length < 2 ? (
          <div className="h-full flex items-center justify-center text-ink-faint text-sm">
            Building equity history…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{ top: 8, right: 6, bottom: 0, left: 0 }}
            >
              <defs>
                <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={stroke} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <YAxis
                domain={["auto", "auto"]}
                width={54}
                tick={{
                  fill: "#5a6678",
                  fontSize: 10,
                  fontFamily: "JetBrains Mono",
                }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "#0f141c",
                  border: "1px solid #26303f",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ display: "none" }}
                formatter={(v) => [`$${usd(v)}`, "Equity"]}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke={stroke}
                strokeWidth={2}
                fill="url(#eq)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
