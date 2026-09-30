//+------------------------------------------------------------------+
//|                                              DeltaForge_EA.mq4       |
//|                        DeltaForge Agentic AI Trading System v1.0     |
//|                                     https://deltaforge.tech          |
//+------------------------------------------------------------------+
#property copyright "DeltaForge Trading Systems"
#property link      "https://deltaforge.tech"
#property version   "1.00"
#property description "DeltaForge Multi-Strategy Agentic AI EA - MT4 Version"
#property strict

//+------------------------------------------------------------------+
//| ENUMERATIONS                                                      |
//+------------------------------------------------------------------+
enum ENUM_SIGNAL     { SIGNAL_NONE=0, SIGNAL_BUY=1, SIGNAL_SELL=-1 };
enum ENUM_TRAIL_TYPE { TRAIL_ATR=0, TRAIL_PERCENT=1, TRAIL_DOLLAR=2, TRAIL_TIME=3 };

//+------------------------------------------------------------------+
//| INPUT PARAMETERS                                                  |
//+------------------------------------------------------------------+
extern bool   InpBotRunning          = true;    // Bot Running on Start
extern bool   InpAutoStopOnAnomaly   = true;    // Auto-Stop on Anomaly

// Strategy toggles
extern bool   Strat_MA_Cross         = true;    // MA Crossover
extern bool   Strat_EMA_Trend        = true;    // EMA Trend
extern bool   Strat_MACD             = true;    // MACD
extern bool   Strat_ADX              = true;    // ADX Filter
extern bool   Strat_SAR              = true;    // Parabolic SAR
extern bool   Strat_RSI              = true;    // RSI
extern bool   Strat_Stoch            = true;    // Stochastic
extern bool   Strat_Momentum         = true;    // Momentum
extern bool   Strat_BB               = true;    // Bollinger Bands
extern bool   Strat_ATR              = true;    // ATR Breakout
extern bool   Strat_ChaikinMF        = true;    // Chaikin MF
extern bool   Strat_Fibonacci        = true;    // Fibonacci
extern bool   Strat_Ichimoku         = true;    // Ichimoku
extern bool   Strat_Breakout         = true;    // Breakout
extern bool   Strat_VolumeBreakout   = true;    // Volume Breakout
extern bool   Strat_SMC              = true;    // Smart Money Concepts
extern bool   Strat_SupportResist    = true;    // S/R Zones
extern bool   Strat_Pullback         = true;    // Pullback
extern bool   Strat_OrderFlow        = true;    // Order Flow
extern bool   Strat_MarketProfile    = true;    // Market Profile
// ── Advanced Strategies (26 total) ──────────────────────────────────
extern bool   Strat_LuxAlgo          = true;    // LuxAlgo RSI Divergence + EMA Ribbon
extern bool   Strat_NewsMomentum     = true;    // News Momentum (Impulse + Volume Surge)
extern bool   Strat_QuantAlgo        = true;    // Quantitative Z-Score Mean Reversion

// Risk settings
extern double InpMaxLossPerTrade     = 50.0;    // Max Loss Per Trade ($)
extern double InpMaxLotSize          = 1.0;     // Maximum Lot Size
extern int    InpMaxTotalOrders      = 10;      // Max Total Orders
extern int    InpMaxOrdersPerPair    = 2;       // Max Orders Per Pair
extern int    InpMaxBuyOrders        = 5;       // Max Buy Orders
extern int    InpMaxSellOrders       = 5;       // Max Sell Orders
extern double InpRiskPercent         = 1.0;     // Risk % Per Trade
extern double InpMinMLScore          = 60.0;    // Min ML Score (0-100)

// Stop loss
extern bool   InpTrailEnabled        = true;    // Trail Stop ON/OFF
extern int    InpTrailType           = 0;       // 0=ATR 1=% 2=$ 3=Time 4=Volatility
extern double InpTrailPercent        = 1.5;     // Trail Stop %
extern double InpTrailDollar         = 30.0;    // Trail Stop $
extern double InpATRMult             = 2.0;     // ATR Multiplier
extern int    InpTrailTimeMins       = 60;      // Time Trail: max minutes before full tighten
extern double InpVolatilityMult      = 1.5;     // Volatility Trail: ATR multiplier
extern int    InpATRPeriod           = 14;      // ATR Period

// Take profit
extern bool   InpTPEnabled           = true;    // Take Profit ON/OFF
extern double InpTPRR                = 2.0;     // Risk:Reward Ratio

// Scan intervals (seconds)
extern int    InpScan15M             = 2100;    // M15 scan (secs)
extern int    InpScan1H              = 3600;    // H1 scan (secs)
extern int    InpScan4H              = 14400;   // H4 scan (secs)
extern int    InpScan1D              = 86400;   // D1 scan (secs)

// HTF confirmation
extern bool   InpHTFConfirm          = true;    // HTF Confirmation
extern bool   InpBothHTF             = false;   // Require Both HTF

// Display
extern int    InpPanelX              = 10;      // Panel X
extern int    InpPanelY              = 30;      // Panel Y

//+------------------------------------------------------------------+
//| GLOBALS                                                           |
//+------------------------------------------------------------------+
bool     g_BotRunning;
datetime g_LastScan[4]; // 0=M15,1=H1,2=H4,3=D1
int      g_ScanIntervals[4];
int      g_TFs[4]  = {PERIOD_M15, PERIOD_H1, PERIOD_H4, PERIOD_D1};
int      g_Magic   = 20250001;

string   g_prefix  = "NF4_";
double   g_LastSL  = 0, g_LastTP = 0;

//+------------------------------------------------------------------+
//| INIT                                                              |
//+------------------------------------------------------------------+
int OnInit()
{
   g_BotRunning        = InpBotRunning;
   g_ScanIntervals[0]  = InpScan15M;
   g_ScanIntervals[1]  = InpScan1H;
   g_ScanIntervals[2]  = InpScan4H;
   g_ScanIntervals[3]  = InpScan1D;

   ArrayInitialize(g_LastScan, 0);
   EventSetTimer(60);
   BuildPanel();
   Print("DeltaForge EA v1.0 (MT4) initialized on ", Symbol());
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| DEINIT                                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectsDeleteAll(0, g_prefix);
}

