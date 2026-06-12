//+------------------------------------------------------------------+
//|                                              DeltaForge_EA.mq5       |
//|                        DeltaForge Agentic AI Trading System v1.0     |
//|                                     https://deltaforge.tech          |
//+------------------------------------------------------------------+
#property copyright   "DeltaForge Trading Systems"
#property link        "https://deltaforge.tech"
#property version     "1.00"
#property description "DeltaForge Multi-Strategy Agentic AI EA with ML Signal Scoring"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\OrderInfo.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\HistoryOrderInfo.mqh>
#include "Include\Strategies.mqh"
#include "Include\RiskManager.mqh"
#include "Include\DisplayPanel.mqh"
#include "Include\MLFilter.mqh"

//+------------------------------------------------------------------+
//| BOT CONTROL                                                       |
//+------------------------------------------------------------------+
input group "=== BOT CONTROL ==="
input bool     InpBotRunning           = true;            // Start Bot Running
input bool     InpAutoStopOnAnomaly    = true;            // Auto-Stop on Market Anomaly

//+------------------------------------------------------------------+
//| STRATEGY SELECTION                                                |
//+------------------------------------------------------------------+
input group "=== STRATEGY SELECTION ==="
input bool     Strat_MA_Cross          = true;            // Moving Average Crossover
input bool     Strat_EMA_Trend         = true;            // EMA Trend Following
input bool     Strat_MACD              = true;            // MACD Strategy
input bool     Strat_ADX_Filter        = true;            // ADX Trend Strength Filter
input bool     Strat_ParabolicSAR      = true;            // Parabolic SAR
input bool     Strat_RSI               = true;            // RSI Overbought/Oversold
input bool     Strat_Stochastic        = true;            // Stochastic Oscillator
input bool     Strat_Momentum          = true;            // Momentum Indicator
input bool     Strat_BollingerBands    = true;            // Bollinger Bands Reversal
input bool     Strat_ATR_Breakout      = true;            // ATR Volatility Breakout
input bool     Strat_AccumDist         = true;            // Accumulation/Distribution
input bool     Strat_ChaikinMF         = true;            // Chaikin Money Flow
input bool     Strat_Fibonacci         = true;            // Fibonacci Retracement
input bool     Strat_PivotPoints       = true;            // Pivot Points
input bool     Strat_SupportResist     = true;            // Support & Resistance Zones
input bool     Strat_Ichimoku          = true;            // Ichimoku Cloud Strategy
input bool     Strat_Breakout          = true;            // Breakout Trading
input bool     Strat_Trendline         = true;            // Trendline Trading
input bool     Strat_VolumeBreakout    = true;            // Volume Breakout
input bool     Strat_Pullback          = true;            // Pullback Trading
input bool     Strat_SMC               = true;            // Smart Money Concepts (SMC)
input bool     Strat_OrderFlow         = true;            // Order Flow / Liquidity
input bool     Strat_MarketProfile     = true;            // Market Profile / VAH/VAL
// ── Advanced Strategies ──────────────────────────────────────────────
input bool     Strat_LuxAlgo           = true;            // LuxAlgo RSI Divergence + EMA Ribbon
input bool     Strat_NewsMomentum      = true;            // News Momentum (Impulse + Volume)
input bool     Strat_QuantAlgo         = true;            // Quantitative Z-Score Mean Reversion

//+------------------------------------------------------------------+
//| RISK MANAGEMENT                                                   |
//+------------------------------------------------------------------+
input group "=== RISK MANAGEMENT ==="
input double   InpMaxLossPerTrade      = 50.0;            // Max Loss Per Trade ($)
input double   InpMaxLotSize           = 1.0;             // Maximum Lot Size Allowed
input int      InpMaxTotalOrders       = 10;              // Max Total Open Orders
input int      InpMaxOrdersPerPair     = 2;               // Max Orders Per Pair
input int      InpMaxBuyOrders         = 5;               // Maximum Buy Orders
input int      InpMaxSellOrders        = 5;               // Maximum Sell Orders
input double   InpRiskPercent          = 1.0;             // Risk % Per Trade
input double   InpMinMLScore           = 60.0;            // Min ML Signal Score (0-100)

