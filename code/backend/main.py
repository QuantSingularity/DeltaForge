"""
DeltaForge Crypto Bot - Main Entry Point v1.2
─────────────────────────────────────────────────────────────────────
Usage:
  python -m backend                   # live trading
  python -m backend --backtest        # walk-forward backtest
  python -m backend --sandbox         # paper trading
  python -m backend --exchange bybit  # override exchange
  python -m backend --retrain         # retrain ML from outcomes
─────────────────────────────────────────────────────────────────────
"""

import argparse
import os
import signal
import time
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from ai_models.anomaly.anomaly_detector import AnomalyDetector
from ai_models.features.feature_extractor import FeatureExtractor
from ai_models.learning.online_learner import OnlineLearner
from ai_models.scoring.signal_scorer import SignalScorer

from .backtest.engine import BacktestEngine
from .backtest.metrics import BacktestMetrics

# ── Internal imports (all from new subpackages) ───────────────────────
from .core.config import ConfigManager
from .core.logger import get_logger, setup_logging
from .display.dashboard import DeltaForgeDisplay
from .display.event_log import EVT_ANOMALY, EVT_HTF_REJECT, EVT_ML_REJECT
from .exchanges.exchange_manager import ExchangeManager
from .notifications.notifier import Notifier
from .risk.risk_manager import RiskManager
from .strategies.engine import StrategyEngine
from .strategies.indicators import _adx
from .trading.portfolio import Portfolio
from .trading.trade_manager import TradeManager

TIMEFRAMES = ["15m", "1h", "4h", "1d"]
DEFAULT_SCAN = {"15m": 2100, "1h": 3600, "4h": 14400, "1d": 86400}


