import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { pct, pnlClass, signed, usd } from "../lib/format";

function Stat({ label, children, accent }) {
  return (
    <div className="hidden sm:flex flex-col">
      <span className="eyebrow">{label}</span>
      <span className={`stat text-sm mt-0.5 ${accent || "text-ink"}`}>
        {children}
      </span>
    </div>
  );
}

export default function TopBar({ state, connected, onMenu }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const status = state?.status || {};
  const account = state?.account || {};
  const running = status.bot_running;

  const toggle = async () => {
    setBusy(true);
    try {
      if (running) await api.stop();
      else await api.start();
    } catch {
      /* surfaced via the event log */
    } finally {
      setBusy(false);
    }
  };

  const signOut = () => {
    logout();
    navigate("/", { replace: true });
  };

  const initial = (user?.name || user?.email || "?")
    .trim()
    .charAt(0)
    .toUpperCase();

  return (
    <header className="panel px-4 py-2.5 flex items-center gap-x-5 gap-y-2">
      <button
        onClick={onMenu}
        className="lg:hidden text-ink-muted hover:text-ink"
        aria-label="Toggle navigation"
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path
            d="M4 6h16M4 12h16M4 18h16"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      </button>

      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${running ? "bg-buy pulse" : "bg-flat"}`}
        />
        <span className="text-sm font-medium">
          {running ? "Running" : "Stopped"}
        </span>
        <span className="hidden md:inline text-xs text-ink-faint uppercase tracking-wider ml-1">
          {status.mode || "sandbox"} · {status.exchange || "-"}
        </span>
      </div>

      <div className="flex items-center gap-5 ml-auto">
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
          className={`px-3.5 py-1.5 rounded-md text-sm font-semibold border transition-colors ${
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

        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="w-8 h-8 rounded-full bg-ember/15 text-ember font-semibold text-sm flex items-center justify-center hover:bg-ember/25 transition-colors"
            aria-label="Account menu"
          >
            {initial}
          </button>
          {menuOpen ? (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setMenuOpen(false)}
              />
              <div className="absolute right-0 mt-2 w-52 panel p-2 z-20">
                <div className="px-3 py-2 border-b border-panel-800/70">
                  <div className="text-sm font-medium truncate">
                    {user?.name || "Account"}
                  </div>
                  <div className="text-xs text-ink-faint truncate">
                    {user?.email}
                  </div>
                </div>
                <button
                  onClick={signOut}
                  className="w-full text-left px-3 py-2 mt-1 rounded-md text-sm text-ink-muted hover:text-sell hover:bg-sell/10 transition-colors"
                >
                  Sign out
                </button>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}
