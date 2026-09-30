//+------------------------------------------------------------------+
//|                                                  Strategies.mqh  |
//|              DeltaForge - 23 Strategy Implementations                |
//+------------------------------------------------------------------+
#pragma once

enum ENUM_SIGNAL   { SIGNAL_NONE = 0, SIGNAL_BUY = 1, SIGNAL_SELL = -1 };
enum ENUM_TRAIL_TYPE {
   TRAIL_ATR       = 0,
   TRAIL_PERCENT   = 1,
   TRAIL_DOLLAR    = 2,
   TRAIL_TIME      = 3,
   TRAIL_VOLATILITY= 4
};

struct SSignalResult {
   ENUM_SIGNAL direction;
   double      confluence;
   double      ml_score;
   string      strategy_hits;
   double      suggested_sl;
   double      suggested_tp;
   double      probability;
};

//+------------------------------------------------------------------+
//| CStrategies - Central strategy calculation class                  |
//+------------------------------------------------------------------+
class CStrategies
{
private:
   string         m_symbol;
   int            m_atr_period;

   // Indicator handles
   int            h_MA_Fast, h_MA_Slow;
   int            h_EMA20, h_EMA50, h_EMA200;
   int            h_MACD;
   int            h_ADX;
   int            h_SAR;
   int            h_RSI;
   int            h_Stoch;
   int            h_Momentum;
   int            h_BB;
   int            h_ATR;
   int            h_Ichimoku;

   // Cache maps: tf -> handle
   // We create handles per timeframe on demand
   void ReleaseHandles()
   {
      IndicatorRelease(h_MA_Fast);  IndicatorRelease(h_MA_Slow);
      IndicatorRelease(h_EMA20);    IndicatorRelease(h_EMA50);
      IndicatorRelease(h_EMA200);   IndicatorRelease(h_MACD);
      IndicatorRelease(h_ADX);      IndicatorRelease(h_SAR);
      IndicatorRelease(h_RSI);      IndicatorRelease(h_Stoch);
      IndicatorRelease(h_Momentum); IndicatorRelease(h_BB);
      IndicatorRelease(h_ATR);      IndicatorRelease(h_Ichimoku);
   }

   double iVal(int handle, int shift = 1)
   {
      double buf[];
      if(CopyBuffer(handle, 0, shift, 1, buf) <= 0) return EMPTY_VALUE;
      return buf[0];
   }
   double iVal2(int handle, int buf_idx, int shift = 1)
   {
      double buf[];
      if(CopyBuffer(handle, buf_idx, shift, 1, buf) <= 0) return EMPTY_VALUE;
      return buf[0];
   }

public:
   CStrategies(string symbol, int atr_period)
   {
      m_symbol     = symbol;
      m_atr_period = atr_period;
      InitHandles(PERIOD_M15);
   }

   ~CStrategies() { ReleaseHandles(); }

   void InitHandles(ENUM_TIMEFRAMES tf)
   {
      ReleaseHandles();
      h_MA_Fast  = iMA(m_symbol, tf, 10, 0, MODE_SMA,   PRICE_CLOSE);
      h_MA_Slow  = iMA(m_symbol, tf, 50, 0, MODE_SMA,   PRICE_CLOSE);
      h_EMA20    = iMA(m_symbol, tf, 20, 0, MODE_EMA,   PRICE_CLOSE);
      h_EMA50    = iMA(m_symbol, tf, 50, 0, MODE_EMA,   PRICE_CLOSE);
      h_EMA200   = iMA(m_symbol, tf, 200,0, MODE_EMA,   PRICE_CLOSE);
      h_MACD     = iMACD(m_symbol, tf, 12, 26, 9, PRICE_CLOSE);
      h_ADX      = iADX(m_symbol, tf, 14);
      h_SAR      = iSAR(m_symbol, tf, 0.02, 0.2);
      h_RSI      = iRSI(m_symbol, tf, 14, PRICE_CLOSE);
      h_Stoch    = iStochastic(m_symbol, tf, 14, 3, 3, MODE_SMA, STO_LOWHIGH);
      h_Momentum = iMomentum(m_symbol, tf, 14, PRICE_CLOSE);
      h_BB       = iBands(m_symbol, tf, 20, 0, 2.0, PRICE_CLOSE);
      h_ATR      = iATR(m_symbol, tf, m_atr_period);
      h_Ichimoku = iIchimoku(m_symbol, tf, 9, 26, 52);
   }