//+------------------------------------------------------------------+
//| STOP LOSS CONFIGURATION                                           |
//+------------------------------------------------------------------+
input group "=== STOP LOSS ==="
input bool     InpTrailStopEnabled     = true;            // Trail Stop ON/OFF
input ENUM_TRAIL_TYPE InpTrailType     = TRAIL_ATR;       // Trail Stop Type
input double   InpTrailPercent         = 1.5;             // Trail Stop % (percentage-based)
input double   InpTrailDollar          = 30.0;            // Trail Stop $ (dollar-based)
input int      InpTrailTimeMins        = 60;              // Time Trail: bars until max tighten
input double   InpVolatilityMult       = 1.5;             // Volatility Trail: ATR multiplier
input double   InpATRMultiplier        = 2.0;             // ATR Multiplier (volatility-based)
input int      InpTimeTrailMinutes     = 60;              // Time-Based Trail (minutes)
input double   InpTrailModLotTrigger   = 0.5;             // Trail Modify Trigger (lot fraction)
input int      InpATRPeriod            = 14;              // ATR Period

//+------------------------------------------------------------------+
//| TAKE PROFIT CONFIGURATION                                         |
//+------------------------------------------------------------------+
input group "=== TAKE PROFIT ==="
input bool     InpTakeProfitEnabled    = true;            // Take Profit ON/OFF
input double   InpTPRiskReward         = 2.0;             // TP Risk:Reward Ratio
input bool     InpTPFromBacktest       = true;            // Use Backtested TP Levels

//+------------------------------------------------------------------+
//| SCAN INTERVALS (seconds)                                          |
//+------------------------------------------------------------------+
input group "=== SCAN INTERVALS ==="
input int      InpScan15M              = 2100;            // 15-Min Scan Interval (secs) [35 min]
input int      InpScan1H               = 3600;            // 1-Hour Scan Interval (secs)
input int      InpScan4H               = 14400;           // 4-Hour Scan Interval (secs)
input int      InpScan1D               = 86400;           // 1-Day Scan Interval (secs)

//+------------------------------------------------------------------+
//| HIGHER TIMEFRAME CONFIRMATION                                     |
//+------------------------------------------------------------------+
input group "=== HTF CONFIRMATION ==="
input bool     InpRequireBothHTF       = false;           // Require BOTH higher TFs aligned
input bool     InpHTFConfirmEnabled    = true;            // HTF Confirmation ON/OFF

//+------------------------------------------------------------------+
//| DISPLAY                                                           |
//+------------------------------------------------------------------+
input group "=== DISPLAY ==="
input int      InpPanelX               = 10;              // Panel X Position
input int      InpPanelY               = 30;              // Panel Y Position
input bool     InpShowProbability      = true;            // Show Trade Probability
input bool     InpShowAllSignals       = true;            // Show All Strategy Signals
input color    InpBuyColor             = clrLime;         // Buy Signal Color
input color    InpSellColor            = clrRed;          // Sell Signal Color
input color    InpNeutralColor         = clrGray;         // Neutral/Pending Color
input color    InpSLColor              = clrOrangeRed;    // Stop Loss Line Color
input color    InpTPColor              = clrDodgerBlue;   // Take Profit Line Color

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
CTrade         Trade;
CPositionInfo  PosInfo;
COrderInfo     OrdInfo;

bool           g_BotRunning;
datetime       g_LastScan15M;
datetime       g_LastScan1H;
datetime       g_LastScan4H;
datetime       g_LastScan1D;

// The 4 locked timeframes
ENUM_TIMEFRAMES g_Timeframes[4] = {PERIOD_M15, PERIOD_H1, PERIOD_H4, PERIOD_D1};
string         g_Symbol;
int            g_MagicNumber = 20250001;

