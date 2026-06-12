//+------------------------------------------------------------------+
//|                                                  MLFilter.mqh   |
//|              DeltaForge ML Signal Scoring + Anomaly Detection        |
//|  Architecture: Pre-trained logistic regression weights embedded  |
//|  Training: Run Python backtest/train_ml.py to update weights     |
//+------------------------------------------------------------------+
#pragma once

// Feature indices
#define ML_FEAT_RSI        0
#define ML_FEAT_MACD_HIST  1
#define ML_FEAT_BB_PCT     2
#define ML_FEAT_ATR_NORM   3
#define ML_FEAT_ADX        4
#define ML_FEAT_STOCH_K    5
#define ML_FEAT_VOL_RATIO  6
#define ML_FEAT_EMA_SLOPE  7
#define ML_FEAT_MOMENTUM   8
#define ML_FEAT_CONF       9
#define ML_FEAT_COUNT      10

class CMLFilter
{
private:
   double m_threshold;

   // Pre-trained logistic regression weights (updated by Python trainer)
   // Default: slightly favour confluence and RSI signals
   double m_weights[ML_FEAT_COUNT];
   double m_bias;

   // Isolation Forest approximate: track rolling std
   double m_priceHistory[100];
   int    m_histIdx;
   bool   m_histFull;

   double Sigmoid(double x)
   {
      return 1.0 / (1.0 + MathExp(-x));
   }

   double ExtractFeature(string symbol, ENUM_TIMEFRAMES tf, int feat)
   {
      switch(feat) {
         case ML_FEAT_RSI: {
            int h = iRSI(symbol, tf, 14, PRICE_CLOSE);
            double buf[]; CopyBuffer(h, 0, 1, 1, buf);
            IndicatorRelease(h);
            return (buf[0] - 50.0) / 50.0; // normalize -1 to 1
         }
         case ML_FEAT_MACD_HIST: {
            int h = iMACD(symbol, tf, 12, 26, 9, PRICE_CLOSE);
            double main[]; double sig[];
            CopyBuffer(h, 0, 1, 1, main);
            CopyBuffer(h, 1, 1, 1, sig);
            IndicatorRelease(h);
            double hist = main[0] - sig[0];
            double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
            return MathMax(-1.0, MathMin(1.0, hist / (point * 100)));
         }
         case ML_FEAT_BB_PCT: {
            int h = iBands(symbol, tf, 20, 0, 2.0, PRICE_CLOSE);
            double up[]; double lo[]; double mid[];
            CopyBuffer(h, 1, 1, 1, up);
            CopyBuffer(h, 2, 1, 1, lo);
            IndicatorRelease(h);
            double close = iClose(symbol, tf, 1);
            double range = up[0] - lo[0];
            return range > 0 ? (close - lo[0]) / range : 0.5;
         }
         case ML_FEAT_ATR_NORM: {
            int h = iATR(symbol, tf, 14);
            double buf[]; CopyBuffer(h, 0, 1, 1, buf);
            IndicatorRelease(h);
            double close = iClose(symbol, tf, 1);
            return close > 0 ? MathMin(1.0, buf[0] / close * 100) : 0;
         }
         case ML_FEAT_ADX: {
            int h = iADX(symbol, tf, 14);
            double buf[]; CopyBuffer(h, 0, 1, 1, buf);
            IndicatorRelease(h);
            return buf[0] / 100.0;
         }
         case ML_FEAT_STOCH_K: {
            int h = iStochastic(symbol, tf, 14, 3, 3, MODE_SMA, STO_LOWHIGH);
            double buf[]; CopyBuffer(h, 0, 1, 1, buf);
            IndicatorRelease(h);
            return (buf[0] - 50.0) / 50.0;
         }
         case ML_FEAT_VOL_RATIO: {
            double curVol = (double)iVolume(symbol, tf, 1);
            double avgVol = 0;
            for(int i=2; i<=11; i++) avgVol += (double)iVolume(symbol, tf, i);
            avgVol /= 10.0;
            return avgVol > 0 ? MathMin(2.0, curVol / avgVol) - 1.0 : 0;
         }
         case ML_FEAT_EMA_SLOPE: {
            int h = iMA(symbol, tf, 20, 0, MODE_EMA, PRICE_CLOSE);
            double buf[]; CopyBuffer(h, 0, 1, 2, buf);
            IndicatorRelease(h);
            double slope = buf[0] > 0 ? (buf[0] - buf[1]) / buf[0] * 100 : 0;
            return MathMax(-1.0, MathMin(1.0, slope * 10));
         }
         case ML_FEAT_MOMENTUM: {
            int h = iMomentum(symbol, tf, 14, PRICE_CLOSE);
            double buf[]; CopyBuffer(h, 0, 1, 1, buf);
            IndicatorRelease(h);
            return (buf[0] - 100.0) / 10.0;
         }
         default: return 0;
      }
   }

public:
   CMLFilter(double threshold)
   {
      m_threshold = threshold;
      m_histIdx   = 0;
      m_histFull  = false;

      // Default pre-trained weights (replace with Python-trained values)
      m_weights[ML_FEAT_RSI]       =  0.45;
      m_weights[ML_FEAT_MACD_HIST] =  0.62;
      m_weights[ML_FEAT_BB_PCT]    = -0.38;
      m_weights[ML_FEAT_ATR_NORM]  = -0.22;
      m_weights[ML_FEAT_ADX]       =  0.58;
      m_weights[ML_FEAT_STOCH_K]   =  0.33;
      m_weights[ML_FEAT_VOL_RATIO] =  0.41;
      m_weights[ML_FEAT_EMA_SLOPE] =  0.71;
      m_weights[ML_FEAT_MOMENTUM]  =  0.49;
      m_weights[ML_FEAT_CONF]      =  0.85; // Confluence is strongest predictor
      m_bias = -0.15;
   }

