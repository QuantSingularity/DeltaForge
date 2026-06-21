import BacktestPanel from "../components/BacktestPanel";
import PageHeader from "../components/PageHeader";

export default function Backtest() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Backtest"
        subtitle="Run an on-demand walk-forward backtest and review the headline metrics."
      />
      <div className="max-w-2xl">
        <BacktestPanel />
      </div>
    </div>
  );
}