CDisplayPanel* g_Panel;
CMLFilter*     g_ML;
CRiskManager*  g_Risk;
CStrategies*   g_Strategies;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   g_Symbol     = Symbol();
   g_BotRunning = InpBotRunning;

   // Initialize modules
   g_Risk       = new CRiskManager(InpMaxLossPerTrade, InpMaxLotSize,
                                    InpMaxTotalOrders, InpMaxOrdersPerPair,
                                    InpMaxBuyOrders, InpMaxSellOrders,
                                    InpRiskPercent);

   g_ML         = new CMLFilter(InpMinMLScore);
   g_Strategies = new CStrategies(g_Symbol, InpATRPeriod);
   g_Panel      = new CDisplayPanel(InpPanelX, InpPanelY, g_BotRunning,
                                     InpBuyColor, InpSellColor,
                                     InpNeutralColor, InpSLColor, InpTPColor);

   // Set magic number
   Trade.SetExpertMagicNumber(g_MagicNumber);
   Trade.SetDeviationInPoints(20);
   Trade.SetTypeFilling(ORDER_FILLING_FOK);

   // Reset scan timers
   g_LastScan15M = 0;
   g_LastScan1H  = 0;
   g_LastScan4H  = 0;
   g_LastScan1D  = 0;

   // Set timer to check every 60 seconds
   EventSetTimer(60);

   // Initial panel draw
   g_Panel.Draw(g_BotRunning, g_Symbol, 0, 0, 0, 0, 0);

   Print("DeltaForge EA v1.0 initialized on ", g_Symbol);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_Panel      != NULL) { delete g_Panel;      g_Panel      = NULL; }
   if(g_ML         != NULL) { delete g_ML;         g_ML         = NULL; }
   if(g_Risk       != NULL) { delete g_Risk;        g_Risk       = NULL; }
   if(g_Strategies != NULL) { delete g_Strategies; g_Strategies = NULL; }
   ObjectsDeleteAll(0, "DeltaForge_");
   Comment("");
}

//+------------------------------------------------------------------+
//| Timer event - periodic scanning                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(!g_BotRunning) {
      g_Panel.UpdateStatus(false, "BOT STOPPED - Manual Restart Required");
      return;
   }

   datetime now = TimeCurrent();

   // Auto-anomaly detection
   if(InpAutoStopOnAnomaly && g_ML.DetectAnomaly(g_Symbol, PERIOD_M15)) {
      g_BotRunning = false;
      g_Panel.UpdateStatus(false, "AUTO-STOPPED: Market Anomaly Detected");
      Alert("DeltaForge: BOT AUTO-STOPPED on ", g_Symbol, " - Anomaly detected!");
      return;
   }

   // Check manual trades and apply auto SL/TP
   CheckManualTrades();

   // Manage existing trail stops
   ManageTrailStops();

   // Scan timeframes
   if((now - g_LastScan15M) >= InpScan15M) {
      ScanTimeframe(PERIOD_M15);
      g_LastScan15M = now;
   }
   if((now - g_LastScan1H) >= InpScan1H) {
      ScanTimeframe(PERIOD_H1);
      g_LastScan1H = now;
   }
   if((now - g_LastScan4H) >= InpScan4H) {
      ScanTimeframe(PERIOD_H4);
      g_LastScan4H = now;
   }
   if((now - g_LastScan1D) >= InpScan1D) {
      ScanTimeframe(PERIOD_D1);
      g_LastScan1D = now;
   }
}

//+------------------------------------------------------------------+
//| Main tick                                                         |
//+------------------------------------------------------------------+
void OnTick()
{
   // Always manage trailing stops on each tick if enabled
   if(g_BotRunning && InpTrailStopEnabled)
      ManageTrailStops();

   // Update panel price info
   if(g_Panel != NULL)
      g_Panel.UpdatePrice(SymbolInfoDouble(g_Symbol, SYMBOL_BID),
                          SymbolInfoDouble(g_Symbol, SYMBOL_ASK));
}

