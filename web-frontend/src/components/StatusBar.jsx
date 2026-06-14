import { useState } from "react";
import { api } from "../api/client";
import { pnlClass, signed, usd, pct } from "../lib/format";

function ForgeMark() {
  return (
    <div className="flex items-center gap-2.5">
      <svg width="26" height="26" viewBox="0 0 32 32" fill="none" aria-hidden>
        <path
          d="M6 24 L16 4 L26 24 Z"
          stroke="#ff7a18"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <path d="M11 24 L16 14 L21 24 Z" fill="#ff7a18" opacity="0.85" />
      </svg>
      <div className="leading-none">
        <div className="text-[15px] font-bold tracking-tight">
          Delta<span className="text-ember">Forge</span>
        </div>
        <div className="text-[9px] uppercase tracking-[0.22em] text-ink-faint mt-0.5">
          Trading Operations
        </div>
      </div>
    </div>
  );
}

function Stat({ label, children, accent }) {
  return (
    <div className="flex flex-col">
      <span className="eyebrow">{label}</span>
      <span className={`stat text-[15px] mt-0.5 ${accent || "text-ink"}`}>
        {children}
      </span>
    </div>
  );
}

export default function StatusBar({ state, connected }) {
  const [busy, setBusy] = useState(false);
  const status = state?.status || {};
  const account = state?.account || {};
  const running = status.bot_running;

  const toggle = async () => {
    setBusy(true);
    try {
      running ? await api.stop() : await api.start();
    } finally {
      setBusy(false);
    }
  };

  return (
    <header className="panel px-4 py-3 flex flex-wrap items-center gap-x-8 gap-y-3">
      <ForgeMark />

      <div className="flex items-center gap-2 pl-2 border-l border-panel-700/70">
        <span
          className={`w-2 h-2 rounded-full ${running ? "bg-buy pulse" : "bg-flat"}`}
        />
        <span className="text-sm font-medium">
          {running ? "Running" : "Stopped"}
        </span>
        <span className="text-xs text-ink-faint uppercase tracking-wider ml-1">
          {status.mode || "sandbox"} · {status.exchange || "—"}
        </span>
      </div>

      <div className="flex items-center gap-8 ml-auto">
        <Stat label="Balance">${usd(account.balance)}</Stat>
        <Stat label="Session P&L" accent={pnlClass(account.session_pnl || 0)}>
          ${signed(account.session_pnl || 0)}
        </Stat>
        <Stat label="Return" accent={pnlClass(account.session_pnl_pct || 0)}>
          {pct(account.session_pnl_pct || 0)}
        </Stat>

        <button
          onClick={toggle}
          disabled={busy}
          className={`px-4 py-2 rounded-md text-sm font-semibold border transition-colors ${
            running
              ? "border-sell/40 text-sell hover:bg-sell/10"
              : "border-ember/50 text-ember hover:bg-ember/10"
          } disabled:opacity-50`}
        >
          {busy ? "…" : running ? "Stop bot" : "Start bot"}
        </button>

        <span
          title={
            connected
              ? "Live stream connected"
              : "Polling (socket reconnecting)"
          }
          className={`text-[10px] font-mono px-2 py-1 rounded ${
            connected ? "text-buy bg-buy/10" : "text-warn bg-warn/10"
          }`}
        >
          {connected ? "● LIVE" : "○ POLL"}
        </span>
      </div>
    </header>
  );
}
