"""DeltaForge - Position sizing and dollar-risk validation."""

import logging
from typing import Optional, Tuple

import pandas as pd

logger = logging.getLogger("DeltaForge.PositionSizer")


class PositionSizer:
    """Computes lot size from balance, entry, and SL."""

    def calculate_position_size(
        self,
        balance_usdt: float,
        entry_price: float,
        sl_price: float,
        symbol: str = "BTC/USDT",
    ) -> Tuple[float, float]:
        r = self.risk_cfg
        risk_pct = r.get("risk_percent", 1.0) / 100.0
        max_dollar = r.get("max_loss_per_trade", 50.0)
        max_dollar_amt = r.get("max_dollar_amount_crypto", 10000.0)

        dollar_risk = min(balance_usdt * risk_pct, max_dollar)

        sl_dist_pct = abs(entry_price - sl_price) / entry_price
        if sl_dist_pct == 0:
            logger.warning("SL == entry price, using 1% SL distance")
            sl_dist_pct = 0.01

        position_usdt = min(dollar_risk / sl_dist_pct, max_dollar_amt)
        amount_base = position_usdt / entry_price

        logger.debug(
            f"Position size: ${position_usdt:.2f} | "
            f"{amount_base:.6f} base | Risk: ${dollar_risk:.2f}"
        )
        return amount_base, dollar_risk

    # ─────────────────────────────────────────────────────────────
    # SL / TP CALCULATION
    # ─────────────────────────────────────────────────────────────

    def validate_dollar_risk(
        self, entry_price: float, sl_price: float, amount: float
    ) -> Tuple[bool, float]:
        max_loss = self.risk_cfg.get("max_loss_per_trade", 50.0)
        sl_dist = abs(entry_price - sl_price)
        dollar_risk = sl_dist * amount
        ok = dollar_risk <= max_loss
        if not ok:
            logger.warning(
                f"Dollar risk ${dollar_risk:.2f} exceeds max ${max_loss:.2f}"
            )
        return ok, dollar_risk

    # ─────────────────────────────────────────────────────────────
    # RISK SUMMARY  (for display Risk Dashboard panel)
    # ─────────────────────────────────────────────────────────────

    def _compute_atr(self, df: Optional[pd.DataFrame], period: int = 14) -> float:
        if df is None or len(df) < period + 1:
            return 0.0
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    def max_dollar_crypto(self) -> float:
        return self.risk_cfg.get("max_dollar_amount_crypto", 10000.0)

    def tp_enabled(self) -> bool:
        return self.risk_cfg.get("take_profit_enabled", True)