//+------------------------------------------------------------------+
//| Chart event - panel button clicks                                 |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long& lparam, const double& dparam, const string& sparam)
{
   if(id == CHARTEVENT_OBJECT_CLICK) {
      if(sparam == "DeltaForge_BtnToggle") {
         g_BotRunning = !g_BotRunning;
         g_Panel.UpdateStatus(g_BotRunning,
            g_BotRunning ? "BOT RUNNING" : "BOT STOPPED");
         Print("DeltaForge: Bot ", g_BotRunning ? "STARTED" : "STOPPED", " manually");
      }
      if(sparam == "DeltaForge_BtnRefresh")
         ScanTimeframe(PERIOD_M15);
   }
}

//+------------------------------------------------------------------+
//| Scan a specific timeframe for signals                             |
//+------------------------------------------------------------------+
void ScanTimeframe(ENUM_TIMEFRAMES tf)
{
   if(!g_BotRunning) return;

   // Risk checks first
   if(!g_Risk.CanPlaceOrder(g_Symbol, 0)) return;

   // Collect signals from all enabled strategies
   SSignalResult sig = CollectStrategies(tf);

   // ML Score
   double mlScore = g_ML.ScoreSignal(g_Symbol, tf, sig);
   sig.ml_score   = mlScore;

   // Display the signal on panel
   g_Panel.UpdateSignal(sig, tf);

   // Check ML threshold
   if(mlScore < InpMinMLScore) {
      Print("DeltaForge [", EnumToString(tf), "]: ML score ", DoubleToString(mlScore,1),
            " below threshold. Signal rejected.");
      return;
   }

   // No signal
   if(sig.direction == SIGNAL_NONE) return;

   // Higher timeframe confirmation
   if(InpHTFConfirmEnabled && !CheckHTFConfirmation(tf, sig.direction)) {
      Print("DeltaForge [", EnumToString(tf), "]: HTF Confirmation failed. Signal rejected.");
      g_Panel.UpdateStatus(g_BotRunning, "HTF Rejected - " + EnumToString(tf));
      return;
   }

   // Calculate SL/TP from backtest data + ATR
   double sl = 0, tp = 0;
   CalculateSLTP(tf, sig.direction, sl, tp);

   // Final lot size from risk manager
   double lots = g_Risk.CalculateLotSize(g_Symbol, sl);
   if(lots <= 0) return;

   // Place the order
   PlaceOrder(sig.direction, lots, sl, tp, tf);
}

