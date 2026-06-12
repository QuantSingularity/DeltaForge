"""DeltaForge — DeltaForgeDisplay: 5-panel rich terminal dashboard."""

import os
import re
import time
from datetime import datetime
from typing import Dict, List

try:
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .event_log import (
    EVT_ANOMALY,
    EVT_BUY_SIGNAL,
    EVT_ENTRY,
    EVT_EXIT_LOSS,
    EVT_EXIT_WIN,
    EVT_HTF_REJECT,
    EVT_INFO,
    EVT_ML_REJECT,
    EVT_SELL_SIGNAL,
    EVT_TRAIL,
    EVT_WARN,
    EventLog,
)


class DeltaForgeDisplay:
    """
    Live terminal dashboard.
    Sections:
      ┌─ Header ──────────────────────────────────────────────┐
      │  Bot name / exchange / status / uptime / session PnL │
      ├─ Signal Analysis ─────────────────────────────────────┤
      │  TF | Symbol | Dir | Conf | ML% | Prob | SL | TP      │
      ├─ Open Trades ─────────────────────────────────────────┤
      │  Symbol | Side | Entry | Cur | SL | TP | Trail | PnL  │
      ├─ Risk Dashboard ──────────────────────────────────────┤
      │  Exposure | Unrealized | Session PnL | Per-trade risk │
      └─ Event Log (last 12 events, color-coded) ─────────────┘
    """

    MAX_LOG = 14

    def __init__(self, config: dict):
        self._plain = not RICH_AVAILABLE
        if not RICH_AVAILABLE:
            print(
                "[DeltaForge] Install 'rich' for the full dashboard: pip install rich"
            )
        self.console = Console() if RICH_AVAILABLE else None
        self.cfg = config

        # Pull color config (fall back to sensible defaults)
        dc = config.get("display", {})
        self.c_buy = dc.get("buy_color", "green")
        self.c_sell = dc.get("sell_color", "red")
        self.c_neutral = dc.get("neutral_color", "yellow")
        self.c_sl = dc.get("sl_color", "orange_red1")
        self.c_tp = dc.get("tp_color", "dodger_blue1")
        self.c_trail = dc.get("trail_color", "dark_orange")
        self.c_entry = dc.get("entry_color", "bright_green")
        self.c_exit = dc.get("exit_color", "bright_red")
        self.c_risk = dc.get("risk_color", "magenta")

        self._bot_running = True
        self._signals: Dict[str, dict] = {}  # tf  -> signal_data
        self._trades: List[dict] = []
        self._log = EventLog()
        self._stats: dict = {}
        self._exchange = config.get("exchange", {}).get("id", "?")
        self._start_time = time.time()

    # ─────────────────────────────────────────────────────────────
    # PUBLIC UPDATE API
    # ─────────────────────────────────────────────────────────────
    def set_bot_status(self, running: bool, reason: str = ""):
        self._bot_running = running
        msg = f"BOT {'STARTED' if running else 'STOPPED'}"
        msg += f": {reason}" if reason else ""
        self._add_event(EVT_INFO if running else EVT_WARN, msg)

    def update_signal(
        self,
        symbol: str,
        timeframe: str,
        direction: int,
        confluence: float,
        ml_score: float,
        probability: float,
        sl: float,
        tp: float,
        strategies: List[str],
    ):
        self._signals[timeframe] = {
            "symbol": symbol,
            "direction": direction,
            "confluence": confluence,
            "ml_score": ml_score,
            "probability": probability,
            "sl": sl,
            "tp": tp,
            "strategies": strategies,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
        # Log non-neutral signals as events
        if direction == 1:
            self._add_event(
                EVT_BUY_SIGNAL,
                f"BUY signal {symbol}/{timeframe} | Conf:{confluence:.0f}% "
                f"ML:{ml_score:.0f}% Prob:{probability:.0f}%",
            )
        elif direction == -1:
            self._add_event(
                EVT_SELL_SIGNAL,
                f"SELL signal {symbol}/{timeframe} | Conf:{confluence:.0f}% "
                f"ML:{ml_score:.0f}% Prob:{probability:.0f}%",
            )

    def update_trades(self, trades: List[dict]):
        self._trades = trades

    def update_stats(self, stats: dict):
        self._stats = stats

    def log_entry(
        self,
        symbol: str,
        side: str,
        entry: float,
        sl: float,
        tp: float,
        amount: float,
        ml_score: float,
        tf: str,
    ):
        """Record a trade entry event."""
        self._add_event(
            EVT_ENTRY,
            f"ENTRY {side.upper()} {symbol} @ {entry:.6f} | "
            f"SL:{sl:.6f} TP:{tp:.6f} | Qty:{amount:.4f} ML:{ml_score:.0f}% [{tf}]",
        )

    def log_exit(
        self, symbol: str, side: str, exit_price: float, pnl: float, reason: str = ""
    ):
        """Record a trade exit event."""
        evt = EVT_EXIT_WIN if pnl >= 0 else EVT_EXIT_LOSS
        tag = f"({reason})" if reason else ""
        self._add_event(
            evt,
            f"EXIT {side.upper()} {symbol} @ {exit_price:.6f} | "
            f"PnL:${pnl:+.2f} {tag}",
        )

    def log_trail_update(self, symbol: str, side: str, old_sl: float, new_sl: float):
        """Record a trailing stop movement event."""
        direction = "▲" if new_sl > old_sl else "▼"
        self._add_event(
            EVT_TRAIL,
            f"TRAIL {direction} {symbol} {side.upper()} | "
            f"SL: {old_sl:.6f} → {new_sl:.6f}",
        )

    def log(self, message: str, color: str = "white"):
        """Generic log (legacy interface compatibility)."""
        self._add_event(EVT_INFO, message, _color_override=color)

    # ─────────────────────────────────────────────────────────────
    # INTERNAL EVENT STORE
    # ─────────────────────────────────────────────────────────────
    def _add_event(self, evt_type: str, message: str, _color_override: str = ""):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log._events.append(
            {
                "type": evt_type,
                "msg": message,
                "ts": ts,
                "color_override": _color_override,
            }
        )
        if len(self._log._events) > self.MAX_LOG:
            self._log._events.pop(0)

    def _event_color(self, evt: dict) -> str:
        if evt.get("color_override"):
            return evt["color_override"]
        t = evt["type"]
        return {
            EVT_BUY_SIGNAL: self.c_buy,
            EVT_SELL_SIGNAL: self.c_sell,
            EVT_ENTRY: self.c_entry,
            EVT_EXIT_WIN: self.c_buy,
            EVT_EXIT_LOSS: self.c_exit,
            EVT_TRAIL: self.c_trail,
            EVT_HTF_REJECT: self.c_neutral,
            EVT_ML_REJECT: self.c_neutral,
            EVT_ANOMALY: "bold red",
            EVT_INFO: "white",
            EVT_WARN: "yellow",
        }.get(t, "white")

    # ─────────────────────────────────────────────────────────────
    # RENDER
    # ─────────────────────────────────────────────────────────────
    def render(self) -> str:
        if self._plain:
            self._plain_render()
            return ""
        self.console.clear()
        self._print_header()
        self._print_signals()
        self._print_trades()
        self._print_risk_dashboard()
        self._print_event_log()
        return ""

    # ─────────────────────────────────────────────────────────────
    # SECTION: HEADER
    # ─────────────────────────────────────────────────────────────
    def _print_header(self):
        sc = self.c_buy if self._bot_running else self.c_sell
        stxt = "● RUNNING" if self._bot_running else "● STOPPED"
        uptime = int(time.time() - self._start_time)
        h, m, s = uptime // 3600, (uptime % 3600) // 60, uptime % 60

        header = Text()
        header.append("  DeltaForge Agentic AI Bot v1.1", style="bold cyan")
        header.append(f"   [{self._exchange.upper()}]", style="bold yellow")
        header.append("   Status: ", style="white")
        header.append(stxt, style=f"bold {sc}")
        header.append(f"   Up: {h:02d}:{m:02d}:{s:02d}", style="dim white")
        header.append(
            f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim white"
        )

        total_pnl = self._stats.get("total_pnl", 0)
        pc = self.c_buy if total_pnl >= 0 else self.c_sell
        header.append("   Session PnL: ", style="white")
        header.append(f"${total_pnl:+.2f}", style=f"bold {pc}")

        trades_count = self._stats.get("total_trades", 0)
        header.append(f"   Trades: {trades_count}", style="dim white")

        self.console.print(
            Panel(
                header,
                border_style="cyan",
                title="[bold cyan]DeltaForge — In-House Use Only[/]",
            )
        )

    # ─────────────────────────────────────────────────────────────
    # SECTION: SIGNAL ANALYSIS
    # ─────────────────────────────────────────────────────────────
    def _print_signals(self):
        table = Table(
            title="Signal Analysis", border_style="blue", show_lines=True, expand=True
        )
        table.add_column("TF", style="bold white", width=5)
        table.add_column("Symbol", style="cyan", width=12)
        table.add_column("Direction", justify="center", width=8)
        table.add_column("Confluence", justify="right", width=12)
        table.add_column("ML Score", justify="right", width=10)
        table.add_column("Probability", justify="right", width=12)
        table.add_column("Sugg. SL", justify="right", width=14)
        table.add_column("Sugg. TP", justify="right", width=14)
        table.add_column("Updated", justify="right", width=10)
        table.add_column("Active Strategies", style="dim", min_width=30)

        for tf in ("15m", "1h", "4h", "1d"):
            sig = self._signals.get(tf)
            if not sig:
                table.add_row(tf, "—", "WAITING", "—", "—", "—", "—", "—", "—", "—")
                continue

            d = sig["direction"]
            d_txt = Text("  BUY  " if d == 1 else ("  SELL " if d == -1 else "  WAIT "))
            d_txt.stylize(
                f"bold {self.c_buy}"
                if d == 1
                else (f"bold {self.c_sell}" if d == -1 else self.c_neutral)
            )

            ml = sig["ml_score"]
            ml_t = Text(f"{ml:.1f}%")
            ml_t.stylize(
                "bold green" if ml >= 70 else ("yellow" if ml >= 50 else "red")
            )

            prob = sig["probability"]
            pr_t = Text(f"{prob:.1f}%")
            pr_t.stylize(
                "bold green" if prob >= 65 else ("yellow" if prob >= 50 else "red")
            )

            conf = sig["confluence"]
            cf_t = Text(f"{conf:.1f}%")
            cf_t.stylize("green" if conf >= 60 else ("yellow" if conf >= 40 else "red"))

            sl_val = sig["sl"]
            tp_val = sig["tp"]
            sl_t = Text(f"{sl_val:.6f}" if sl_val else "—")
            tp_t = Text(f"{tp_val:.6f}" if tp_val else "—")
            sl_t.stylize(self.c_sl)
            tp_t.stylize(self.c_tp)

            strats = " ".join(sig["strategies"][:7])
            table.add_row(
                tf,
                sig["symbol"],
                d_txt,
                cf_t,
                ml_t,
                pr_t,
                sl_t,
                tp_t,
                sig["time"],
                strats,
            )
        self.console.print(table)

    # ─────────────────────────────────────────────────────────────
    # SECTION: OPEN TRADES
    # ─────────────────────────────────────────────────────────────
    def _print_trades(self):
        if not self._trades:
            self.console.print(
                Panel(
                    Align.center("[dim]No open trades[/dim]"),
                    title="Open Trades",
                    border_style="green",
                )
            )
            return

        table = Table(
            title=f"Open Trades ({len(self._trades)})",
            border_style="green",
            show_lines=True,
            expand=True,
        )
        table.add_column("Symbol", style="cyan", width=12)
        table.add_column("Side", justify="center", width=6)
        table.add_column("Entry", justify="right", width=14)
        table.add_column("Current", justify="right", width=14)
        table.add_column("SL", justify="right", width=14)
        table.add_column("TP", justify="right", width=14)
        table.add_column("Trail▲", justify="center", width=7)
        table.add_column("Amount", justify="right", width=10)
        table.add_column("uPnL", justify="right", width=10)
        table.add_column("TF", width=5)
        table.add_column("ML%", justify="right", width=6)

        for t in self._trades:
            side = t.get("side", "")
            st = Text(f" {side.upper()} ")
            st.stylize(f"bold {self.c_buy}" if side == "buy" else f"bold {self.c_sell}")

            upnl = t.get("unrealized_pnl", 0)
            pnl_t = Text(f"${upnl:+.2f}")
            pnl_t.stylize(self.c_buy if upnl >= 0 else self.c_sell)

            sl_t = Text(f"{t.get('sl', 0):.6f}")
            tp_t = Text(f"{t.get('tp', 0):.6f}" if t.get("tp") else "—")
            sl_t.stylize(self.c_sl)
            tp_t.stylize(self.c_tp)

            # Trail indicator: show arrow if trail recently moved
            trail_moved = t.get("trail_updated", False)
            trail_txt = Text("▲ YES" if trail_moved else "—")
            trail_txt.stylize(self.c_trail if trail_moved else "dim white")

            table.add_row(
                t.get("symbol", ""),
                st,
                f"{t.get('entry_price', 0):.6f}",
                f"{t.get('current_price', 0):.6f}",
                sl_t,
                tp_t,
                trail_txt,
                f"{t.get('amount', 0):.4f}",
                pnl_t,
                t.get("timeframe", ""),
                f"{t.get('ml_score', 0):.0f}",
            )
        self.console.print(table)

    # ─────────────────────────────────────────────────────────────
    # SECTION: RISK DASHBOARD  (new — required by PDF)
    # ─────────────────────────────────────────────────────────────
    def _print_risk_dashboard(self):
        rs = self._stats.get("risk_summary", {})
        if not rs and not self._trades:
            return

        # Compute from live trades if no explicit summary
        total_exposure = rs.get(
            "total_exposure",
            sum(t.get("amount", 0) * t.get("current_price", 0) for t in self._trades),
        )
        unrealized_pnl = rs.get(
            "unrealized_pnl", sum(t.get("unrealized_pnl", 0) for t in self._trades)
        )
        session_pnl = self._stats.get("total_pnl", 0)
        open_count = rs.get("open_positions", len(self._trades))
        max_single_risk = rs.get("max_single_risk", 0)
        avg_ml = rs.get("avg_ml_score", 0)
        max_drawdown = rs.get("session_drawdown", 0)
        total_trades = self._stats.get("total_trades", 0)

        # Color helpers
        pnl_c = self.c_buy if session_pnl >= 0 else self.c_sell
        upnl_c = self.c_buy if unrealized_pnl >= 0 else self.c_sell
        dd_c = (
            "green"
            if max_drawdown <= 5
            else ("yellow" if max_drawdown <= 15 else "red")
        )

        table = Table(
            title="Risk Dashboard",
            border_style=self.c_risk,
            show_lines=False,
            expand=True,
            show_header=False,
        )
        table.add_column("Metric", style=f"bold {self.c_risk}", width=24)
        table.add_column("Value", justify="left", min_width=16)
        table.add_column("Metric2", style=f"bold {self.c_risk}", width=24)
        table.add_column("Value2", justify="left", min_width=16)

        def mk(v, c):
            t = Text(str(v))
            t.stylize(c)
            return t

        table.add_row(
            "Open Positions",
            mk(open_count, "white"),
            "Session Trades",
            mk(total_trades, "white"),
        )
        table.add_row(
            "Total Exposure",
            mk(f"${total_exposure:,.2f}", "white"),
            "Max Single Risk",
            mk(f"${max_single_risk:.2f}", "yellow"),
        )
        table.add_row(
            "Unrealized PnL",
            mk(f"${unrealized_pnl:+.2f}", upnl_c),
            "Session PnL",
            mk(f"${session_pnl:+.2f}", pnl_c),
        )
        table.add_row(
            "Session Drawdown",
            mk(f"{max_drawdown:.1f}%", dd_c),
            "Avg ML Score",
            mk(f"{avg_ml:.1f}%", "white"),
        )
        self.console.print(table)

    # ─────────────────────────────────────────────────────────────
    # SECTION: EVENT LOG  (typed + color-coded)
    # ─────────────────────────────────────────────────────────────
    def _print_event_log(self):
        if not self._log._events:
            return

        # Event type labels (fixed-width prefix)
        labels = {
            EVT_BUY_SIGNAL: f"[bold {self.c_buy}][BUY SIG ][/]",
            EVT_SELL_SIGNAL: f"[bold {self.c_sell}][SELL SIG][/]",
            EVT_ENTRY: f"[bold {self.c_entry}][ENTRY   ][/]",
            EVT_EXIT_WIN: f"[bold {self.c_buy}][EXIT WIN][/]",
            EVT_EXIT_LOSS: f"[bold {self.c_exit}][EXIT LOS][/]",
            EVT_TRAIL: f"[bold {self.c_trail}][TRAIL   ][/]",
            EVT_HTF_REJECT: f"[{self.c_neutral}][HTF REJ ][/]",
            EVT_ML_REJECT: f"[{self.c_neutral}][ML  REJ ][/]",
            EVT_ANOMALY: "[bold red][ANOMALY ][/]",
            EVT_INFO: "[dim white][INFO    ][/]",
            EVT_WARN: "[yellow][WARNING ][/]",
        }

        lines = []
        for ev in self._log._events[-self.MAX_LOG :]:
            t = ev["type"]
            col = self._event_color(ev)
            lbl = labels.get(t, "[dim][INFO    ][/]")
            msg = ev["msg"]
            ts = ev["ts"]
            lines.append(f"{lbl} [{col}]{ts}  {msg}[/{col}]")

        log_str = "\n".join(lines)
        self.console.print(
            Panel(
                log_str,
                title="Event Log",
                border_style="dim white",
                padding=(0, 1),
            )
        )

    # ─────────────────────────────────────────────────────────────
    # PLAIN TEXT FALLBACK
    # ─────────────────────────────────────────────────────────────
    def _plain_render(self):
        os.system("cls" if os.name == "nt" else "clear")
        running = "RUNNING" if self._bot_running else "STOPPED"
        print(f"\n{'='*70}")
        print(
            f"  DeltaForge AI Bot v1.1  [{self._exchange.upper()}]  Status: {running}"
        )
        print(
            f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            f"  Session PnL: ${self._stats.get('total_pnl', 0):+.2f}"
        )
        print(f"{'='*70}")
        for tf in ("15m", "1h", "4h", "1d"):
            sig = self._signals.get(tf)
            if not sig:
                print(f"  {tf:4s}: WAITING")
                continue
            d = sig["direction"]
            ds = "BUY" if d == 1 else ("SELL" if d == -1 else "WAIT")
            print(
                f"  {tf:4s}: {ds:4s} | Conf:{sig['confluence']:.0f}% "
                f"| ML:{sig['ml_score']:.0f}% | Prob:{sig['probability']:.0f}% "
                f"| SL:{sig['sl']:.6f} | TP:{sig['tp']:.6f}"
            )
        print()
        for t in self._trades:
            upnl = t.get("unrealized_pnl", 0)
            print(
                f"  {t['symbol']} {t['side'].upper()} | "
                f"Entry:{t['entry_price']:.6f} Cur:{t['current_price']:.6f} "
                f"SL:{t['sl']:.6f} TP:{t.get('tp',0):.6f} uPnL:${upnl:+.2f}"
            )
        print()
        for ev in self._log._events[-8:]:
            clean = re.sub(r"\[/?[^\]]*\]", "", ev.get("msg", ""))
            print(f"  [{ev['ts']}] {ev['type']:12s} {clean}")

    # ─────────────────────────────────────────────────────────────
    # BACKTEST REPORT
    # ─────────────────────────────────────────────────────────────
    def print_backtest_result(self, result):
        if self._plain:
            print(f"\nBacktest: {result.symbol} {result.timeframe}")
            print(f"  Trades:{result.total_trades}  WR:{result.win_rate:.1f}%")
            print(f"  PnL:${result.total_pnl:.2f}  MDD:{result.max_drawdown:.1f}%")
            print(f"  Sharpe:{result.sharpe:.2f}  PF:{result.profit_factor:.2f}")
            return

        table = Table(
            title=f"Backtest — {result.symbol} {result.timeframe}",
            border_style="yellow",
            show_lines=True,
        )
        table.add_column("Metric", style="bold white")
        table.add_column("Value", justify="right")

        def row(k, v, c="white"):
            t = Text(str(v))
            t.stylize(c)
            table.add_row(k, t)

        row("Total Trades", result.total_trades)
        row(
            "Win Rate",
            f"{result.win_rate:.1f}%",
            "green" if result.win_rate >= 55 else "red",
        )
        row(
            "Total PnL",
            f"${result.total_pnl:.2f}",
            "green" if result.total_pnl >= 0 else "red",
        )
        row(
            "Max Drawdown",
            f"{result.max_drawdown:.1f}%",
            "green" if result.max_drawdown <= 15 else "red",
        )
        row(
            "Sharpe Ratio",
            f"{result.sharpe:.2f}",
            "green" if result.sharpe >= 1 else "yellow",
        )
        row(
            "Profit Factor",
            f"{result.profit_factor:.2f}",
            "green" if result.profit_factor >= 1.5 else "red",
        )
        row("Avg Win", f"${result.avg_win:.4f}")
        row("Avg Loss", f"${result.avg_loss:.4f}")
        row("Best Strategy", result.best_strategy, "cyan")

        self.console.print(table)
