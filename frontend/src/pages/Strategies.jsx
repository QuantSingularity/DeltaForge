import { useOutletContext } from "react-router-dom";
import ConfluenceHeatmap from "../components/ConfluenceHeatmap";
import PageHeader from "../components/PageHeader";
import SignalMatrix from "../components/SignalMatrix";

export default function Strategies() {
  const { state } = useOutletContext();

  return (
    <div className="space-y-4">
      <PageHeader
        title="Strategies"
        subtitle="Per-symbol signal matrix and the live 26-strategy confluence heatmap."
      />
      <SignalMatrix state={state} />
      <ConfluenceHeatmap />
    </div>
  );
}
