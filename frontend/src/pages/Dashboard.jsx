import { useOutletContext } from "react-router-dom";
import ConfluenceHeatmap from "../components/ConfluenceHeatmap";
import EquityCurve from "../components/EquityCurve";
import EventLog from "../components/EventLog";
import OpenTrades from "../components/OpenTrades";
import RiskPanel from "../components/RiskPanel";
import SignalMatrix from "../components/SignalMatrix";

export default function Dashboard() {
  const { state } = useOutletContext();

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <SignalMatrix state={state} />
          <OpenTrades state={state} />
          <ConfluenceHeatmap />
        </div>
        <div className="space-y-4">
          <EquityCurve state={state} />
          <RiskPanel state={state} />
          <EventLog state={state} />
        </div>
      </div>
    </div>
  );
}