class DeltaForgeBot:

    def __init__(
        self, config_path: str, exchange_id: str = None, sandbox: bool = False
    ):
        # ── Config ────────────────────────────────────────────────────
        self.cfg_mgr = ConfigManager(config_path)
        cfg = self.cfg_mgr.as_dict()

        setup_logging(level=cfg.get("log_level", "info"))
        self.logger = get_logger("Bot")
        self.running = False
        self.bot_active = self.cfg_mgr.bot_running

        # ── Exchange ──────────────────────────────────────────────────
        exc_cfg = cfg["exchange"]
        ex_id = exchange_id or exc_cfg.get("id", "binance")
        self.exchange = ExchangeManager(
            exchange_id=ex_id,
            api_key=exc_cfg.get("api_key", ""),
            api_secret=exc_cfg.get("api_secret", ""),
            passphrase=exc_cfg.get("passphrase", ""),
            trade_type=exc_cfg.get("trade_type", "spot"),
            sandbox=sandbox or exc_cfg.get("sandbox", False),
            bitflex_base_url=exc_cfg.get("bitflex_base_url", "https://api.bitflex.com"),
        )

        # ── Core components ───────────────────────────────────────────
        self.display = DeltaForgeDisplay(cfg)
        self.risk = RiskManager(cfg)
        self.strategies = StrategyEngine(cfg)
        self.scorer = SignalScorer()
        self.scorer.load_weights()  # restore persisted weights if present
        self.extractor = FeatureExtractor()
        self.anomaly = AnomalyDetector(cfg)
        self.learner = OnlineLearner(self.scorer)
        self.notifier = Notifier(cfg)
        self.portfolio = Portfolio(self.cfg_mgr.initial_capital)

        # ── Trade manager wired to display + notifier trail callbacks ─
        def _on_trail(symbol, side, old_sl, new_sl):
            self.display.log_trail_update(symbol, side, old_sl, new_sl)
            self.notifier.trail_update(symbol, side, old_sl, new_sl)

        self.trade_mgr = TradeManager(
            exchange=self.exchange,
            risk=self.risk,
            config=cfg,
            trail_event_cb=_on_trail,
        )

        # ── Config reload propagation ─────────────────────────────────
        self.cfg_mgr.on_reload(self.risk.reload)

        scan_cfg = cfg.get("scan_intervals", {})
        self.scan_intervals = {
            tf: scan_cfg.get(tf, DEFAULT_SCAN[tf]) for tf in TIMEFRAMES
        }
        self.last_scan: Dict[str, float] = {tf: 0 for tf in TIMEFRAMES}
        self._ohlcv_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self._bt_win_rates: Dict[str, float] = {}

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        self.logger.info(f"DeltaForge Bot v1.2 | Exchange: {ex_id.upper()}")

    # ── MAIN LOOP ────────────────────────────────────────────────────
    def run(self):
        self.running = True
        self.display.set_bot_status(self.bot_active, "Initialized")
        self.notifier.bot_started(self.cfg_mgr.exchange_id)
        self._warm_cache()
        self._bt_win_rates = BacktestEngine.load_bt_win_rates(
            self._get_symbols(), TIMEFRAMES
        )
        while self.running:
            try:
                self._tick()
                time.sleep(10)
            except Exception as e:
                self.logger.error(f"Main loop error: {e}", exc_info=True)
                time.sleep(30)

    def _tick(self):
        now = time.time()
        self.cfg_mgr.check_reload()

        current_prices = self._get_current_prices()
        live_trades = self.trade_mgr.get_all_trades()
        risk_summary = self.risk.get_risk_summary(
            live_trades, current_prices, self.portfolio.net_pnl
        )
        self.display.update_stats(
            {
                "total_pnl": self.portfolio.net_pnl,
                "total_trades": self.portfolio.total_trades,
                "risk_summary": risk_summary,
                "portfolio": self.portfolio.to_summary_dict(),
            }
        )

        # Sync closed positions → portfolio + online learning
        closed = self.trade_mgr.sync_positions()
        for c in closed:
            self.portfolio.record_close(
                symbol=c["symbol"],
                side=c["side"],
                entry_price=c.get("entry_price", 0),
                exit_price=c.get("exit_price", 0),
                amount=c.get("amount", 0),
                pnl=c["pnl"],
                open_time=c.get("open_time", time.time()),
                exit_reason=c.get("reason", "sl"),
                timeframe=c.get("timeframe", ""),
                strategy=c.get("strategies", ""),
            )
            self.portfolio.remove_deployed(c.get("amount", 0) * c.get("exit_price", 0))
            if c.get("features"):
                self.learner.record(
                    np.array(c["features"]),
                    c["direction"],
                    c.get("confluence", 50),
                    c["pnl"],
                )
            self.display.log_exit(
                c["symbol"],
                c["side"],
                c.get("exit_price", 0),
                c["pnl"],
                reason=c.get("reason", ""),
            )
            self.notifier.trade_exit(
                c["symbol"],
                c["side"],
                c.get("exit_price", 0),
                c["pnl"],
                c.get("reason", ""),
            )

        if not self.bot_active:
            self._update_trades_display(current_prices)
            self.display.render()
            return

        # Anomaly detection
        for sym in self._get_symbols():
            ticker = self.exchange.fetch_ticker(sym)
            if ticker:
                spread_pct = (
                    (ticker.get("ask", 0) - ticker.get("bid", 0))
                    / max(ticker.get("last", 1), 1)
                    * 100
                )
                self.anomaly.update(ticker.get("last", 0), ticker.get("quoteVolume", 0))
                is_anom, reason = self.anomaly.is_anomaly(
                    ticker.get("last", 0), ticker.get("quoteVolume", 0), spread_pct
                )
                if is_anom and self.cfg_mgr.auto_stop_anomaly:
                    self.bot_active = False
                    self.display._add_event(EVT_ANOMALY, f"AUTO-STOP: {reason}")
                    self.display.set_bot_status(False, f"Anomaly: {reason}")
                    self.notifier.anomaly_detected(reason)
                    return

        df_map = self._build_df_map()
        self.trade_mgr.detect_and_fix_manual_trades(df_map, self._bt_win_rates)
        self.trade_mgr.update_trail_stops(current_prices, df_map)

        for tf in TIMEFRAMES:
            if (now - self.last_scan[tf]) >= self.scan_intervals[tf]:
                self._scan_timeframe(tf)
                self.last_scan[tf] = now

        self._update_trades_display(current_prices)
        self.display.render()

    # ── PER-TIMEFRAME SCAN ───────────────────────────────────────────
    def _scan_timeframe(self, tf: str):
        for symbol in self._get_symbols():
            try:
                self._scan_symbol(symbol, tf)
            except Exception as e:
                self.logger.error(f"Scan error {symbol}/{tf}: {e}")

    def _scan_symbol(self, symbol: str, tf: str):
        df = self._get_ohlcv(symbol, tf)
        if df is None or len(df) < 200:
            return

        open_orders = self.exchange.get_open_orders(symbol)
        positions = self.exchange.get_positions(symbol)
        allowed, reason = self.risk.can_place_order(
            open_orders, positions, symbol, "buy"
        )
        if not allowed:
            return

        sig = self.strategies.run_all(df)
        direction = sig["direction"]
        confluence = sig["confluence"]
        if direction == 0 or confluence < 40:
            return

        if self.cfg_mgr.htf_enabled and not self._check_htf(symbol, tf, direction):
            self.display._add_event(
                EVT_HTF_REJECT,
                f"HTF rejected {symbol} {tf} {'BUY' if direction==1 else 'SELL'}",
            )
            return

        bt_wr = self._bt_win_rates.get(symbol, 0.0)
        features = self.extractor.extract(df)
        features[9] = confluence / 100.0
        ml_score = self.scorer.score(features, direction, confluence)
        probability = ml_score * 0.7 + bt_wr * 0.3 if bt_wr > 0 else ml_score

        entry_price = float(df["close"].iloc[-1])
        side = "buy" if direction == 1 else "sell"
        sl, tp = self.risk.calculate_sl_tp(df, side, entry_price, bt_win_rate=bt_wr)

        self.display.update_signal(
            symbol=symbol,
            timeframe=tf,
            direction=direction,
            confluence=confluence,
            ml_score=ml_score,
            probability=probability,
            sl=sl,
            tp=tp,
            strategies=sig["hits"],
        )

        if ml_score < self.cfg_mgr.min_ml_score:
            self.display._add_event(
                EVT_ML_REJECT,
                f"ML rejected {symbol}/{tf} {ml_score:.1f}% < {self.cfg_mgr.min_ml_score}%",
            )
            return

        allowed, reason = self.risk.can_place_order(
            open_orders, positions, symbol, side
        )
        if not allowed:
            return

        trade = self.trade_mgr.open_trade(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            sl=sl,
            tp=tp,
            df=df,
            timeframe=tf,
            confluence=confluence,
            ml_score=ml_score,
            strategies=" ".join(sig["hits"][:8]),
            features=features.tolist(),
        )
        if trade:
            self.portfolio.add_deployed(trade.amount * trade.entry_price)
            self.display.log_entry(
                symbol=symbol,
                side=side,
                entry=trade.entry_price,
                sl=trade.sl,
                tp=trade.tp,
                amount=trade.amount,
                ml_score=ml_score,
                tf=tf,
            )
            self.notifier.trade_entry(
                symbol,
                side,
                trade.entry_price,
                trade.sl,
                trade.tp,
                trade.amount,
                ml_score,
                tf,
            )

    # ── HTF VALIDATION ───────────────────────────────────────────────
    def _check_htf(self, symbol: str, tf: str, direction: int) -> bool:
        htf_map = {
            "15m": ["1h", "4h"],
            "1h": ["4h", "1d"],
            "4h": ["1d"],
            "1d": [],
        }
        htfs = htf_map.get(tf, [])
        if not htfs:
            return True
        results = []
        for htf in htfs:
            df = self._get_ohlcv(symbol, htf)
            if df is None or len(df) < 50:
                results.append(True)
                continue
            ema = df["close"].ewm(span=20, adjust=False).mean()
            slope = ema.iloc[-1] - ema.iloc[-2]
            adx, pos_di, neg_di = _adx(df)
            adx_val = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
            htf_buy = slope > 0 and (adx_val < 20 or pos_di.iloc[-1] >= neg_di.iloc[-1])
            htf_sell = slope < 0 and (
                adx_val < 20 or neg_di.iloc[-1] >= pos_di.iloc[-1]
            )
            results.append(
                (direction == 1 and htf_buy) or (direction == -1 and htf_sell)
            )
        return all(results) if self.cfg_mgr.htf_require_both else any(results)

    # ── OHLCV HELPERS ────────────────────────────────────────────────
    def _get_ohlcv(
        self, symbol: str, tf: str, limit: int = 500
    ) -> Optional[pd.DataFrame]:
        raw = self.exchange.fetch_ohlcv(symbol, tf, limit=limit)
        if not raw:
            return None
        df = pd.DataFrame(
            raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp").sort_index()
        for c in ("open", "high", "low", "close", "volume"):
            df[c] = df[c].astype(float)
        self._ohlcv_cache.setdefault(symbol, {})[tf] = df
        return df

    def _warm_cache(self):
        self.logger.info("Warming OHLCV cache...")
        for sym in self._get_symbols():
            for tf in TIMEFRAMES:
                self._get_ohlcv(sym, tf)
                time.sleep(0.3)

    def _build_df_map(self) -> Dict[str, pd.DataFrame]:
        return {
            sym: self._ohlcv_cache.get(sym, {}).get("1h")
            for sym in self._get_symbols()
            if self._ohlcv_cache.get(sym, {}).get("1h") is not None
        }

    def _get_current_prices(self) -> Dict[str, float]:
        return {
            sym: float(t.get("last", 0))
            for sym in self._get_symbols()
            for t in [self.exchange.fetch_ticker(sym)]
            if t
        }

    def _get_symbols(self) -> List[str]:
        return self.cfg_mgr.symbols

    def _update_trades_display(self, current_prices: dict):
        result = []
        for t in self.trade_mgr.get_all_trades():
            price = current_prices.get(t.symbol, t.entry_price)
            upnl = (
                (price - t.entry_price) if t.side == "buy" else (t.entry_price - price)
            ) * t.amount
            result.append(
                {
                    "symbol": t.symbol,
                    "side": t.side,
                    "entry_price": t.entry_price,
                    "current_price": price,
                    "sl": t.current_sl,
                    "tp": t.tp,
                    "amount": t.amount,
                    "unrealized_pnl": round(upnl, 4),
                    "timeframe": t.timeframe,
                    "ml_score": t.ml_score,
                    "trail_updated": t.trail_updated,
                }
            )
        self.display.update_trades(result)

    # ── SHUTDOWN ─────────────────────────────────────────────────────
    def _handle_shutdown(self, *_):
        self.logger.info("Shutdown signal received")
        self.running = False
        self.scorer.save_weights()
        self.notifier.bot_stopped("Shutdown signal")
        self.display.log("Bot shutting down...", "yellow")

    def stop(self):
        self.bot_active = False
        self.display.set_bot_status(False, "Stopped")
        self.notifier.bot_stopped()

    def start(self):
        self.bot_active = True
        self.display.set_bot_status(True, "Started")


# ── BACKTEST RUNNER ──────────────────────────────────────────────────
def run_backtest(config_path: str, exchange_id: str = None):
    cfg_mgr = ConfigManager(config_path)
    cfg = cfg_mgr.as_dict()
    display = DeltaForgeDisplay(cfg)
    exc_cfg = cfg["exchange"]
    exchange = ExchangeManager(
        exchange_id=exchange_id or exc_cfg.get("id", "binance"),
        api_key=exc_cfg.get("api_key", ""),
        api_secret=exc_cfg.get("api_secret", ""),
        passphrase=exc_cfg.get("passphrase", ""),
        trade_type="spot",
        sandbox=True,
        bitflex_base_url=exc_cfg.get("bitflex_base_url", ""),
    )
    bt_engine = BacktestEngine(cfg)
    for symbol in cfg.get("symbols", ["BTC/USDT"]):
        for tf in TIMEFRAMES:
            print(f"\nBacktesting {symbol} / {tf}...")
            raw = exchange.fetch_ohlcv(symbol, tf, limit=1000)
            if not raw or len(raw) < 300:
                print(f"  Insufficient data")
                continue
            df = pd.DataFrame(
                raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("timestamp").sort_index()
            for c in ("open", "high", "low", "close", "volume"):
                df[c] = df[c].astype(float)
            result = bt_engine.run(
                df, symbol, tf, initial_capital=cfg.get("initial_capital", 10000)
            )
            display.print_backtest_result(result)
            pnls = [t["pnl"] for t in result.trades]
            equity = result.equity_curve
            if pnls and equity:
                m = BacktestMetrics(pnls, equity, cfg.get("initial_capital", 10000))
                print("  Extended metrics:", m.report())
            time.sleep(1)


# ── CLI ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="DeltaForge AI Trading Bot")
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--exchange", type=str, default=None)
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "config.json"),
    )
    parser.add_argument("--retrain", action="store_true")
    args = parser.parse_args()

    if args.retrain:
        scorer = SignalScorer()
        learner = OnlineLearner(scorer)
        learner.load_history_and_retrain()
        print("ML model retrained.")
        return

    if args.backtest:
        run_backtest(args.config, args.exchange)
        return

    bot = DeltaForgeBot(args.config, exchange_id=args.exchange, sandbox=args.sandbox)
    bot.run()


if __name__ == "__main__":
    main()
