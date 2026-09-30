"""
DeltaForge StrategyEngine - composes all 26 strategy mixins into one class.
Imports from subdirectory modules; handles run_all() voting logic.
"""

import logging
from typing import Dict

import pandas as pd

from .advanced.strategies import AdvancedStrategies
from .indicators import SIGNAL_BUY, SIGNAL_NONE, SIGNAL_SELL
from .momentum.strategies import MomentumStrategies
from .price_action.strategies import PriceActionStrategies
from .trend.strategies import TrendStrategies
from .volatility.strategies import VolatilityStrategies
from .volume.strategies import VolumeStrategies

logger = logging.getLogger("DeltaForge.Strategies")


class StrategyEngine(
    TrendStrategies,
    MomentumStrategies,
    VolatilityStrategies,
    VolumeStrategies,
    PriceActionStrategies,
    AdvancedStrategies,
):
    """
    All 26 strategies composed via multiple inheritance from category mixins.
    Call run_all(df) → dict with direction, confluence, votes, hits.
    """

    STRATEGY_MAP = {
        # Trend Following (7)
        "ma_cross": "ma_cross",
        "ema_trend": "ema_trend",
        "macd": "macd_strategy",
        "adx": "adx_filter",
        "parabolic_sar": "parabolic_sar",
        "ichimoku": "ichimoku",
        "trendline": "trendline",
        # Momentum (4)
        "rsi": "rsi_strategy",
        "stochastic": "stochastic",
        "momentum": "momentum",
        "bollinger_bands": "bollinger_bands",
        # Volatility (2)
        "atr_breakout": "atr_breakout",
        "breakout": "breakout",
        # Volume & Money Flow (4)
        "accum_dist": "accum_dist",
        "chaikin_mf": "chaikin_mf",
        "volume_breakout": "volume_breakout",
        "pullback": "pullback",
        # Price Action (4)
        "fibonacci": "fibonacci",
        "pivot_points": "pivot_points",
        "support_resist": "support_resistance",
        # Advanced (5)
        "smc": "smart_money_concepts",
        "order_flow": "order_flow",
        "market_profile": "market_profile",
        "lux_algo": "lux_algo",
        "news_momentum": "news_momentum",
        "quant_algo": "quant_algo",
    }

    def __init__(self, config: dict):
        self.cfg = config
        self.strategies_enabled = config.get("strategies", {})

    def run_all(self, df: pd.DataFrame) -> Dict:
        results = {}
        buy_v = sell_v = total = 0
        hits = []

        for cfg_key, method_name in self.STRATEGY_MAP.items():
            if not self.strategies_enabled.get(cfg_key, True):
                continue
            method = getattr(self, method_name, None)
            if method is None:
                continue
            try:
                sig, conf, note = method(df)
                results[cfg_key] = {"signal": sig, "confidence": conf, "note": note}
                total += 1
                if sig == SIGNAL_BUY:
                    buy_v += 1
                    hits.append(f"{cfg_key}(B)")
                elif sig == SIGNAL_SELL:
                    sell_v += 1
                    hits.append(f"{cfg_key}(S)")
            except Exception as e:
                logger.debug(f"Strategy {cfg_key} error: {e}")

        direction = SIGNAL_NONE
        confluence = 0.0
        if total > 0:
            if buy_v > sell_v and buy_v / total >= 0.40:
                direction = SIGNAL_BUY
                confluence = buy_v / total * 100
            elif sell_v > buy_v and sell_v / total >= 0.40:
                direction = SIGNAL_SELL
                confluence = sell_v / total * 100

        return {
            "signals": results,
            "direction": direction,
            "votes_buy": buy_v,
            "votes_sell": sell_v,
            "total": total,
            "confluence": confluence,
            "hits": hits,
        }
