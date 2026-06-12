//+------------------------------------------------------------------+
//|                                               RiskManager.mqh   |
//|                        DeltaForge Risk Management Module             |
//+------------------------------------------------------------------+
#pragma once
#include <Trade\PositionInfo.mqh>

class CRiskManager
{
private:
   double m_maxLossPerTrade;
   double m_maxLotSize;
   int    m_maxTotalOrders;
   int    m_maxOrdersPerPair;
   int    m_maxBuyOrders;
   int    m_maxSellOrders;
   double m_riskPercent;

   CPositionInfo m_posInfo;

public:
   CRiskManager(double maxLoss, double maxLot, int maxTotal,
                int maxPerPair, int maxBuy, int maxSell, double riskPct)
   {
      m_maxLossPerTrade  = maxLoss;
      m_maxLotSize       = maxLot;
      m_maxTotalOrders   = maxTotal;
      m_maxOrdersPerPair = maxPerPair;
      m_maxBuyOrders     = maxBuy;
      m_maxSellOrders    = maxSell;
      m_riskPercent      = riskPct;
   }

   //--- Count helpers
   int CountTotalPositions()
   {
      return PositionsTotal();
   }

   int CountPairPositions(string symbol)
   {
      int n = 0;
      for(int i = 0; i < PositionsTotal(); i++) {
         if(m_posInfo.SelectByIndex(i) && m_posInfo.Symbol() == symbol)
            n++;
      }
      return n;
   }

   int CountBuyPositions(string symbol)
   {
      int n = 0;
      for(int i = 0; i < PositionsTotal(); i++) {
         if(m_posInfo.SelectByIndex(i)
         && m_posInfo.Symbol() == symbol
         && m_posInfo.PositionType() == POSITION_TYPE_BUY) n++;
      }
      return n;
   }

   int CountSellPositions(string symbol)
   {
      int n = 0;
      for(int i = 0; i < PositionsTotal(); i++) {
         if(m_posInfo.SelectByIndex(i)
         && m_posInfo.Symbol() == symbol
         && m_posInfo.PositionType() == POSITION_TYPE_SELL) n++;
      }
      return n;
   }

   //--- Main gate: can we place an order?
   bool CanPlaceOrder(string symbol, int orderType)
   {
      if(CountTotalPositions() >= m_maxTotalOrders) {
         Print("DeltaForge Risk: Max total orders reached (", m_maxTotalOrders, ")");
         return false;
      }
      if(CountPairPositions(symbol) >= m_maxOrdersPerPair) {
         Print("DeltaForge Risk: Max orders on pair reached (", m_maxOrdersPerPair, ")");
         return false;
      }
      if(orderType == ORDER_TYPE_BUY && CountBuyPositions(symbol) >= m_maxBuyOrders) {
         Print("DeltaForge Risk: Max buy orders reached (", m_maxBuyOrders, ")");
         return false;
      }
      if(orderType == ORDER_TYPE_SELL && CountSellPositions(symbol) >= m_maxSellOrders) {
         Print("DeltaForge Risk: Max sell orders reached (", m_maxSellOrders, ")");
         return false;
      }
      return true;
   }

   //--- Calculate lot size from risk%
   double CalculateLotSize(string symbol, double slPrice)
   {
      double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
      double riskAmount = MathMin(balance * m_riskPercent / 100.0, m_maxLossPerTrade);
      double bid        = SymbolInfoDouble(symbol, SYMBOL_BID);
      double tickVal    = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
      double tickSize   = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
      double minLot     = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
      double maxLot     = MathMin(m_maxLotSize, SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX));
      double lotStep    = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

      if(slPrice <= 0 || tickVal <= 0 || tickSize <= 0) return minLot;

      double slPoints = MathAbs(bid - slPrice) / tickSize;
      if(slPoints == 0) return minLot;

      double lots = riskAmount / (slPoints * tickVal);
      lots = MathMax(minLot, MathMin(maxLot, lots));
      lots = MathFloor(lots / lotStep) * lotStep;

      return NormalizeDouble(lots, 2);
   }

   //--- Get ATR value
   double GetATR(string symbol, ENUM_TIMEFRAMES tf, int period)
   {
      int handle = iATR(symbol, tf, period);
      if(handle == INVALID_HANDLE) return 0;
      double buf[];
      if(CopyBuffer(handle, 0, 1, 1, buf) <= 0) { IndicatorRelease(handle); return 0; }
      IndicatorRelease(handle);
      return buf[0];
   }

   //--- Validate that a dollar-risk loss doesn't exceed max loss
   bool ValidateLoss(string symbol, double lots, double slPrice)
   {
      double bid      = SymbolInfoDouble(symbol, SYMBOL_BID);
      double tickVal  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
      double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
      double slPoints = MathAbs(bid - slPrice) / tickSize;
      double dollarRisk = slPoints * tickVal * lots;
      if(dollarRisk > m_maxLossPerTrade) {
         Print("DeltaForge Risk: Dollar risk $", DoubleToString(dollarRisk,2),
               " > max $", DoubleToString(m_maxLossPerTrade,2));
         return false;
      }
      return true;
   }
};