//+------------------------------------------------------------------+
//| Aggregate all enabled strategy signals                            |
//+------------------------------------------------------------------+
SSignalResult CollectStrategies(ENUM_TIMEFRAMES tf)
{
   SSignalResult result;
   result.direction     = SIGNAL_NONE;
   result.confluence    = 0;
   result.ml_score      = 0;
   result.strategy_hits = "";

   int buyVotes  = 0;
   int sellVotes = 0;
   int total     = 0;

   #define CHECK_STRAT(enabled, func, name) \
      if(enabled) { \
         ENUM_SIGNAL s = g_Strategies.func(tf); \
         total++; \
         if(s == SIGNAL_BUY)  { buyVotes++;  result.strategy_hits += name + "(B) "; } \
         else if(s == SIGNAL_SELL) { sellVotes++; result.strategy_hits += name + "(S) "; } \
      }

   CHECK_STRAT(Strat_MA_Cross,       GetMA_Cross,         "MA")
   CHECK_STRAT(Strat_EMA_Trend,      GetEMA_Trend,        "EMA")
   CHECK_STRAT(Strat_MACD,           GetMACD,             "MACD")
   CHECK_STRAT(Strat_ADX_Filter,     GetADX,              "ADX")
   CHECK_STRAT(Strat_ParabolicSAR,   GetParabolicSAR,     "PSAR")
   CHECK_STRAT(Strat_RSI,            GetRSI,              "RSI")
   CHECK_STRAT(Strat_Stochastic,     GetStochastic,       "STOCH")
   CHECK_STRAT(Strat_Momentum,       GetMomentum,         "MOM")
   CHECK_STRAT(Strat_BollingerBands, GetBollingerBands,   "BB")
   CHECK_STRAT(Strat_ATR_Breakout,   GetATRBreakout,      "ATR")
   CHECK_STRAT(Strat_AccumDist,      GetAccumDist,        "AD")
   CHECK_STRAT(Strat_ChaikinMF,      GetChaikinMF,        "CMF")
   CHECK_STRAT(Strat_Fibonacci,      GetFibonacci,        "FIB")
   CHECK_STRAT(Strat_PivotPoints,    GetPivotPoints,      "PIV")
   CHECK_STRAT(Strat_SupportResist,  GetSupportResist,    "SR")
   CHECK_STRAT(Strat_Ichimoku,       GetIchimoku,         "ICHI")
   CHECK_STRAT(Strat_Breakout,       GetBreakout,         "BRK")
   CHECK_STRAT(Strat_Trendline,      GetTrendline,        "TRL")
   CHECK_STRAT(Strat_VolumeBreakout, GetVolumeBreakout,   "VBKO")
   CHECK_STRAT(Strat_Pullback,       GetPullback,         "PBK")
   CHECK_STRAT(Strat_SMC,            GetSMC,              "SMC")
   CHECK_STRAT(Strat_OrderFlow,      GetOrderFlow,        "OF")
   CHECK_STRAT(Strat_MarketProfile,  GetMarketProfile,    "MP")
   CHECK_STRAT(Strat_LuxAlgo,        GetLuxAlgo,          "LUX")
   CHECK_STRAT(Strat_NewsMomentum,   GetNewsMomentum,     "NEWS")
   CHECK_STRAT(Strat_QuantAlgo,      GetQuantAlgo,        "QUANT")

   if(total == 0) return result;

   result.confluence = (buyVotes > sellVotes)
                       ? (double)buyVotes  / total * 100.0
                       : (double)sellVotes / total * 100.0;

   // Minimum 40% confluence required
   if(buyVotes > sellVotes && (double)buyVotes/total >= 0.40)
      result.direction = SIGNAL_BUY;
   else if(sellVotes > buyVotes && (double)sellVotes/total >= 0.40)
      result.direction = SIGNAL_SELL;

   return result;
}

//+------------------------------------------------------------------+
//| Higher Timeframe Confirmation                                     |
//+------------------------------------------------------------------+
bool CheckHTFConfirmation(ENUM_TIMEFRAMES tf, ENUM_SIGNAL dir)
{
   ENUM_TIMEFRAMES htf1 = PERIOD_NULL, htf2 = PERIOD_NULL;

   if(tf == PERIOD_M15) { htf1 = PERIOD_H1;  htf2 = PERIOD_H4; }
   if(tf == PERIOD_H1)  { htf1 = PERIOD_H4;  htf2 = PERIOD_D1; }
   if(tf == PERIOD_H4)  { htf1 = PERIOD_D1;  htf2 = PERIOD_D1; }
   if(tf == PERIOD_D1)  { htf1 = PERIOD_D1;  htf2 = PERIOD_D1; } // D1 is highest; skip HTF check

   if(tf == PERIOD_D1) return true;

   // Get HTF trends (simple EMA slope direction)
   ENUM_SIGNAL trend1 = g_Strategies.GetEMA_Trend(htf1);
   ENUM_SIGNAL trend2 = (htf2 != htf1) ? g_Strategies.GetEMA_Trend(htf2) : trend1;

   if(InpRequireBothHTF)
      return (trend1 == dir && trend2 == dir);
   else
      return (trend1 == dir || trend2 == dir);
}

