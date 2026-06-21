import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import Brand from "../components/Brand";

const FEATURES = [
  {
    title: "26 strategies, one verdict",
    body: "Trend, momentum, volatility, volume, price-action and advanced strategies vote through a confluence engine before any entry is considered.",
  },
  {
    title: "AI signal scoring",
    body: "A logistic-regression scorer rates every candidate 0 to 100 percent, learns online from outcomes, and auto-stops on anomalies.",
  },
  {
    title: "Risk that adapts live",
    body: "Per-trade loss caps, order and position limits, and five trailing-stop types. Edits hot-reload the running bot without a restart.",
  },
  {
    title: "Crypto and forex",
    body: "Ten crypto exchanges over ccxt plus a native Bitflex adapter, and forex through MT4 and MT5 Expert Advisors sharing the same logic.",
  },
  {
    title: "Four timeframes, confirmed",
    body: "15m, 1h, 4h and 1d only, with higher-timeframe trend confirmation required before an entry is taken.",
  },
  {
    title: "Live operations dashboard",
    body: "Signal matrix, open positions, confluence heatmap, equity curve, risk panel, event log and on-demand backtests, streamed in real time.",
  },
];

function Stat({ value, label }) {
  return (
    <div className="text-center">
      <div className="text-2xl md:text-3xl font-bold text-ink stat">
        {value}
      </div>
      <div className="eyebrow mt-1">{label}</div>
    </div>
  );
}

export default function Home() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="w-full max-w-6xl mx-auto px-5 py-4 flex items-center justify-between">
        <Brand subtitle="Trading Operations" />
        <nav className="flex items-center gap-3">
          {isAuthenticated ? (
            <Link
              to="/dashboard"
              className="px-4 py-2 rounded-md text-sm font-semibold border border-ember/50 text-ember hover:bg-ember/10 transition-colors"
            >
              Open dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/signin"
                className="px-4 py-2 rounded-md text-sm font-medium text-ink-muted hover:text-ink transition-colors"
              >
                Sign in
              </Link>
              <Link
                to="/signup"
                className="px-4 py-2 rounded-md text-sm font-semibold border border-ember/50 text-ember hover:bg-ember/10 transition-colors"
              >
                Get started
              </Link>
            </>
          )}
        </nav>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="max-w-6xl mx-auto px-5 pt-16 pb-20 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-panel-700/70 bg-panel-900/60 text-[11px] text-ink-muted mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-buy pulse" />
            Multi-strategy agentic trading core
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight leading-[1.05]">
            Forge an edge from
            <br />
            <span className="text-ember">confluence, not guesswork</span>
          </h1>
          <p className="mt-6 max-w-2xl mx-auto text-ink-muted text-base md:text-lg">
            DeltaForge runs 26 strategies, an AI scoring layer and adaptive risk
            management across crypto and forex, then shows you everything live
            in one operations dashboard.
          </p>
          <div className="mt-9 flex items-center justify-center gap-3">
            <Link
              to={isAuthenticated ? "/dashboard" : "/signup"}
              className="px-6 py-3 rounded-lg text-sm font-semibold bg-ember text-panel-950 hover:bg-ember-bright transition-colors"
            >
              {isAuthenticated ? "Open dashboard" : "Create an account"}
            </Link>
            <Link
              to="/signin"
              className="px-6 py-3 rounded-lg text-sm font-semibold border border-panel-700 text-ink hover:border-panel-600 transition-colors"
            >
              Sign in
            </Link>
          </div>

          <div className="mt-16 grid grid-cols-3 gap-6 max-w-lg mx-auto">
            <Stat value="26" label="Strategies" />
            <Stat value="10+" label="Exchanges" />
            <Stat value="4" label="Timeframes" />
          </div>
        </section>

        {/* Features */}
        <section className="max-w-6xl mx-auto px-5 pb-24">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f) => (
              <div key={f.title} className="panel p-5">
                <h3 className="text-sm font-semibold text-ink">{f.title}</h3>
                <p className="mt-2 text-sm text-ink-muted leading-relaxed">
                  {f.body}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA band */}
        <section className="max-w-6xl mx-auto px-5 pb-24">
          <div className="panel p-8 md:p-12 text-center">
            <h2 className="text-2xl md:text-3xl font-bold">
              Ready to run the desk?
            </h2>
            <p className="mt-3 text-ink-muted max-w-xl mx-auto">
              Spin up the dashboard in sandbox mode and watch the strategy
              confluence engine work before you connect a live account.
            </p>
            <Link
              to={isAuthenticated ? "/dashboard" : "/signup"}
              className="inline-block mt-7 px-6 py-3 rounded-lg text-sm font-semibold bg-ember text-panel-950 hover:bg-ember-bright transition-colors"
            >
              {isAuthenticated ? "Open dashboard" : "Get started free"}
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-panel-800/70">
        <div className="max-w-6xl mx-auto px-5 py-6 flex flex-col md:flex-row items-center justify-between gap-3 text-[11px] text-ink-faint">
          <Brand subtitle={null} size={20} />
          <span>
            Internal trading operations. No resale or commercial redistribution.{" "}
            {new Date().getFullYear()}
          </span>
        </div>
      </footer>
    </div>
  );
}