//+------------------------------------------------------------------+
//| TIMER                                                             |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(!g_BotRunning) {
      PanelStatus(false, "BOT STOPPED");
      return;
   }
   if(InpAutoStopOnAnomaly && DetectAnomaly()) {
      g_BotRunning = false;
      PanelStatus(false, "AUTO-STOPPED: ANOMALY");
      Alert("DeltaForge MT4: BOT STOPPED - Anomaly on ", Symbol());
      return;
   }

   CheckManualTrades();
   if(InpTrailEnabled) ManageTrails();

   datetime now = TimeCurrent();
   for(int i = 0; i < 4; i++) {
      if((now - g_LastScan[i]) >= g_ScanIntervals[i]) {
         ScanTF(g_TFs[i]);
         g_LastScan[i] = now;
      }
   }
}

//+------------------------------------------------------------------+
//| TICK                                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   if(g_BotRunning && InpTrailEnabled)
      ManageTrails();
   PanelUpdatePrice(Bid, Ask);
}

//+------------------------------------------------------------------+
//| CHART EVENT (button clicks)                                       |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam,
                  const double &dparam, const string &sparam)
{
   if(id == CHARTEVENT_OBJECT_CLICK) {
      if(sparam == g_prefix+"BtnToggle") {
         g_BotRunning = !g_BotRunning;
         PanelStatus(g_BotRunning, g_BotRunning ? "RUNNING" : "STOPPED");
         ObjectSetInteger(0, g_prefix+"BtnToggle", OBJPROP_STATE, false);
      }
      if(sparam == g_prefix+"BtnScan") {
         ScanTF(PERIOD_M15);
         ObjectSetInteger(0, g_prefix+"BtnScan", OBJPROP_STATE, false);
      }
   }
}

//+------------------------------------------------------------------+
//| SCAN ONE TIMEFRAME                                                |
//+------------------------------------------------------------------+
void ScanTF(int tf)
{
   if(!g_BotRunning) return;
   if(!CanPlaceOrder(0)) return;

   int    buyV = 0, sellV = 0, total = 0;
   string hits = "";
   GetSignals(tf, buyV, sellV, total, hits);

   double conf   = 0;
   int    dir    = 0;
   if(total > 0) {
      if(buyV > sellV && (double)buyV/total >= 0.4) {
         dir  = 1; conf = (double)buyV/total*100;
      } else if(sellV > buyV && (double)sellV/total >= 0.4) {
         dir  = -1; conf = (double)sellV/total*100;
      }
   }

   double mlScore = ScoreML(tf, dir, conf);
   double prob    = mlScore;

   PanelUpdateSignal(tf, dir, conf, mlScore, prob, hits);

   if(mlScore < InpMinMLScore || dir == 0) return;

   if(InpHTFConfirm && !ConfirmHTF(tf, dir)) {
      Print("DeltaForge MT4 [TF", tf, "]: HTF rejected");
      return;
   }

   double sl = 0, tp = 0;
   CalcSLTP(tf, dir, sl, tp);
   double lots = CalcLots(sl);
   if(lots <= 0) return;

   PlaceOrder(dir, lots, sl, tp, tf);
}

//+------------------------------------------------------------------+
//| COLLECT SIGNALS FROM ALL STRATEGIES                               |
//+------------------------------------------------------------------+
void GetSignals(int tf, int &buyV, int &sellV, int &total, string &hits)
{
   buyV = 0; sellV = 0; total = 0; hits = "";

   #define VOTE(enabled, sig, name) \
      if(enabled) { int s=(sig); total++; \
        if(s==1){buyV++; hits+=name+"(B) ";} \
        else if(s==-1){sellV++; hits+=name+"(S) ";} }

   VOTE(Strat_MA_Cross,       S_MACross(tf),      "MA")
   VOTE(Strat_EMA_Trend,      S_EMATrend(tf),     "EMA")
   VOTE(Strat_MACD,           S_MACD(tf),         "MACD")
   VOTE(Strat_ADX,            S_ADX(tf),          "ADX")
   VOTE(Strat_SAR,            S_SAR(tf),          "SAR")
   VOTE(Strat_RSI,            S_RSI(tf),          "RSI")
   VOTE(Strat_Stoch,          S_Stoch(tf),        "STOCH")
   VOTE(Strat_Momentum,       S_Momentum(tf),     "MOM")
   VOTE(Strat_BB,             S_BB(tf),           "BB")
   VOTE(Strat_ATR,            S_ATRBreak(tf),     "ATR")
   VOTE(Strat_ChaikinMF,      S_CMF(tf),          "CMF")
   VOTE(Strat_Fibonacci,      S_Fib(tf),          "FIB")
   VOTE(Strat_Ichimoku,       S_Ichimoku(tf),     "ICHI")
   VOTE(Strat_Breakout,       S_Breakout(tf),     "BRK")
   VOTE(Strat_VolumeBreakout, S_VolBreak(tf),     "VBKO")
   VOTE(Strat_SMC,            S_SMC(tf),          "SMC")
   VOTE(Strat_SupportResist,  S_SR(tf),           "SR")
   VOTE(Strat_Pullback,       S_Pullback(tf),     "PBK")
   VOTE(Strat_OrderFlow,      S_OrderFlow(tf),    "OF")
   VOTE(Strat_MarketProfile,  S_MktProfile(tf),   "MP")
   VOTE(Strat_LuxAlgo,        S_LuxAlgo(tf),      "LUX")
   VOTE(Strat_NewsMomentum,   S_NewsMomentum(tf), "NEWS")
   VOTE(Strat_QuantAlgo,      S_QuantAlgo(tf),    "QUANT")
}

