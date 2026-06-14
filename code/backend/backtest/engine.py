"""DeltaForge — Walk-forward BacktestEngine."""

"""
DeltaForge Backtest Engine
Walk-forward backtesting on historical OHLCV data.
Outputs: equity curve, trade log, per-strategy win rates, ML training dataset.
Trail simulation now uses the configured trail type (not hardcoded 1%).
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from ai_models.scoring.signal_scorer import SignalScorer

from ..risk.risk_manager import RiskManager
from ..strategies.engine import StrategyEngine

logger = logging.getLogger("DeltaForge.Backtest")


@dataclass
class BTTrade:
    symbol: str
    side: str
    entry_price: float
    entry_idx: int
    sl: float
    tp: float
    lot: float
    peak_price: float = 0.0
    exit_price: float = 0.0
    exit_idx: int = 0
    pnl: float = 0.0
    status: str = "open"  # open|sl|tp|trail|timeout
    strategies: str = ""
    confluence: float = 0.0
    ml_score: float = 0.0
    features: list = field(default_factory=list)


@dataclass
class BTResult:
    symbol: str
    timeframe: str
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    best_strategy: str = ""
    equity_curve: list = field(default_factory=list)
    trades: list = field(default_factory=list)


class BacktestEngine:
    """
    Event-driven walk-forward backtester.
    Uses the configured trailing stop type for accurate simulation.
    """

    def __init__(self, config: dict):
        self.cfg = config
        self.risk_cfg = config.get("risk", {})
        self.bt_cfg = config.get("backtest", {})
        self.trail_cfg = config.get("trail_stop", {})
        self.strategies = StrategyEngine(config)
        self.risk_mgr = RiskManager(config)
        self.scorer = SignalScorer()
        self.lookback = 200

    # ─────────────────────────────────────────────────────────────
    # MAIN ENTRY
    # ─────────────────────────────────────────────────────────────
    def run(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        initial_capital: float = 10000.0,
        walk_forward: bool = True,
    ) -> BTResult:
        logger.info(f"Backtest: {symbol} {timeframe} | {len(df)} bars")
        if walk_forward:
            return self._walk_forward(df, symbol, timeframe, initial_capital)
        return self._simple_run(df, symbol, timeframe, initial_capital)

    # ─────────────────────────────────────────────────────────────
    # WALK-FORWARD
    # ─────────────────────────────────────────────────────────────
    def _walk_forward(
        self, df: pd.DataFrame, symbol: str, timeframe: str, capital: float
    ) -> BTResult:
        n = len(df)
        wf_size = self.bt_cfg.get("walk_forward_bars", 200)
        train_pct = self.bt_cfg.get("train_pct", 0.7)

        all_trades: List[BTTrade] = []
        equity_val = capital
        equity = [capital]

        step = max(wf_size // 4, 50)
        for start in range(self.lookback, n - wf_size, step):
            end = min(start + wf_size, n)
            window = df.iloc[:end]
            train_end = start + int(wf_size * train_pct)
            train_df = window.iloc[:train_end]

            X_train, y_train = self._build_training_data(train_df, symbol)
            if len(X_train) >= 30:
                self.scorer.train(X_train, y_train, lr=0.02, epochs=300)

            seg_trades, equity_val = self._simulate_segment(
                window.iloc[train_end:], symbol, equity_val, full_df=window
            )
            all_trades.extend(seg_trades)
            equity.append(equity_val)

        result = self._compile_result(all_trades, equity, symbol, timeframe, capital)
        self._save_result(result, symbol, timeframe)
        return result

    # ─────────────────────────────────────────────────────────────
    # SIMPLE RUN
    # ─────────────────────────────────────────────────────────────
    def _simple_run(
        self, df: pd.DataFrame, symbol: str, timeframe: str, capital: float
    ) -> BTResult:
        trades, final_eq = self._simulate_segment(df, symbol, capital, full_df=df)
        equity = [capital] + [
            capital + sum(t.pnl for t in trades[: i + 1]) for i in range(len(trades))
        ]
        result = self._compile_result(trades, equity, symbol, timeframe, capital)
        self._save_result(result, symbol, timeframe)
        return result

    # ─────────────────────────────────────────────────────────────
    # CORE SIMULATION
    # ─────────────────────────────────────────────────────────────
    def _simulate_segment(
        self, df: pd.DataFrame, symbol: str, capital: float, full_df: pd.DataFrame
    ) -> Tuple[List[BTTrade], float]:
        open_trades: List[BTTrade] = []
        closed_trades: List[BTTrade] = []
        equity = capital

        max_total = self.risk_cfg.get("max_total_orders", 10)
        max_pair = self.risk_cfg.get("max_orders_per_pair", 2)
        max_buy = self.risk_cfg.get("max_buy_orders", 5)
        max_sell = self.risk_cfg.get("max_sell_orders", 5)

        for i in range(self.lookback, len(df)):
            bar = df.iloc[i]
            sub_df = full_df.iloc[: full_df.index.get_loc(df.index[i]) + 1]

            # Manage open trades (exit check + trail update)
            still_open = []
            for trade in open_trades:
                closed, reason = self._check_exit(trade, bar)
                if closed:
                    trade.exit_price = closed
                    trade.status = reason
                    trade.exit_idx = i
                    trade.pnl = self._calc_pnl(trade)
                    equity += trade.pnl
                    closed_trades.append(trade)
                else:
                    new_sl = self._trail_bar(trade, bar, sub_df)
                    if new_sl:
                        trade.sl = new_sl
                    still_open.append(trade)
            open_trades = still_open

            if len(open_trades) >= max_total:
                continue
            if len([t for t in open_trades if t.symbol == symbol]) >= max_pair:
                continue

            sig = self.strategies.run_all(sub_df)
            direction = sig["direction"]
            confluence = sig["confluence"]

            if direction == 0 or confluence < 40:
                continue

            if not self._check_htf_sim(sub_df, direction):
                continue

            side = "buy" if direction == 1 else "sell"
            buy_count = len([t for t in open_trades if t.side == "buy"])
            sell_count = len([t for t in open_trades if t.side == "sell"])
            if side == "buy" and buy_count >= max_buy:
                continue
            if side == "sell" and sell_count >= max_sell:
                continue

            features = self.scorer.extract_features(sub_df)
            features[9] = confluence / 100.0
            ml_score = self.scorer.score(features, direction, confluence)

            min_ml = self.cfg.get("min_ml_score", 55.0)
            if ml_score < min_ml:
                continue

            entry = float(bar["close"])
            sl, tp = self.risk_mgr.calculate_sl_tp(sub_df, side, entry)
            amount, dollar_risk = self.risk_mgr.calculate_position_size(
                equity, entry, sl, symbol
            )
            ok, _ = self.risk_mgr.validate_dollar_risk(entry, sl, amount)
            if not ok:
                continue

            trade = BTTrade(
                symbol=symbol,
                side=side,
                entry_price=entry,
                entry_idx=i,
                sl=sl,
                tp=tp,
                lot=amount,
                peak_price=entry,
                strategies=" ".join(sig["hits"][:5]),
                confluence=confluence,
                ml_score=ml_score,
                features=features.tolist(),
            )
            open_trades.append(trade)

        # Close remaining at last bar
        last_bar = df.iloc[-1]
        for trade in open_trades:
            trade.exit_price = float(last_bar["close"])
            trade.status = "timeout"
            trade.exit_idx = len(df) - 1
            trade.pnl = self._calc_pnl(trade)
            equity += trade.pnl
            closed_trades.append(trade)

        return closed_trades, equity

    # ─────────────────────────────────────────────────────────────
    # EXIT CHECK
    # ─────────────────────────────────────────────────────────────
    def _check_exit(self, trade: BTTrade, bar) -> Tuple[Optional[float], str]:
        h = float(bar["high"])
        l = float(bar["low"])
        if trade.side == "buy":
            if l <= trade.sl:
                return trade.sl, "sl"
            if trade.tp and h >= trade.tp:
                return trade.tp, "tp"
        else:
            if h >= trade.sl:
                return trade.sl, "sl"
            if trade.tp and l <= trade.tp:
                return trade.tp, "tp"
        return None, ""

    # ─────────────────────────────────────────────────────────────
    # TRAIL BAR — uses configured trail type (not hardcoded %)
    # ─────────────────────────────────────────────────────────────
    def _trail_bar(self, trade: BTTrade, bar, df: pd.DataFrame) -> Optional[float]:
        if not self.trail_cfg.get("enabled", True):
            return None

        trail_type = self.trail_cfg.get("type", "atr")
        price = float(bar["close"])

        # Update peak
        if trade.side == "buy" and price > trade.peak_price:
            trade.peak_price = price
        elif trade.side == "sell" and price < trade.peak_price:
            trade.peak_price = price

        if trail_type == "percent":
            pct = self.trail_cfg.get("percent", 1.5) / 100.0
            new_sl = price * (1 - pct) if trade.side == "buy" else price * (1 + pct)

        elif trail_type == "dollar":
            dollar = self.trail_cfg.get("dollar", 30.0)
            new_sl = price - dollar if trade.side == "buy" else price + dollar

        elif trail_type == "volatility":
            atr = self._bar_atr(df)
            if atr == 0:
                return None
            mult = self.trail_cfg.get("volatility_atr_mult", 1.5)
            new_sl = price - atr * mult if trade.side == "buy" else price + atr * mult

        elif trail_type == "time":
            atr = self._bar_atr(df)
            if atr == 0:
                return None
            # Tighten linearly over time_minutes
            bars_in_trade = getattr(trade, "_bt_bars", 0) + 1
            trade._bt_bars = bars_in_trade
            max_bars = self.trail_cfg.get("time_minutes", 60)  # treat as bars
            tighten = min(1.0, bars_in_trade / max_bars)
            dist = atr * self.trail_cfg.get("atr_multiplier", 2.0) * (1 - tighten * 0.5)
            new_sl = price - dist if trade.side == "buy" else price + dist

        else:  # ATR (default)
            atr = self._bar_atr(df)
            if atr == 0:
                return None
            mult = self.trail_cfg.get("atr_multiplier", 2.0)
            new_sl = price - atr * mult if trade.side == "buy" else price + atr * mult

        # Only move SL in favour
        if trade.side == "buy" and new_sl > trade.sl and new_sl < price:
            return new_sl
        if trade.side == "sell" and new_sl < trade.sl and new_sl > price:
            return new_sl
        return None

    def _bar_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        if df is None or len(df) < period + 1:
            return 0.0
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        v = tr.rolling(period).mean().iloc[-1]
        return float(v) if not np.isnan(v) else 0.0

    def _calc_pnl(self, trade: BTTrade) -> float:
        if trade.side == "buy":
            return (trade.exit_price - trade.entry_price) * trade.lot
        return (trade.entry_price - trade.exit_price) * trade.lot

    def _check_htf_sim(self, df: pd.DataFrame, direction: int) -> bool:
        if len(df) < 8:
            return True
        try:
            ds = df["close"].iloc[::4]
            ema = ds.ewm(span=20, adjust=False).mean()
            slope = ema.iloc[-1] - ema.iloc[-2]
            return (direction == 1 and slope > 0) or (direction == -1 and slope < 0)
        except:
            return True

    def _build_training_data(
        self, df: pd.DataFrame, symbol: str
    ) -> Tuple[np.ndarray, np.ndarray]:
        X, y = [], []
        for i in range(self.lookback, len(df) - 20):
            sub = df.iloc[: i + 1]
            try:
                sig = self.strategies.run_all(sub)
                if sig["direction"] == 0:
                    continue
                feat = self.scorer.extract_features(sub)
                feat[9] = sig["confluence"] / 100.0
                fut = df["close"].iloc[i + 1 : i + 11]
                entry = float(df["close"].iloc[i])
                if sig["direction"] == 1:
                    label = 1 if fut.max() > entry * 1.005 else 0
                else:
                    label = 1 if fut.min() < entry * 0.995 else 0
                X.append(feat)
                y.append(label)
            except:
                pass
        return (np.array(X) if X else np.zeros((0, 10))), np.array(y)

    def _compile_result(
        self, trades: List[BTTrade], equity: list, symbol: str, tf: str, init_cap: float
    ) -> BTResult:
        res = BTResult(symbol=symbol, timeframe=tf)
        res.total_trades = len(trades)
        # Always expose the equity curve (starts at initial capital) even when
        # a segment produced no trades.
        res.equity_curve = list(equity) if equity else [init_cap]
        if not trades:
            return res

        pnls = [t.pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        res.wins = len(wins)
        res.losses = len(losses)
        res.win_rate = len(wins) / len(trades) * 100
        res.total_pnl = sum(pnls)
        res.avg_win = np.mean(wins) if wins else 0
        res.avg_loss = abs(np.mean(losses)) if losses else 0
        res.profit_factor = (
            sum(wins) / abs(sum(losses))
            if losses and sum(losses) != 0
            else float("inf")
        )

        eq_arr = np.array(equity)
        peak = np.maximum.accumulate(eq_arr)
        dd = (peak - eq_arr) / np.maximum(peak, 1e-9)
        res.max_drawdown = float(dd.max() * 100)

        if len(eq_arr) > 1:
            rets = np.diff(eq_arr) / np.maximum(eq_arr[:-1], 1e-9)
            res.sharpe = float(rets.mean() / (rets.std() + 1e-9) * np.sqrt(252))

        res.equity_curve = equity
        res.trades = [
            {
                "symbol": t.symbol,
                "side": t.side,
                "entry": t.entry_price,
                "exit": t.exit_price,
                "sl": t.sl,
                "tp": t.tp,
                "pnl": round(t.pnl, 4),
                "status": t.status,
                "confluence": t.confluence,
                "ml_score": t.ml_score,
                "strategies": t.strategies,
            }
            for t in trades
        ]

        strat_wins: Dict[str, int] = {}
        for t in trades:
            if t.pnl > 0:
                for s in t.strategies.split():
                    strat_wins[s] = strat_wins.get(s, 0) + 1
        if strat_wins:
            res.best_strategy = max(strat_wins, key=strat_wins.get)

        logger.info(
            f"Backtest {symbol} {tf}: {res.total_trades} trades | "
            f"WR {res.win_rate:.1f}% | PnL ${res.total_pnl:.2f} | "
            f"MDD {res.max_drawdown:.1f}% | Sharpe {res.sharpe:.2f} | "
            f"PF {res.profit_factor:.2f}"
        )
        return res

    def _save_result(self, result: BTResult, symbol: str, tf: str):
        fname = f"backtest_{symbol.replace('/','_')}_{tf}.json"
        data = {
            "symbol": result.symbol,
            "timeframe": result.timeframe,
            "total_trades": result.total_trades,
            "wins": result.wins,
            "losses": result.losses,
            "win_rate": round(result.win_rate, 2),
            "total_pnl": round(result.total_pnl, 2),
            "max_drawdown": round(result.max_drawdown, 2),
            "sharpe": round(result.sharpe, 3),
            "profit_factor": round(result.profit_factor, 3),
            "avg_win": round(result.avg_win, 4),
            "avg_loss": round(result.avg_loss, 4),
            "best_strategy": result.best_strategy,
            "trades": result.trades,
        }
        with open(fname, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Backtest saved to {fname}")

    # ─────────────────────────────────────────────────────────────
    # LOAD SAVED BACKTEST WIN RATES (for manual trade SL/TP)
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def load_bt_win_rates(symbols: list, timeframes: list) -> Dict[str, float]:
        """
        Load saved backtest JSON files and return best win rate per symbol
        across all timeframes. Used by TradeManager for manual trade SL/TP.
        """
        win_rates: Dict[str, float] = {}
        for sym in symbols:
            best_wr = 0.0
            for tf in timeframes:
                fname = f"backtest_{sym.replace('/','_')}_{tf}.json"
                try:
                    with open(fname) as f:
                        data = json.load(f)
                    wr = float(data.get("win_rate", 0))
                    if wr > best_wr:
                        best_wr = wr
                except (FileNotFoundError, json.JSONDecodeError):
                    pass
            if best_wr > 0:
                win_rates[sym] = best_wr
        return win_rates