   //-------------------------------------------------------------------
   // 1. MOVING AVERAGE CROSSOVER
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetMA_Cross(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double fast1 = iVal(h_MA_Fast, 1), fast2 = iVal(h_MA_Fast, 2);
      double slow1 = iVal(h_MA_Slow, 1), slow2 = iVal(h_MA_Slow, 2);
      if(fast1 == EMPTY_VALUE || slow1 == EMPTY_VALUE) return SIGNAL_NONE;
      if(fast2 < slow2 && fast1 > slow1) return SIGNAL_BUY;
      if(fast2 > slow2 && fast1 < slow1) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 2. EMA TREND FOLLOWING (20/50/200 alignment)
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetEMA_Trend(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double e20 = iVal(h_EMA20), e50 = iVal(h_EMA50), e200 = iVal(h_EMA200);
      if(e20 == EMPTY_VALUE) return SIGNAL_NONE;
      double price = iClose(m_symbol, tf, 1);
      if(price > e20 && e20 > e50 && e50 > e200) return SIGNAL_BUY;
      if(price < e20 && e20 < e50 && e50 < e200) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 3. MACD SIGNAL LINE CROSS
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetMACD(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double main1 = iVal2(h_MACD, 0, 1), main2 = iVal2(h_MACD, 0, 2);
      double sig1  = iVal2(h_MACD, 1, 1), sig2  = iVal2(h_MACD, 1, 2);
      if(main1 == EMPTY_VALUE) return SIGNAL_NONE;
      if(main2 < sig2 && main1 > sig1) return SIGNAL_BUY;
      if(main2 > sig2 && main1 < sig1) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 4. ADX TREND STRENGTH (filter only - confirms trend exists)
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetADX(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double adx   = iVal2(h_ADX, 0, 1);
      double diPlus= iVal2(h_ADX, 1, 1);
      double diMinus=iVal2(h_ADX, 2, 1);
      if(adx == EMPTY_VALUE) return SIGNAL_NONE;
      if(adx > 25 && diPlus  > diMinus) return SIGNAL_BUY;
      if(adx > 25 && diMinus > diPlus)  return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 5. PARABOLIC SAR
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetParabolicSAR(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double sar   = iVal(h_SAR, 1);
      double price = iClose(m_symbol, tf, 1);
      if(sar == EMPTY_VALUE) return SIGNAL_NONE;
      double sarPrev = iVal(h_SAR, 2);
      double pricePrev = iClose(m_symbol, tf, 2);
      // Flip detection
      if(sarPrev > pricePrev && sar < price) return SIGNAL_BUY;
      if(sarPrev < pricePrev && sar > price) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 6. RSI OVERBOUGHT/OVERSOLD
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetRSI(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double rsi1 = iVal(h_RSI, 1), rsi2 = iVal(h_RSI, 2);
      if(rsi1 == EMPTY_VALUE) return SIGNAL_NONE;
      if(rsi2 < 30 && rsi1 > 30) return SIGNAL_BUY;   // Oversold bounce
      if(rsi2 > 70 && rsi1 < 70) return SIGNAL_SELL;  // Overbought fade
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 7. STOCHASTIC OSCILLATOR
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetStochastic(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double k1 = iVal2(h_Stoch, 0, 1), k2 = iVal2(h_Stoch, 0, 2);
      double d1 = iVal2(h_Stoch, 1, 1), d2 = iVal2(h_Stoch, 1, 2);
      if(k1 == EMPTY_VALUE) return SIGNAL_NONE;
      if(k1 < 20 && d1 < 20 && k2 < d2 && k1 > d1) return SIGNAL_BUY;
      if(k1 > 80 && d1 > 80 && k2 > d2 && k1 < d1) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 8. MOMENTUM INDICATOR
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetMomentum(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double m1 = iVal(h_Momentum, 1);
      double m2 = iVal(h_Momentum, 2);
      if(m1 == EMPTY_VALUE) return SIGNAL_NONE;
      if(m1 > 100 && m2 < 100) return SIGNAL_BUY;
      if(m1 < 100 && m2 > 100) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 9. BOLLINGER BANDS REVERSAL
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetBollingerBands(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double upper = iVal2(h_BB, 1, 1);
      double lower = iVal2(h_BB, 2, 1);
      double close1= iClose(m_symbol, tf, 1);
      double close2= iClose(m_symbol, tf, 2);
      if(upper == EMPTY_VALUE) return SIGNAL_NONE;
      // Price touches lower band and closes back inside
      if(close2 <= lower && close1 > lower) return SIGNAL_BUY;
      if(close2 >= upper && close1 < upper) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 10. ATR VOLATILITY BREAKOUT
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetATRBreakout(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double atr    = iVal(h_ATR, 1);
      double high1  = iHigh(m_symbol, tf, 1);
      double low1   = iLow( m_symbol, tf, 1);
      double high20 = 0, low20 = 999999;
      for(int i = 2; i <= 20; i++) {
         double h = iHigh(m_symbol, tf, i);
         double l = iLow( m_symbol, tf, i);
         if(h > high20) high20 = h;
         if(l < low20)  low20  = l;
      }
      if(atr == EMPTY_VALUE) return SIGNAL_NONE;
      double close = iClose(m_symbol, tf, 1);
      if(close > high20 + atr * 0.5) return SIGNAL_BUY;
      if(close < low20  - atr * 0.5) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 11. ACCUMULATION / DISTRIBUTION LINE
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetAccumDist(ENUM_TIMEFRAMES tf)
   {
      // Compute simplified A/D: CLV direction over 5 bars
      double ad1 = 0, ad5 = 0;
      for(int i = 1; i <= 5; i++) {
         double h = iHigh(m_symbol, tf, i);
         double l = iLow( m_symbol, tf, i);
         double c = iClose(m_symbol, tf, i);
         double v = (double)iVolume(m_symbol, tf, i);
         double hl = h - l;
         if(hl == 0) continue;
         double clv = ((c - l) - (h - c)) / hl;
         if(i <= 2) ad1 += clv * v;
         ad5 += clv * v;
      }
      if(ad5 == 0) return SIGNAL_NONE;
      if(ad1 > 0 && ad5 > 0) return SIGNAL_BUY;
      if(ad1 < 0 && ad5 < 0) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 12. CHAIKIN MONEY FLOW
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetChaikinMF(ENUM_TIMEFRAMES tf)
   {
      double sumMFV = 0, sumVol = 0;
      for(int i = 1; i <= 20; i++) {
         double h = iHigh(m_symbol, tf, i);
         double l = iLow( m_symbol, tf, i);
         double c = iClose(m_symbol, tf, i);
         double v = (double)iVolume(m_symbol, tf, i);
         double hl = h - l;
         if(hl == 0) continue;
         sumMFV += ((c - l) - (h - c)) / hl * v;
         sumVol += v;
      }
      if(sumVol == 0) return SIGNAL_NONE;
      double cmf = sumMFV / sumVol;
      if(cmf > 0.05) return SIGNAL_BUY;
      if(cmf < -0.05)return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 13. FIBONACCI RETRACEMENT
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetFibonacci(ENUM_TIMEFRAMES tf)
   {
      // Find swing high/low over 50 bars
      double swingH = 0, swingL = 999999;
      for(int i = 1; i <= 50; i++) {
         double h = iHigh(m_symbol, tf, i);
         double l = iLow( m_symbol, tf, i);
         if(h > swingH) swingH = h;
         if(l < swingL) swingL = l;
      }
      double range  = swingH - swingL;
      double close  = iClose(m_symbol, tf, 1);
      // Key Fib levels
      double fib382 = swingH - range * 0.382;
      double fib500 = swingH - range * 0.500;
      double fib618 = swingH - range * 0.618;
      double tol    = range * 0.015; // 1.5% tolerance

      if(MathAbs(close - fib618) < tol || MathAbs(close - fib500) < tol)
         return SIGNAL_BUY;
      if(MathAbs(close - fib382) < tol && close < fib500)
         return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 14. PIVOT POINTS
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetPivotPoints(ENUM_TIMEFRAMES tf)
   {
      double prevH = iHigh(m_symbol, tf, 1);
      double prevL = iLow( m_symbol, tf, 1);
      double prevC = iClose(m_symbol, tf, 1);
      double pivot  = (prevH + prevL + prevC) / 3.0;
      double r1     = 2 * pivot - prevL;
      double s1     = 2 * pivot - prevH;
      double close  = iClose(m_symbol, tf, 0);
      double tol    = iATR(m_symbol, tf, 14) == INVALID_HANDLE ? 0.001 : 0.0010;

      if(close > pivot && MathAbs(close - pivot) < tol) return SIGNAL_BUY;
      if(close < pivot && MathAbs(close - pivot) < tol) return SIGNAL_SELL;
      if(close > s1   && MathAbs(close - s1) < tol)    return SIGNAL_BUY;
      if(close < r1   && MathAbs(close - r1) < tol)    return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 15. SUPPORT & RESISTANCE ZONES
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetSupportResist(ENUM_TIMEFRAMES tf)
   {
      double close = iClose(m_symbol, tf, 1);
      double atr   = iVal(h_ATR, 1);
      if(atr == EMPTY_VALUE) return SIGNAL_NONE;

      // Identify levels as local pivot highs/lows over 100 bars
      int touchBuy = 0, touchSell = 0;
      for(int i = 3; i <= 100; i++) {
         double h = iHigh(m_symbol, tf, i);
         double l = iLow( m_symbol, tf, i);
         if(MathAbs(close - l) < atr * 0.5) touchBuy++;
         if(MathAbs(close - h) < atr * 0.5) touchSell++;
      }
      if(touchBuy  >= 3) return SIGNAL_BUY;  // Price at support
      if(touchSell >= 3) return SIGNAL_SELL; // Price at resistance
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 16. ICHIMOKU CLOUD
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetIchimoku(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      // Buffer indices: 0=Tenkan, 1=Kijun, 2=SpanA, 3=SpanB, 4=Chikou
      double tenkan   = iVal2(h_Ichimoku, 0, 1);
      double kijun    = iVal2(h_Ichimoku, 1, 1);
      double spanA    = iVal2(h_Ichimoku, 2, 1);
      double spanB    = iVal2(h_Ichimoku, 3, 1);
      double close    = iClose(m_symbol, tf, 1);

      if(tenkan == EMPTY_VALUE) return SIGNAL_NONE;
      double cloudTop = MathMax(spanA, spanB);
      double cloudBot = MathMin(spanA, spanB);

      if(close > cloudTop && tenkan > kijun) return SIGNAL_BUY;
      if(close < cloudBot && tenkan < kijun) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 17. BREAKOUT TRADING (range high/low break)
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetBreakout(ENUM_TIMEFRAMES tf)
   {
      double close = iClose(m_symbol, tf, 1);
      double high20= 0, low20 = 999999;
      for(int i = 2; i <= 20; i++) {
         double h = iHigh(m_symbol, tf, i);
         double l = iLow( m_symbol, tf, i);
         if(h > high20) high20 = h;
         if(l < low20)  low20  = l;
      }
      double atr = iVal(h_ATR, 1);
      if(atr == EMPTY_VALUE) return SIGNAL_NONE;
      if(close > high20 + atr * 0.3) return SIGNAL_BUY;
      if(close < low20  - atr * 0.3) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 18. TRENDLINE TRADING (using EMA as proxy trendline)
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetTrendline(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double e50_1 = iVal(h_EMA50, 1), e50_2 = iVal(h_EMA50, 2);
      double close = iClose(m_symbol, tf, 1);
      double prev  = iClose(m_symbol, tf, 2);
      if(e50_1 == EMPTY_VALUE) return SIGNAL_NONE;
      // Price crossing back above EMA50 after pullback
      if(prev < e50_2 && close > e50_1) return SIGNAL_BUY;
      if(prev > e50_2 && close < e50_1) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 19. VOLUME BREAKOUT
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetVolumeBreakout(ENUM_TIMEFRAMES tf)
   {
      double avgVol = 0;
      for(int i = 2; i <= 21; i++)
         avgVol += (double)iVolume(m_symbol, tf, i);
      avgVol /= 20.0;
      double curVol = (double)iVolume(m_symbol, tf, 1);
      double close  = iClose(m_symbol, tf, 1);
      double prev   = iClose(m_symbol, tf, 2);
      if(curVol > avgVol * 1.8) { // 80% above average volume
         if(close > prev) return SIGNAL_BUY;
         if(close < prev) return SIGNAL_SELL;
      }
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 20. PULLBACK TRADING
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetPullback(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double e200 = iVal(h_EMA200, 1);
      double e50  = iVal(h_EMA50,  1);
      double close = iClose(m_symbol, tf, 1);
      if(e200 == EMPTY_VALUE) return SIGNAL_NONE;
      // In uptrend: price pulls back to EMA50 but EMA50 > EMA200
      if(e50 > e200 && MathAbs(close - e50) < e50 * 0.002) return SIGNAL_BUY;
      if(e50 < e200 && MathAbs(close - e50) < e50 * 0.002) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 21. SMART MONEY CONCEPTS (SMC): Fair Value Gaps + Order Blocks
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetSMC(ENUM_TIMEFRAMES tf)
   {
      // Fair Value Gap: gap between candle i+2 high and candle i low
      for(int i = 3; i <= 10; i++) {
         double h_before = iHigh(m_symbol, tf, i+1);
         double l_after  = iLow( m_symbol, tf, i-1);
         double l_before = iLow( m_symbol, tf, i+1);
         double h_after  = iHigh(m_symbol, tf, i-1);
         double close    = iClose(m_symbol, tf, 1);
         // Bullish FVG
         if(l_after > h_before && close >= h_before && close <= l_after)
            return SIGNAL_BUY;
         // Bearish FVG
         if(h_after < l_before && close <= l_before && close >= h_after)
            return SIGNAL_SELL;
      }
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 22. ORDER FLOW / LIQUIDITY SWEEP
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetOrderFlow(ENUM_TIMEFRAMES tf)
   {
      // Liquidity sweep: price briefly breaks a recent high/low then reverses
      double high5 = 0, low5 = 999999;
      for(int i = 2; i <= 6; i++) {
         double h = iHigh(m_symbol, tf, i);
         double l = iLow( m_symbol, tf, i);
         if(h > high5) high5 = h;
         if(l < low5)  low5  = l;
      }
      double curH  = iHigh(m_symbol,  tf, 1);
      double curL  = iLow(m_symbol,   tf, 1);
      double close = iClose(m_symbol, tf, 1);
      double atr   = iVal(h_ATR, 1);
      if(atr == EMPTY_VALUE) return SIGNAL_NONE;
      // Wick above resistance then close below = sell
      if(curH > high5 + atr*0.1 && close < high5) return SIGNAL_SELL;
      // Wick below support then close above = buy
      if(curL < low5  - atr*0.1 && close > low5)  return SIGNAL_BUY;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 23. MARKET PROFILE (Value Area approximation)
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetMarketProfile(ENUM_TIMEFRAMES tf)
   {
      // Approximate POC using highest volume price zone
      double maxVol = 0; int pocBar = 1;
      for(int i = 1; i <= 20; i++) {
         double v = (double)iVolume(m_symbol, tf, i);
         if(v > maxVol) { maxVol = v; pocBar = i; }
      }
      double poc   = (iHigh(m_symbol, tf, pocBar) + iLow(m_symbol, tf, pocBar)) / 2.0;
      double close = iClose(m_symbol, tf, 1);
      double atr   = iVal(h_ATR, 1);
      if(atr == EMPTY_VALUE) return SIGNAL_NONE;
      if(close > poc + atr * 0.3) return SIGNAL_BUY;
      if(close < poc - atr * 0.3) return SIGNAL_SELL;
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 24. LUXALGO - RSI Divergence + EMA Ribbon Confirmation
   //    Bullish: price at/below recent swing low, RSI higher than it was there.
   //    Bearish: price at/above recent swing high, RSI lower than it was there.
   //    Secondary: full EMA ribbon momentum (EMA9 > EMA21 > EMA50 = bull).
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetLuxAlgo(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double rsi1 = iVal(h_RSI, 1);
      double close1= iClose(m_symbol, tf, 1);
      if(rsi1 == EMPTY_VALUE) return SIGNAL_NONE;

      // Find swing low / swing high over last 30 bars
      double swingLowPrice = close1, swingLowRSI = rsi1;
      double swingHiPrice  = close1, swingHiRSI  = rsi1;
      for(int i = 2; i <= 30; i++)
      {
         double c = iClose(m_symbol, tf, i);
         double r = iVal(h_RSI, i);
         if(r == EMPTY_VALUE) continue;
         if(c < swingLowPrice) { swingLowPrice = c; swingLowRSI = r; }
         if(c > swingHiPrice)  { swingHiPrice  = c; swingHiRSI  = r; }
      }

      double ema20v = iVal(h_EMA20, 1);
      double ema50v = iVal(h_EMA50, 1);
      if(ema20v == EMPTY_VALUE) return SIGNAL_NONE;

      // Average volume check
      double curVol = (double)iVolume(m_symbol, tf, 1);
      double avgVol = 0;
      for(int j = 2; j <= 21; j++) avgVol += (double)iVolume(m_symbol, tf, j);
      avgVol /= 20.0;
      bool volOk = (curVol > avgVol * 1.1);

      // Bullish divergence: price near/at swing low, RSI higher now
      if(close1 <= swingLowPrice * 1.003 &&
         rsi1   >  swingLowRSI   + 3.0  &&
         rsi1   <  45.0                  &&
         ema20v >= ema50v * 0.998         &&
         volOk)
         return SIGNAL_BUY;

      // Bearish divergence: price near/at swing high, RSI lower now
      if(close1 >= swingHiPrice * 0.997 &&
         rsi1   <  swingHiRSI   - 3.0  &&
         rsi1   >  55.0                  &&
         ema20v <= ema50v * 1.002         &&
         volOk)
         return SIGNAL_SELL;

      // Secondary: EMA ribbon momentum (EMA9 < EMA20 < EMA50 etc.)
      int hEma9  = iMA(m_symbol, tf, 9,  0, MODE_EMA, PRICE_CLOSE);
      int hEma21 = iMA(m_symbol, tf, 21, 0, MODE_EMA, PRICE_CLOSE);
      double ema9v = EMPTY_VALUE, ema21v = EMPTY_VALUE;
      double buf[1];
      if(CopyBuffer(hEma9, 0, 1, 1, buf) > 0)  ema9v  = buf[0];
      if(CopyBuffer(hEma21,0, 1, 1, buf) > 0)  ema21v = buf[0];
      IndicatorRelease(hEma9); IndicatorRelease(hEma21);

      if(ema9v != EMPTY_VALUE && ema21v != EMPTY_VALUE)
      {
         double slope9p = iVal(hEma9,  1); // use cached EMA20 slope proxy
         if(ema9v > ema21v && ema21v > ema20v && ema20v > ema50v &&
            rsi1 > 50 && volOk)
            return SIGNAL_BUY;
         if(ema9v < ema21v && ema21v < ema20v && ema20v < ema50v &&
            rsi1 < 50 && volOk)
            return SIGNAL_SELL;
      }
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 25. NEWS MOMENTUM - Large Impulse Candle + Volume Surge Continuation
   //    Detects a sudden big-body candle (body > 1.8× ATR) with exceptional
   //    volume (> 2.2× 20-bar average).  Trades continuation if current
   //    price has not fully reversed.  Proxy for news-driven moves.
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetNewsMomentum(ENUM_TIMEFRAMES tf)
   {
      InitHandles(tf);
      double atr = iVal(h_ATR, 1);
      if(atr == EMPTY_VALUE || atr == 0) return SIGNAL_NONE;

      double avgVol = 0;
      for(int j = 4; j <= 23; j++) avgVol += (double)iVolume(m_symbol, tf, j);
      avgVol /= 20.0;
      if(avgVol == 0) return SIGNAL_NONE;

      double curClose = iClose(m_symbol, tf, 1);

      // Scan candles 2-4 bars back for impulse event
      for(int offset = 2; offset <= 4; offset++)
      {
         double o = iOpen(m_symbol,  tf, offset);
         double c = iClose(m_symbol, tf, offset);
         double v = (double)iVolume(m_symbol, tf, offset);
         double body = MathAbs(c - o);

         if(body < atr * 1.8 || v < avgVol * 2.2)
            continue;    // not an impulse bar

         bool isBull = (c > o);
         if(isBull  && curClose >= c * 0.995) return SIGNAL_BUY;
         if(!isBull && curClose <= c * 1.005) return SIGNAL_SELL;
      }
      return SIGNAL_NONE;
   }

   //-------------------------------------------------------------------
   // 26. QUANTITATIVE ALGO - Z-Score Mean Reversion
   //    Computes a 20-bar rolling Z-score.  When Z-score exceeds ±1.8σ
   //    and is already pulling back toward the mean, signals a reversion.
   //    Also detects momentum continuation when price is strongly trending.
   //-------------------------------------------------------------------
   ENUM_SIGNAL GetQuantAlgo(ENUM_TIMEFRAMES tf)
   {
      const int PERIOD = 20;
      const int NEED   = PERIOD + 5;
      if(iBars(m_symbol, tf) < NEED) return SIGNAL_NONE;

      // Build rolling mean and std over PERIOD bars
      double sum = 0, sumSq = 0;
      for(int k = 1; k <= PERIOD; k++)
      {
         double c = iClose(m_symbol, tf, k);
         sum   += c;
         sumSq += c * c;
      }
      double mean = sum / PERIOD;
      double var  = sumSq / PERIOD - mean * mean;
      if(var <= 0) return SIGNAL_NONE;
      double sigma = MathSqrt(var);

      double z_now  = (iClose(m_symbol, tf, 1) - mean) / sigma;
      double z_prev = (iClose(m_symbol, tf, 2) - mean) / sigma;
      double z_prv2 = (iClose(m_symbol, tf, 3) - mean) / sigma;

      const double THRESHOLD = 1.8;

      // Mean-reversion: Z was extreme and is now pulling back
      // Oversold reversion
      if(z_prv2 < -THRESHOLD && z_prev < -THRESHOLD && z_now > z_prev)
         return SIGNAL_BUY;

      // Overbought reversion
      if(z_prv2 >  THRESHOLD && z_prev >  THRESHOLD && z_now < z_prev)
         return SIGNAL_SELL;

      // Momentum mode: sustained Z in same direction
      if(z_prev > 1.5 && z_now > z_prev) return SIGNAL_BUY;
      if(z_prev <-1.5 && z_now < z_prev) return SIGNAL_SELL;

      return SIGNAL_NONE;
   }
};