//--- Strategy 1: MA Crossover
int S_MACross(int tf) {
   double f1=iMA(NULL,tf,10,0,MODE_SMA,PRICE_CLOSE,1), f2=iMA(NULL,tf,10,0,MODE_SMA,PRICE_CLOSE,2);
   double s1=iMA(NULL,tf,50,0,MODE_SMA,PRICE_CLOSE,1), s2=iMA(NULL,tf,50,0,MODE_SMA,PRICE_CLOSE,2);
   if(f2<s2&&f1>s1) return 1; if(f2>s2&&f1<s1) return -1; return 0;
}
//--- Strategy 2: EMA Trend
int S_EMATrend(int tf) {
   double e20=iMA(NULL,tf,20,0,MODE_EMA,PRICE_CLOSE,1);
   double e50=iMA(NULL,tf,50,0,MODE_EMA,PRICE_CLOSE,1);
   double e200=iMA(NULL,tf,200,0,MODE_EMA,PRICE_CLOSE,1);
   double p=iClose(NULL,tf,1);
   if(p>e20&&e20>e50&&e50>e200) return 1;
   if(p<e20&&e20<e50&&e50<e200) return -1; return 0;
}
//--- Strategy 3: MACD
int S_MACD(int tf) {
   double m1=iMACD(NULL,tf,12,26,9,PRICE_CLOSE,MODE_MAIN,1);
   double m2=iMACD(NULL,tf,12,26,9,PRICE_CLOSE,MODE_MAIN,2);
   double s1=iMACD(NULL,tf,12,26,9,PRICE_CLOSE,MODE_SIGNAL,1);
   double s2=iMACD(NULL,tf,12,26,9,PRICE_CLOSE,MODE_SIGNAL,2);
   if(m2<s2&&m1>s1) return 1; if(m2>s2&&m1<s1) return -1; return 0;
}
//--- Strategy 4: ADX
int S_ADX(int tf) {
   double adx=iADX(NULL,tf,14,PRICE_CLOSE,MODE_MAIN,1);
   double dp=iADX(NULL,tf,14,PRICE_CLOSE,MODE_PLUSDI,1);
   double dm=iADX(NULL,tf,14,PRICE_CLOSE,MODE_MINUSDI,1);
   if(adx>25&&dp>dm) return 1; if(adx>25&&dm>dp) return -1; return 0;
}
//--- Strategy 5: Parabolic SAR
int S_SAR(int tf) {
   double sar1=iSAR(NULL,tf,0.02,0.2,1), sar2=iSAR(NULL,tf,0.02,0.2,2);
   double p1=iClose(NULL,tf,1), p2=iClose(NULL,tf,2);
   if(sar2>p2&&sar1<p1) return 1; if(sar2<p2&&sar1>p1) return -1; return 0;
}
//--- Strategy 6: RSI
int S_RSI(int tf) {
   double r1=iRSI(NULL,tf,14,PRICE_CLOSE,1), r2=iRSI(NULL,tf,14,PRICE_CLOSE,2);
   if(r2<30&&r1>30) return 1; if(r2>70&&r1<70) return -1; return 0;
}
//--- Strategy 7: Stochastic
int S_Stoch(int tf) {
   double k1=iStochastic(NULL,tf,14,3,3,MODE_SMA,0,MODE_MAIN,1);
   double k2=iStochastic(NULL,tf,14,3,3,MODE_SMA,0,MODE_MAIN,2);
   double d1=iStochastic(NULL,tf,14,3,3,MODE_SMA,0,MODE_SIGNAL,1);
   double d2=iStochastic(NULL,tf,14,3,3,MODE_SMA,0,MODE_SIGNAL,2);
   if(k1<20&&d1<20&&k2<d2&&k1>d1) return 1;
   if(k1>80&&d1>80&&k2>d2&&k1<d1) return -1; return 0;
}
//--- Strategy 8: Momentum
int S_Momentum(int tf) {
   double m1=iMomentum(NULL,tf,14,PRICE_CLOSE,1);
   double m2=iMomentum(NULL,tf,14,PRICE_CLOSE,2);
   if(m1>100&&m2<100) return 1; if(m1<100&&m2>100) return -1; return 0;
}
//--- Strategy 9: Bollinger Bands
int S_BB(int tf) {
   double upper=iBands(NULL,tf,20,2,0,PRICE_CLOSE,MODE_UPPER,1);
   double lower=iBands(NULL,tf,20,2,0,PRICE_CLOSE,MODE_LOWER,1);
   double c1=iClose(NULL,tf,1), c2=iClose(NULL,tf,2);
   if(c2<=lower&&c1>lower) return 1; if(c2>=upper&&c1<upper) return -1; return 0;
}
//--- Strategy 10: ATR Breakout
int S_ATRBreak(int tf) {
   double atr=iATR(NULL,tf,InpATRPeriod,1);
   double high20=0, low20=999999;
   for(int i=2;i<=20;i++){
      if(iHigh(NULL,tf,i)>high20) high20=iHigh(NULL,tf,i);
      if(iLow(NULL,tf,i)<low20)   low20=iLow(NULL,tf,i);
   }
   double c=iClose(NULL,tf,1);
   if(c>high20+atr*0.5) return 1; if(c<low20-atr*0.5) return -1; return 0;
}
//--- Strategy 11: Chaikin MF
int S_CMF(int tf) {
   double smfv=0, svol=0;
   for(int i=1;i<=20;i++){
      double h=iHigh(NULL,tf,i),l=iLow(NULL,tf,i),c=iClose(NULL,tf,i);
      double v=iVolume(NULL,tf,i); double hl=h-l;
      if(hl>0){smfv+=((c-l)-(h-c))/hl*v; svol+=v;}
   }
   double cmf=svol>0?smfv/svol:0;
   if(cmf>0.05) return 1; if(cmf<-0.05) return -1; return 0;
}
//--- Strategy 12: Fibonacci
int S_Fib(int tf) {
   double swH=0,swL=999999;
   for(int i=1;i<=50;i++){
      if(iHigh(NULL,tf,i)>swH) swH=iHigh(NULL,tf,i);
      if(iLow(NULL,tf,i)<swL)  swL=iLow(NULL,tf,i);
   }
   double r=swH-swL, c=iClose(NULL,tf,1);
   double f618=swH-r*0.618, f500=swH-r*0.500, tol=r*0.015;
   if(MathAbs(c-f618)<tol||MathAbs(c-f500)<tol) return 1;
   if(MathAbs(c-(swH-r*0.382))<tol&&c<f500)     return -1; return 0;
}
//--- Strategy 13: Ichimoku
int S_Ichimoku(int tf) {
   double ten=iIchimoku(NULL,tf,9,26,52,MODE_TENKANSEN,1);
   double kij=iIchimoku(NULL,tf,9,26,52,MODE_KIJANSEN,1);
   double spa=iIchimoku(NULL,tf,9,26,52,MODE_SENKOUSPANA,1);
   double spb=iIchimoku(NULL,tf,9,26,52,MODE_SENKOUSPANB,1);
   double c=iClose(NULL,tf,1);
   double cTop=MathMax(spa,spb), cBot=MathMin(spa,spb);
   if(c>cTop&&ten>kij) return 1; if(c<cBot&&ten<kij) return -1; return 0;
}
//--- Strategy 14: Breakout
int S_Breakout(int tf) {
   double h20=0,l20=999999,atr=iATR(NULL,tf,14,1);
   for(int i=2;i<=20;i++){
      if(iHigh(NULL,tf,i)>h20) h20=iHigh(NULL,tf,i);
      if(iLow(NULL,tf,i)<l20)  l20=iLow(NULL,tf,i);
   }
   double c=iClose(NULL,tf,1);
   if(c>h20+atr*0.3) return 1; if(c<l20-atr*0.3) return -1; return 0;
}
//--- Strategy 15: Volume Breakout
int S_VolBreak(int tf) {
   double avg=0;
   for(int i=2;i<=21;i++) avg+=iVolume(NULL,tf,i); avg/=20;
   double cv=iVolume(NULL,tf,1),c=iClose(NULL,tf,1),p=iClose(NULL,tf,2);
   if(cv>avg*1.8){if(c>p) return 1; if(c<p) return -1;}
   return 0;
}
//--- Strategy 16: SMC (Fair Value Gaps)
int S_SMC(int tf) {
   for(int i=3;i<=10;i++){
      double hb=iHigh(NULL,tf,i+1),la=iLow(NULL,tf,i-1);
      double lb=iLow(NULL,tf,i+1), ha=iHigh(NULL,tf,i-1);
      double c=iClose(NULL,tf,1);
      if(la>hb&&c>=hb&&c<=la) return 1;
      if(ha<lb&&c<=lb&&c>=ha) return -1;
   }
   return 0;
}
//--- Strategy 17: Support & Resistance
int S_SR(int tf) {
   double c=iClose(NULL,tf,1), atr=iATR(NULL,tf,14,1);
   int tb=0,ts=0;
   for(int i=3;i<=100;i++){
      if(MathAbs(c-iLow(NULL,tf,i))<atr*0.5)  tb++;
      if(MathAbs(c-iHigh(NULL,tf,i))<atr*0.5) ts++;
   }
   if(tb>=3) return 1; if(ts>=3) return -1; return 0;
}
//--- Strategy 18: Pullback
int S_Pullback(int tf) {
   double e50=iMA(NULL,tf,50,0,MODE_EMA,PRICE_CLOSE,1);
   double e200=iMA(NULL,tf,200,0,MODE_EMA,PRICE_CLOSE,1);
   double c=iClose(NULL,tf,1);
   if(e50>e200&&MathAbs(c-e50)<e50*0.002) return 1;
   if(e50<e200&&MathAbs(c-e50)<e50*0.002) return -1; return 0;
}
//--- Strategy 19: Order Flow
int S_OrderFlow(int tf) {
   double h5=0,l5=999999, atr=iATR(NULL,tf,14,1);
   for(int i=2;i<=6;i++){
      if(iHigh(NULL,tf,i)>h5) h5=iHigh(NULL,tf,i);
      if(iLow(NULL,tf,i)<l5)  l5=iLow(NULL,tf,i);
   }
   double ch=iHigh(NULL,tf,1),cl=iLow(NULL,tf,1),c=iClose(NULL,tf,1);
   if(ch>h5+atr*0.1&&c<h5) return -1;
   if(cl<l5-atr*0.1&&c>l5) return 1; return 0;
}
//--- Strategy 20: Market Profile
int S_MktProfile(int tf) {
   double maxV=0; int pocBar=1;
   for(int i=1;i<=20;i++) if(iVolume(NULL,tf,i)>maxV){maxV=iVolume(NULL,tf,i);pocBar=i;}
   double poc=(iHigh(NULL,tf,pocBar)+iLow(NULL,tf,pocBar))/2;
   double c=iClose(NULL,tf,1), atr=iATR(NULL,tf,14,1);
   if(c>poc+atr*0.3) return 1; if(c<poc-atr*0.3) return -1; return 0;
}

