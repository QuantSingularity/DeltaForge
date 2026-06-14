import StatusBar from "./components/StatusBar";
import SignalMatrix from "./components/SignalMatrix";
import OpenTrades from "./components/OpenTrades";
import RiskPanel from "./components/RiskPanel";
import EquityCurve from "./components/EquityCurve";
import ConfluenceHeatmap from "./components/ConfluenceHeatmap";
import EventLog from "./components/EventLog";
import ConfigEditor from "./components/ConfigEditor";
import BacktestPanel from "./components/BacktestPanel";
import { useLiveState } from "./hooks/useLiveState";

export default function App() {
  const { state, connected } = useLiveState();

  return (
    <div className="min-h-full p-3 md:p-5 max-w-[1500px] mx-auto space-y-4">
      <StatusBar state={state} connected={connected} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Primary column: live trading view */}
        <div className="lg:col-span-2 space-y-4">
          <SignalMatrix state={state} />
          <OpenTrades state={state} />
          <ConfluenceHeatmap />
        </div>

        {/* Secondary column: account, risk, controls */}
        <div className="space-y-4">
          <EquityCurve state={state} />
          <RiskPanel state={state} />
          <EventLog state={state} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <BacktestPanel />
        <ConfigEditor />
      </div>

      <footer className="text-center text-[11px] text-ink-faint py-4">
        DeltaForge · internal trading operations · {new Date().getFullYear()}
      </footer>
    </div>
  );
}