   //--- Score a signal 0-100
   double ScoreSignal(string symbol, ENUM_TIMEFRAMES tf, SSignalResult &sig)
   {
      double features[ML_FEAT_COUNT];
      for(int i = 0; i < ML_FEAT_COUNT-1; i++)
         features[i] = ExtractFeature(symbol, tf, i);
      features[ML_FEAT_CONF] = sig.confluence / 100.0;

      // Adjust sign for SELL signals
      double dirMult = (sig.direction == SIGNAL_SELL) ? -1.0 : 1.0;

      double z = m_bias;
      for(int i = 0; i < ML_FEAT_COUNT; i++)
         z += m_weights[i] * features[i] * dirMult;

      double prob = Sigmoid(z) * 100.0;
      sig.probability = prob;
      return prob;
   }

   //--- Load weights from file (written by Python trainer)
   bool LoadWeights(string filename)
   {
      int fh = FileOpen(filename, FILE_READ | FILE_TXT);
      if(fh == INVALID_HANDLE) {
         Print("DeltaForge ML: Weight file not found, using defaults: ", filename);
         return false;
      }
      m_bias = StringToDouble(FileReadString(fh));
      for(int i = 0; i < ML_FEAT_COUNT; i++)
         m_weights[i] = StringToDouble(FileReadString(fh));
      FileClose(fh);
      Print("DeltaForge ML: Weights loaded from ", filename);
      return true;
   }

   //--- Isolation Forest approximation: detect volatility anomalies
   bool DetectAnomaly(string symbol, ENUM_TIMEFRAMES tf)
   {
      double close = iClose(symbol, tf, 1);
      m_priceHistory[m_histIdx] = close;
      m_histIdx = (m_histIdx + 1) % 100;
      if(m_histIdx == 0) m_histFull = true;

      int n = m_histFull ? 100 : m_histIdx;
      if(n < 20) return false;

      double mean = 0;
      for(int i = 0; i < n; i++) mean += m_priceHistory[i];
      mean /= n;

      double variance = 0;
      for(int i = 0; i < n; i++)
         variance += (m_priceHistory[i] - mean) * (m_priceHistory[i] - mean);
      double std = MathSqrt(variance / n);

      if(std == 0) return false;
      double zscore = MathAbs((close - mean) / std);

      // Z-score > 3.5 = anomaly (extreme price deviation)
      if(zscore > 3.5) {
         Print("DeltaForge ML: Anomaly detected! Z-score=", DoubleToString(zscore,2));
         return true;
      }

      // Also check for spread anomaly
      double spread  = SymbolInfoInteger(symbol, SYMBOL_SPREAD) *
                       SymbolInfoDouble(symbol, SYMBOL_POINT);
      double avgSprd = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE) * 3;
      if(spread > avgSprd * 5) {
         Print("DeltaForge ML: Spread anomaly! Spread=", spread);
         return true;
      }
      return false;
   }

   //--- Update a single weight (for online learning via Python feedback loop)
   void UpdateWeight(int feat_idx, double new_weight)
   {
      if(feat_idx >= 0 && feat_idx < ML_FEAT_COUNT)
         m_weights[feat_idx] = new_weight;
   }
   void UpdateBias(double new_bias) { m_bias = new_bias; }
};