//--------------------------------------------------------------------
// 24. LUXALGO - RSI Divergence + EMA Ribbon Confirmation
//--------------------------------------------------------------------
int S_LuxAlgo(int tf) {
   double rsi1   = iRSI(NULL,tf,14,PRICE_CLOSE,1);
   double close1 = iClose(NULL,tf,1);
   double ema20  = iMA(NULL,tf,20,0,MODE_EMA,PRICE_CLOSE,1);
   double ema50  = iMA(NULL,tf,50,0,MODE_EMA,PRICE_CLOSE,1);
   if(rsi1<=0 || ema20<=0) return 0;

   // Swing high/low over last 30 bars
   double swLowP=close1, swLowR=rsi1, swHiP=close1, swHiR=rsi1;
   for(int i=2;i<=30;i++){
      double c=iClose(NULL,tf,i);
      double r=iRSI(NULL,tf,14,PRICE_CLOSE,i);
      if(c<swLowP){swLowP=c; swLowR=r;}
      if(c>swHiP) {swHiP=c;  swHiR=r;}
   }

   // Average volume
   double avgVol=0;
   for(int j=2;j<=21;j++) avgVol+=iVolume(NULL,tf,j);
   avgVol/=20.0;
   bool volOk=(iVolume(NULL,tf,1)>avgVol*1.1);

   // Bullish divergence
   if(close1<=swLowP*1.003 && rsi1>swLowR+3.0 && rsi1<45.0 && ema20>=ema50*0.998 && volOk)
      return 1;
   // Bearish divergence
   if(close1>=swHiP*0.997  && rsi1<swHiR-3.0  && rsi1>55.0 && ema20<=ema50*1.002 && volOk)
      return -1;

   // EMA Ribbon momentum
   double ema9 =iMA(NULL,tf, 9,0,MODE_EMA,PRICE_CLOSE,1);
   double ema21=iMA(NULL,tf,21,0,MODE_EMA,PRICE_CLOSE,1);
   if(ema9>ema21 && ema21>ema20 && ema20>ema50 && rsi1>50 && volOk) return  1;
   if(ema9<ema21 && ema21<ema20 && ema20<ema50 && rsi1<50 && volOk) return -1;
   return 0;
}