//+------------------------------------------------------------------+
//| Calculate SL/TP levels                                            |
//+------------------------------------------------------------------+
void CalculateSLTP(ENUM_TIMEFRAMES tf, ENUM_SIGNAL dir,
                   double &sl, double &tp)
{
   double atr      = g_Risk.GetATR(g_Symbol, tf, InpATRPeriod);
   double bid      = SymbolInfoDouble(g_Symbol, SYMBOL_BID);
   double point    = SymbolInfoDouble(g_Symbol, SYMBOL_POINT);
   double slDist   = atr * InpATRMultiplier;

   if(dir == SIGNAL_BUY) {
      sl = bid - slDist;
      tp = InpTakeProfitEnabled ? bid + slDist * InpTPRiskReward : 0;
   } else {
      sl = bid + slDist;
      tp = InpTakeProfitEnabled ? bid - slDist * InpTPRiskReward : 0;
   }

   // Ensure minimum stop distance
   long stopLevel = SymbolInfoInteger(g_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * point;
   if(dir == SIGNAL_BUY  && (bid - sl) < minDist) sl = bid - minDist;
   if(dir == SIGNAL_SELL && (sl - bid) < minDist) sl = bid + minDist;

   // Normalize
   sl = NormalizeDouble(sl, (int)SymbolInfoInteger(g_Symbol, SYMBOL_DIGITS));
   tp = NormalizeDouble(tp, (int)SymbolInfoInteger(g_Symbol, SYMBOL_DIGITS));
}

//+------------------------------------------------------------------+
//| Place an order                                                    |
//+------------------------------------------------------------------+
bool PlaceOrder(ENUM_SIGNAL dir, double lots, double sl, double tp,
                ENUM_TIMEFRAMES tf)
{
   string comment = "DeltaForge|" + EnumToString(tf);
   bool   res     = false;

   if(dir == SIGNAL_BUY) {
      double ask = SymbolInfoDouble(g_Symbol, SYMBOL_ASK);
      res = Trade.Buy(lots, g_Symbol, ask, sl, tp, comment);
   } else {
      double bid = SymbolInfoDouble(g_Symbol, SYMBOL_BID);
      res = Trade.Sell(lots, g_Symbol, bid, sl, tp, comment);
   }

   if(res) {
      ulong ticket = Trade.ResultOrder();
      Print("DeltaForge: Order placed #", ticket, " | ",
            EnumToString(dir), " | Lots: ", lots,
            " | SL: ", sl, " | TP: ", tp);
      g_Panel.UpdateLastTrade(dir, lots, sl, tp);
   } else {
      Print("DeltaForge: Order FAILED | Error: ", Trade.ResultRetcodeDescription());
   }

   return res;
}

//+------------------------------------------------------------------+
//| Detect and manage manual trades (auto SL/TP)                     |
//+------------------------------------------------------------------+
void CheckManualTrades()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      if(!PosInfo.SelectByIndex(i)) continue;
      if(PosInfo.Symbol() != g_Symbol) continue;
      if(PosInfo.Magic()  == g_MagicNumber) continue; // Already ours

      // This is a manual trade — apply auto SL/TP if missing
      ulong  ticket = PosInfo.Ticket();
      double curSL  = PosInfo.StopLoss();
      double curTP  = PosInfo.TakeProfit();

      if(curSL == 0 || curTP == 0) {
         ENUM_SIGNAL dir = (PosInfo.PositionType() == POSITION_TYPE_BUY)
                           ? SIGNAL_BUY : SIGNAL_SELL;
         double newSL = curSL, newTP = curTP;
         CalculateSLTP(PERIOD_H1, dir, newSL, newTP);
         if(curSL == 0) curSL = newSL;
         if(curTP == 0) curTP = newTP;
         Trade.PositionModify(ticket, curSL, curTP);
         Print("DeltaForge: Auto SL/TP applied to manual trade #", ticket);
      }
   }
}

