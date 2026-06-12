# DeltaForge - Infrastructure

MetaTrader platform integrations for Forex trading.

## MetaTrader 5 (MQL5)

```
mql5/
├── DeltaForge_EA.mq5          # Main Expert Advisor
└── Include/
    ├── Strategies.mqh         # 26 strategy implementations
    ├── RiskManager.mqh        # Position sizing, SL/TP, trail stops
    ├── MLFilter.mqh           # ML signal scoring
    └── DisplayPanel.mqh       # On-chart display panel
```

**Setup:**

1. Copy `mql5/DeltaForge_EA.mq5` → `<MT5 Data>/MQL5/Experts/`
2. Copy `mql5/Include/*.mqh` → `<MT5 Data>/MQL5/Include/`
3. Compile in MetaEditor (F7)
4. Attach to chart and configure inputs

## MetaTrader 4 (MQL4)

```
mql4/
└── DeltaForge_EA.mq4          # Single-file EA with all 26 strategies inline
```

**Setup:**

1. Copy `mql4/DeltaForge_EA.mq4` → `<MT4 Data>/MQL4/Experts/`
2. Compile in MetaEditor (F7)
3. Attach to chart — panel appears automatically

## Supported Timeframes

`M15` · `H1` · `H4` · `D1`

## Trail Stop Types (all 5 implemented in both EAs)

| Type            | MT5/MQL5           | MT4/MQL4         |
| --------------- | ------------------ | ---------------- |
| ATR             | `TRAIL_ATR`        | `InpTrailType=0` |
| Percentage      | `TRAIL_PERCENT`    | `InpTrailType=1` |
| Dollar          | `TRAIL_DOLLAR`     | `InpTrailType=2` |
| Time-tightening | `TRAIL_TIME`       | `InpTrailType=3` |
| Volatility      | `TRAIL_VOLATILITY` | `InpTrailType=4` |