//--------------------------------------------------------------------
// 25. NEWS MOMENTUM - Large Impulse Candle + Volume Surge Continuation
//--------------------------------------------------------------------
int S_NewsMomentum(int tf) {
   double atr=iATR(NULL,tf,14,1);
   if(atr<=0) return 0;
   double avgVol=0;
   for(int j=4;j<=23;j++) avgVol+=iVolume(NULL,tf,j);
   avgVol/=20.0;
   if(avgVol<=0) return 0;
   double curClose=iClose(NULL,tf,1);
   for(int offset=2;offset<=4;offset++){
      double o=iOpen(NULL,tf,offset), c=iClose(NULL,tf,offset);
      double body=MathAbs(c-o);
      double vol=(double)iVolume(NULL,tf,offset);
      if(body<atr*1.8 || vol<avgVol*2.2) continue;
      bool isBull=(c>o);
      if(isBull  && curClose>=c*0.995) return  1;
      if(!isBull && curClose<=c*1.005) return -1;
   }
   return 0;
}

//--------------------------------------------------------------------
// 26. QUANTITATIVE ALGO - Z-Score Mean Reversion
//--------------------------------------------------------------------
int S_QuantAlgo(int tf) {
   int PERIOD=20;
   if(iBars(NULL,tf)<PERIOD+5) return 0;
   double sum=0, sumSq=0;
   for(int k=1;k<=PERIOD;k++){
      double c=iClose(NULL,tf,k);
      sum+=c; sumSq+=c*c;
   }
   double mean=sum/PERIOD;
   double vari=sumSq/PERIOD-mean*mean;
   if(vari<=0) return 0;
   double sigma=MathSqrt(vari);
   double z1=(iClose(NULL,tf,1)-mean)/sigma;
   double z2=(iClose(NULL,tf,2)-mean)/sigma;
   double z3=(iClose(NULL,tf,3)-mean)/sigma;
   // Mean reversion signals
   if(z3<-1.8 && z2<-1.8 && z1>z2) return  1;   // oversold reversion
   if(z3> 1.8 && z2> 1.8 && z1<z2) return -1;   // overbought reversion
   // Momentum continuation
   if(z2>1.5 && z1>z2)  return  1;
   if(z2<-1.5 && z1<z2) return -1;
   return 0;
}

//+------------------------------------------------------------------+
//| ML SCORE (simplified logistic regression)                         |
//+------------------------------------------------------------------+
double ScoreML(int tf, int dir, double conf)
{
   if(dir == 0) return 0;
   double rsi  = iRSI(NULL,tf,14,PRICE_CLOSE,1);
   double adx  = iADX(NULL,tf,14,PRICE_CLOSE,MODE_MAIN,1);
   double atr  = iATR(NULL,tf,14,1);
   double bid  = MarketInfo(Symbol(),MODE_BID);

   double f_rsi  = (rsi  - 50.0) / 50.0 * dir;
   double f_adx  = adx / 100.0;
   double f_conf = conf / 100.0;
   double f_atr  = MathMin(1.0, atr / bid * 100);

   double z = -0.15 + 0.45*f_rsi + 0.58*f_adx + 0.85*f_conf - 0.22*f_atr;
   double score = 1.0 / (1.0 + MathExp(-z)) * 100.0;
   return score;
}

//+------------------------------------------------------------------+
//| ANOMALY DETECTION                                                 |
//+------------------------------------------------------------------+
double g_pxHist[100]; int g_pxIdx=0; bool g_pxFull=false;
bool DetectAnomaly()
{
   double c = iClose(NULL,PERIOD_M15,1);
   g_pxHist[g_pxIdx] = c; g_pxIdx=(g_pxIdx+1)%100;
   if(g_pxIdx==0) g_pxFull=true;
   int n = g_pxFull ? 100 : g_pxIdx; if(n<20) return false;
   double mean=0; for(int i=0;i<n;i++) mean+=g_pxHist[i]; mean/=n;
   double var=0; for(int i=0;i<n;i++) var+=(g_pxHist[i]-mean)*(g_pxHist[i]-mean);
   double std=MathSqrt(var/n); if(std==0) return false;
   double z=MathAbs((c-mean)/std);
   return(z>3.5);
}

//+------------------------------------------------------------------+
//| HTF CONFIRMATION                                                  |
//+------------------------------------------------------------------+
bool ConfirmHTF(int tf, int dir)
{
   int htf1=-1, htf2=-1;
   if(tf==PERIOD_M15){htf1=PERIOD_H1; htf2=PERIOD_H4;}
   if(tf==PERIOD_H1) {htf1=PERIOD_H4; htf2=PERIOD_D1;}
   if(tf==PERIOD_H4) {htf1=PERIOD_D1; htf2=PERIOD_D1;}
   if(tf==PERIOD_D1) return true;
   int t1=S_EMATrend(htf1), t2=(htf2!=htf1)?S_EMATrend(htf2):t1;
   return InpBothHTF ? (t1==dir&&t2==dir) : (t1==dir||t2==dir);
}

