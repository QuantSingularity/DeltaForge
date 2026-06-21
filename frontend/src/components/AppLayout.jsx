import { useState } from "react";
import { Outlet } from "react-router-dom";
import { useLiveState } from "../hooks/useLiveState";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

// Shell for every authenticated page. Subscribes to the live snapshot stream
// exactly once and passes it down through the router Outlet context so the
// dashboard, trades, strategies, backtest and settings pages share a single
// WebSocket connection.
export default function AppLayout() {
  const { state, connected } = useLiveState();
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="min-h-screen flex">
      <Sidebar open={navOpen} onNavigate={() => setNavOpen(false)} />
      {navOpen ? (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setNavOpen(false)}
        />
      ) : null}

      <div className="flex-1 min-w-0 flex flex-col">
        <div className="p-3 md:p-4">
          <TopBar
            state={state}
            connected={connected}
            onMenu={() => setNavOpen(true)}
          />
        </div>
        <main className="flex-1 px-3 md:px-4 pb-6 max-w-[1500px] w-full mx-auto">
          <Outlet context={{ state, connected }} />
        </main>
      </div>
    </div>
  );
}