//+------------------------------------------------------------------+
//| Manage all open trail stops (all 5 trail types)                  |
//+------------------------------------------------------------------+
void ManageTrailStops()
{
   if(!InpTrailStopEnabled) return;

   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      if(!PosInfo.SelectByIndex(i)) continue;
      if(PosInfo.Symbol() != g_Symbol) continue;

      ulong  ticket  = PosInfo.Ticket();
      double curSL   = PosInfo.StopLoss();
      double curTP   = PosInfo.TakeProfit();
      double bid     = SymbolInfoDouble(g_Symbol, SYMBOL_BID);
      double ask     = SymbolInfoDouble(g_Symbol, SYMBOL_ASK);
      double atr     = g_Risk.GetATR(g_Symbol, PERIOD_H1, InpATRPeriod);
      double tickVal = SymbolInfoDouble(g_Symbol, SYMBOL_TRADE_TICK_VALUE);
      int    digits  = (int)SymbolInfoInteger(g_Symbol, SYMBOL_DIGITS);
      double newSL   = 0;

      // ── Compute new SL per trail type ─────────────────────────
      if(PosInfo.PositionType() == POSITION_TYPE_BUY) {
         switch(InpTrailType) {
            case TRAIL_PERCENT:
               newSL = bid * (1.0 - InpTrailPercent / 100.0);
               break;
            case TRAIL_DOLLAR:
               newSL = (tickVal > 0) ? bid - InpTrailDollar / tickVal
                                     : bid - atr * InpATRMultiplier;
               break;
            case TRAIL_TIME: {
               datetime openTime = PosInfo.Time();
               double elapsed    = (double)(TimeCurrent() - openTime) / 60.0;
               double tighten    = MathMin(1.0, elapsed / MathMax((double)InpTrailTimeMins, 1.0));
               double dist       = atr * InpATRMultiplier * (1.0 - tighten * 0.5);
               newSL = bid - dist;
            } break;
            case TRAIL_VOLATILITY:
               newSL = bid - atr * InpVolatilityMult;
               break;
            case TRAIL_ATR:
            default:
               newSL = bid - atr * InpATRMultiplier;
               break;
         }
         newSL = NormalizeDouble(newSL, digits);
         if(newSL > curSL && newSL < bid) {
            double prevSL = curSL;
            if(Trade.PositionModify(ticket, newSL, curTP)) {
               // ── Display trail event ──────────────────────────
               string msg = StringFormat(
                  "[DELTAFORGE] TRAIL ▲ BUY #%I64u  SL: %.*f → %.*f",
                  ticket, digits, prevSL, digits, newSL);
               Print(msg);
               Comment(StringFormat("DeltaForge | TRAIL ▲ BUY SL: %.*f → %.*f",
                                    digits, prevSL, digits, newSL));
            }
         }
      }
      else if(PosInfo.PositionType() == POSITION_TYPE_SELL) {
         switch(InpTrailType) {
            case TRAIL_PERCENT:
               newSL = ask * (1.0 + InpTrailPercent / 100.0);
               break;
            case TRAIL_DOLLAR:
               newSL = (tickVal > 0) ? ask + InpTrailDollar / tickVal
                                     : ask + atr * InpATRMultiplier;
               break;
            case TRAIL_TIME: {
               datetime openTime = PosInfo.Time();
               double elapsed    = (double)(TimeCurrent() - openTime) / 60.0;
               double tighten    = MathMin(1.0, elapsed / MathMax((double)InpTrailTimeMins, 1.0));
               double dist       = atr * InpATRMultiplier * (1.0 - tighten * 0.5);
               newSL = ask + dist;
            } break;
            case TRAIL_VOLATILITY:
               newSL = ask + atr * InpVolatilityMult;
               break;
            case TRAIL_ATR:
            default:
               newSL = ask + atr * InpATRMultiplier;
               break;
         }
         newSL = NormalizeDouble(newSL, digits);
         if(newSL < curSL && newSL > ask) {
            double prevSL = curSL;
            if(Trade.PositionModify(ticket, newSL, curTP)) {
               string msg = StringFormat(
                  "[DELTAFORGE] TRAIL ▼ SELL #%I64u  SL: %.*f → %.*f",
                  ticket, digits, prevSL, digits, newSL);
               Print(msg);
               Comment(StringFormat("DeltaForge | TRAIL ▼ SELL SL: %.*f → %.*f",
                                    digits, prevSL, digits, newSL));
            }
         }
      }
   }
}