//+------------------------------------------------------------------+
//| CALC SL/TP                                                        |
//+------------------------------------------------------------------+
void CalcSLTP(int tf, int dir, double &sl, double &tp)
{
   double atr  = iATR(NULL,tf,InpATRPeriod,1);
   double bid  = MarketInfo(Symbol(),MODE_BID);
   double dist = atr * InpATRMult;
   int    digs = (int)MarketInfo(Symbol(),MODE_DIGITS);
   long   stop = (long)MarketInfo(Symbol(),MODE_STOPLEVEL);
   double mDist= stop * MarketInfo(Symbol(),MODE_POINT);
   if(dist < mDist) dist = mDist * 1.2;
   sl = dir==1 ? NormalizeDouble(bid-dist,digs) : NormalizeDouble(bid+dist,digs);
   tp = InpTPEnabled ?
        (dir==1 ? NormalizeDouble(bid+dist*InpTPRR,digs) :
                  NormalizeDouble(bid-dist*InpTPRR,digs)) : 0;
   g_LastSL=sl; g_LastTP=tp;
}

//+------------------------------------------------------------------+
//| CALC LOT SIZE                                                     |
//+------------------------------------------------------------------+
double CalcLots(double slPrice)
{
   double balance = AccountBalance();
   double risk    = MathMin(balance * InpRiskPercent/100.0, InpMaxLossPerTrade);
   double bid     = MarketInfo(Symbol(),MODE_BID);
   double tv      = MarketInfo(Symbol(),MODE_TICKVALUE);
   double ts      = MarketInfo(Symbol(),MODE_TICKSIZE);
   double minL    = MarketInfo(Symbol(),MODE_MINLOT);
   double maxL    = MathMin(InpMaxLotSize, MarketInfo(Symbol(),MODE_MAXLOT));
   double step    = MarketInfo(Symbol(),MODE_LOTSTEP);
   if(tv<=0||ts<=0) return minL;
   double slPts   = MathAbs(bid-slPrice)/ts;
   if(slPts==0) return minL;
   double lots    = risk / (slPts * tv);
   lots = MathMax(minL, MathMin(maxL, lots));
   return NormalizeDouble(MathFloor(lots/step)*step, 2);
}

//+------------------------------------------------------------------+
//| PLACE ORDER                                                       |
//+------------------------------------------------------------------+
void PlaceOrder(int dir, double lots, double sl, double tp, int tf)
{
   int type  = dir==1 ? OP_BUY : OP_SELL;
   double px = dir==1 ? MarketInfo(Symbol(),MODE_ASK) : MarketInfo(Symbol(),MODE_BID);
   string cmt= "DeltaForge|TF" + IntegerToString(tf);
   int ticket = OrderSend(Symbol(),type,lots,px,20,sl,tp,cmt,g_Magic,0,
                          dir==1?clrLime:clrRed);
   if(ticket > 0) {
      Print("DeltaForge MT4: Order #",ticket," ",dir==1?"BUY":"SELL",
            " Lots:",lots," SL:",sl," TP:",tp);
      PanelLastTrade(dir,lots,sl,tp);
   } else
      Print("DeltaForge MT4: OrderSend failed, error=",GetLastError());
}

//+------------------------------------------------------------------+
//| RISK CHECKS                                                       |
//+------------------------------------------------------------------+
bool CanPlaceOrder(int dir)
{
   int total=0,pairs=0,buys=0,sells=0;
   for(int i=0;i<OrdersTotal();i++){
      if(!OrderSelect(i,SELECT_BY_POS,MODE_TRADES)) continue;
      total++;
      if(OrderSymbol()==Symbol()){
         pairs++;
         if(OrderType()==OP_BUY)  buys++;
         if(OrderType()==OP_SELL) sells++;
      }
   }
   if(total>=InpMaxTotalOrders){Print("Max total orders");return false;}
   if(pairs>=InpMaxOrdersPerPair){Print("Max pair orders");return false;}
   if(dir==1  && buys>=InpMaxBuyOrders) {Print("Max buy orders"); return false;}
   if(dir==-1 && sells>=InpMaxSellOrders){Print("Max sell orders");return false;}
   return true;
}

//+------------------------------------------------------------------+
//| MANUAL TRADE CHECK (auto SL/TP on non-EA trades)                  |
//+------------------------------------------------------------------+
void CheckManualTrades()
{
   for(int i=0;i<OrdersTotal();i++){
      if(!OrderSelect(i,SELECT_BY_POS,MODE_TRADES)) continue;
      if(OrderSymbol()!=Symbol()) continue;
      if(OrderMagicNumber()==g_Magic) continue;
      double oSL=OrderStopLoss(), oTP=OrderTakeProfit();
      if(oSL==0||oTP==0){
         int dir=OrderType()==OP_BUY?1:-1;
         double sl=0,tp=0;
         CalcSLTP(PERIOD_H1,dir,sl,tp);
         if(oSL==0) oSL=sl;
         if(oTP==0) oTP=tp;
         bool ok=OrderModify(OrderTicket(),OrderOpenPrice(),oSL,oTP,0,clrYellow);
         if(ok) Print("DeltaForge MT4: Auto SL/TP on manual trade #",OrderTicket());
      }
   }
}

//+------------------------------------------------------------------+
//| TRAIL STOP MANAGEMENT                                             |
//+------------------------------------------------------------------+
void ManageTrails()
{
   for(int i=0;i<OrdersTotal();i++){
      if(!OrderSelect(i,SELECT_BY_POS,MODE_TRADES)) continue;
      if(OrderSymbol()!=Symbol()) continue;
      double oSL=OrderStopLoss(),oTP=OrderTakeProfit();
      double bid=MarketInfo(Symbol(),MODE_BID);
      double ask=MarketInfo(Symbol(),MODE_ASK);
      double atr=iATR(NULL,PERIOD_H1,InpATRPeriod,1);
      double tv=MarketInfo(Symbol(),MODE_TICKVALUE);
      double ts=MarketInfo(Symbol(),MODE_TICKSIZE);
      double newSL=0;
      int digs=(int)MarketInfo(Symbol(),MODE_DIGITS);

      if(OrderType()==OP_BUY){
         switch(InpTrailType){
            case 0: newSL=bid-atr*InpATRMult; break;
            case 1: newSL=bid*(1-InpTrailPercent/100); break;
            case 2: newSL=(tv>0&&ts>0)?bid-InpTrailDollar/(tv/ts):bid-atr*InpATRMult; break;
            case 3: { // Time-tightening
               double elapsed=((double)(TimeCurrent()-OrderOpenTime()))/3600.0;
               double maxH=InpTrailTimeMins/60.0;
               double tighten=MathMin(1.0,elapsed/MathMax(maxH,0.001));
               newSL=bid-(atr*InpATRMult*(1.0-tighten*0.5));
            } break;
            case 4: newSL=bid-atr*InpVolatilityMult; break;  // Volatility
            default: newSL=bid-atr*InpATRMult; break;
         }
         newSL=NormalizeDouble(newSL,digs);
         if(newSL>oSL&&newSL<bid){
            double prevSL=oSL;
            if(OrderModify(OrderTicket(),OrderOpenPrice(),newSL,oTP,0,clrOrange)){
               // Display trail update event on chart
               string msg="TRAIL ▲ BUY SL: "+DoubleToStr(prevSL,digs)
                          +" → "+DoubleToStr(newSL,digs);
               Print("[DELTAFORGE] ",msg);
               Comment("[DeltaForge] "+msg);
               ObjectSetString(0,g_prefix+"LV",OBJPROP_TEXT," "+msg);
               ObjectSetInteger(0,g_prefix+"LV",OBJPROP_COLOR,clrOrange);
               ChartRedraw(0);
            }
         }
      }
      else if(OrderType()==OP_SELL){
         switch(InpTrailType){
            case 0: newSL=ask+atr*InpATRMult; break;
            case 1: newSL=ask*(1+InpTrailPercent/100); break;
            case 2: newSL=(tv>0&&ts>0)?ask+InpTrailDollar/(tv/ts):ask+atr*InpATRMult; break;
            case 3: { // Time-tightening
               double elapsed=((double)(TimeCurrent()-OrderOpenTime()))/3600.0;
               double maxH=InpTrailTimeMins/60.0;
               double tighten=MathMin(1.0,elapsed/MathMax(maxH,0.001));
               newSL=ask+(atr*InpATRMult*(1.0-tighten*0.5));
            } break;
            case 4: newSL=ask+atr*InpVolatilityMult; break;  // Volatility
            default: newSL=ask+atr*InpATRMult; break;
         }
         newSL=NormalizeDouble(newSL,digs);
         if(newSL<oSL&&newSL>ask){
            double prevSL=oSL;
            if(OrderModify(OrderTicket(),OrderOpenPrice(),newSL,oTP,0,clrOrange)){
               string msg="TRAIL ▼ SELL SL: "+DoubleToStr(prevSL,digs)
                          +" → "+DoubleToStr(newSL,digs);
               Print("[DELTAFORGE] ",msg);
               Comment("[DeltaForge] "+msg);
               ObjectSetString(0,g_prefix+"LV",OBJPROP_TEXT," "+msg);
               ObjectSetInteger(0,g_prefix+"LV",OBJPROP_COLOR,clrOrange);
               ChartRedraw(0);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| PANEL FUNCTIONS                                                   |
//+------------------------------------------------------------------+
void CreateLbl(string n,string t,int x,int y,int sz,color c){
   if(ObjectFind(0,n)<0) ObjectCreate(0,n,OBJ_LABEL,0,0,0);
   ObjectSetString(0,n,OBJPROP_TEXT,t); ObjectSetInteger(0,n,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,n,OBJPROP_YDISTANCE,y); ObjectSetInteger(0,n,OBJPROP_FONTSIZE,sz);
   ObjectSetString(0,n,OBJPROP_FONT,"Consolas"); ObjectSetInteger(0,n,OBJPROP_COLOR,c);
   ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_LEFT_UPPER);
}
void CreateRect4(string n,int x,int y,int w,int h,color bg){
   if(ObjectFind(0,n)<0) ObjectCreate(0,n,OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,n,OBJPROP_XDISTANCE,x); ObjectSetInteger(0,n,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,n,OBJPROP_XSIZE,w); ObjectSetInteger(0,n,OBJPROP_YSIZE,h);
   ObjectSetInteger(0,n,OBJPROP_BGCOLOR,bg); ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_LEFT_UPPER);
}
void BuildPanel(){
   int px=InpPanelX, py=InpPanelY;
   CreateRect4(g_prefix+"BG",px,py,320,340,C'15,20,30');
   CreateRect4(g_prefix+"HD",px,py,320,26,C'20,100,160');
   CreateLbl(g_prefix+"T1","  DeltaForge AI Bot v1.0 [MT4]",px+4,py+5,9,clrWhite);
   CreateRect4(g_prefix+"SBG",px,py+28,320,22,g_BotRunning?C'0,80,0':C'120,0,0');
   CreateLbl(g_prefix+"SLB","  STATUS: "+(g_BotRunning?"RUNNING":"STOPPED"),px+4,py+33,9,g_BotRunning?clrLime:clrRed);
   if(ObjectFind(0,g_prefix+"BtnToggle")<0)ObjectCreate(0,g_prefix+"BtnToggle",OBJ_BUTTON,0,0,0);
   ObjectSetString(0,g_prefix+"BtnToggle",OBJPROP_TEXT,g_BotRunning?"STOP":"START");
   ObjectSetInteger(0,g_prefix+"BtnToggle",OBJPROP_XDISTANCE,px+244);
   ObjectSetInteger(0,g_prefix+"BtnToggle",OBJPROP_YDISTANCE,py+29);
   ObjectSetInteger(0,g_prefix+"BtnToggle",OBJPROP_XSIZE,72); ObjectSetInteger(0,g_prefix+"BtnToggle",OBJPROP_YSIZE,20);
   ObjectSetInteger(0,g_prefix+"BtnToggle",OBJPROP_BGCOLOR,g_BotRunning?C'150,0,0':C'0,120,0');
   ObjectSetInteger(0,g_prefix+"BtnToggle",OBJPROP_COLOR,clrWhite);
   CreateLbl(g_prefix+"PL","  Price:",px+4,py+55,8,clrSilver);
   CreateLbl(g_prefix+"PR","---",px+80,py+55,9,clrWhite);
   CreateLbl(g_prefix+"SH","  SIGNAL | M15  H1  H4  D1",px+4,py+78,8,clrSilver);
   CreateLbl(g_prefix+"Sm","  M15:",px+4,py+94,8,clrSilver);   CreateLbl(g_prefix+"Sv0","---",px+70,py+94,9,clrGray);
   CreateLbl(g_prefix+"S1","  H1 :",px+4,py+110,8,clrSilver);  CreateLbl(g_prefix+"Sv1","---",px+70,py+110,9,clrGray);
   CreateLbl(g_prefix+"S4","  H4 :",px+4,py+126,8,clrSilver);  CreateLbl(g_prefix+"Sv2","---",px+70,py+126,9,clrGray);
   CreateLbl(g_prefix+"Sd","  D1 :",px+4,py+142,8,clrSilver);  CreateLbl(g_prefix+"Sv3","---",px+70,py+142,9,clrGray);
   CreateLbl(g_prefix+"CL","  Confluence:",px+4,py+162,8,clrSilver); CreateLbl(g_prefix+"CV","---",px+110,py+162,9,clrWhite);
   CreateLbl(g_prefix+"ML","  ML Score:",px+4,py+178,8,clrSilver);   CreateLbl(g_prefix+"MV","---",px+110,py+178,9,clrWhite);
   CreateLbl(g_prefix+"SLL","  Sugg. SL:",px+4,py+198,8,clrSilver); CreateLbl(g_prefix+"SLV","---",px+110,py+198,9,clrOrangeRed);
   CreateLbl(g_prefix+"TPL","  Sugg. TP:",px+4,py+214,8,clrSilver); CreateLbl(g_prefix+"TPV","---",px+110,py+214,9,clrDodgerBlue);
   CreateLbl(g_prefix+"LH","  Last Trade:",px+4,py+234,8,clrSilver); CreateLbl(g_prefix+"LV","---",px+4,py+250,9,clrWhite);
   CreateLbl(g_prefix+"STH","  Strategies:",px+4,py+270,8,clrSilver); CreateLbl(g_prefix+"STV","---",px+4,py+286,7,clrLightBlue);
   if(ObjectFind(0,g_prefix+"BtnScan")<0)ObjectCreate(0,g_prefix+"BtnScan",OBJ_BUTTON,0,0,0);
   ObjectSetString(0,g_prefix+"BtnScan",OBJPROP_TEXT,"SCAN NOW");
   ObjectSetInteger(0,g_prefix+"BtnScan",OBJPROP_XDISTANCE,px+234);
   ObjectSetInteger(0,g_prefix+"BtnScan",OBJPROP_YDISTANCE,py+312);
   ObjectSetInteger(0,g_prefix+"BtnScan",OBJPROP_XSIZE,82); ObjectSetInteger(0,g_prefix+"BtnScan",OBJPROP_YSIZE,22);
   ObjectSetInteger(0,g_prefix+"BtnScan",OBJPROP_BGCOLOR,C'20,60,120'); ObjectSetInteger(0,g_prefix+"BtnScan",OBJPROP_COLOR,clrWhite);
   ChartRedraw(0);
}
void PanelStatus(bool run, string msg){
   ObjectSetInteger(0,g_prefix+"SBG",OBJPROP_BGCOLOR,run?C'0,80,0':C'120,0,0');
   ObjectSetString(0,g_prefix+"SLB",OBJPROP_TEXT,"  STATUS: "+msg);
   ObjectSetInteger(0,g_prefix+"SLB",OBJPROP_COLOR,run?clrLime:clrRed);
   ObjectSetString(0,g_prefix+"BtnToggle",OBJPROP_TEXT,run?"STOP":"START");
   ObjectSetInteger(0,g_prefix+"BtnToggle",OBJPROP_BGCOLOR,run?C'150,0,0':C'0,120,0');
   ChartRedraw(0);
}
void PanelUpdatePrice(double bid, double ask){
   ObjectSetString(0,g_prefix+"PR",OBJPROP_TEXT,
      DoubleToStr(bid,Digits)+" / "+DoubleToStr(ask,Digits));
   ChartRedraw(0);
}
void PanelUpdateSignal(int tf,int dir,double conf,double ml,double prob,string hits){
   string key="",txt="",clabel="";
   color  c=clrGray;
   if(dir==1){txt="BUY";c=clrLime;}else if(dir==-1){txt="SELL";c=clrRed;}else{txt="WAIT";}
   switch(tf){
      case PERIOD_M15: key="Sv0"; break;
      case PERIOD_H1:  key="Sv1"; break;
      case PERIOD_H4:  key="Sv2"; break;
      case PERIOD_D1:  key="Sv3"; break;
   }
   if(key!=""){ObjectSetString(0,g_prefix+key,OBJPROP_TEXT,txt); ObjectSetInteger(0,g_prefix+key,OBJPROP_COLOR,c);}
   ObjectSetString(0,g_prefix+"CV",OBJPROP_TEXT,DoubleToStr(conf,1)+"%");
   ObjectSetString(0,g_prefix+"MV",OBJPROP_TEXT,DoubleToStr(ml,1)+"%");
   ObjectSetInteger(0,g_prefix+"MV",OBJPROP_COLOR,ml>=70?clrLime:ml>=50?clrYellow:clrOrangeRed);
   ObjectSetString(0,g_prefix+"SLV",OBJPROP_TEXT,DoubleToStr(g_LastSL,Digits));
   ObjectSetString(0,g_prefix+"TPV",OBJPROP_TEXT,DoubleToStr(g_LastTP,Digits));
   ObjectSetString(0,g_prefix+"STV",OBJPROP_TEXT,StringSubstr(hits,0,55));
   ChartRedraw(0);
}
void PanelLastTrade(int dir,double lots,double sl,double tp){
   string t=(dir==1?"BUY":"SELL")+" | SL:"+DoubleToStr(sl,Digits)+" TP:"+DoubleToStr(tp,Digits);
   ObjectSetString(0,g_prefix+"LV",OBJPROP_TEXT,"  "+t);
   ObjectSetInteger(0,g_prefix+"LV",OBJPROP_COLOR,dir==1?clrLime:clrRed);
   ChartRedraw(0);
}
