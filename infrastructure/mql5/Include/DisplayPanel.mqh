//+------------------------------------------------------------------+
//|                                               DisplayPanel.mqh  |
//|                       DeltaForge Chart Dashboard Panel               |
//+------------------------------------------------------------------+
#pragma once

class CDisplayPanel
{
private:
   int    m_x, m_y;
   color  m_buyCol, m_sellCol, m_neutCol, m_slCol, m_tpCol;
   string m_prefix;

   void CreateLabel(string name, string text, int x, int y,
                    int fontSize, color clr, string font="Consolas")
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetString(0, name, OBJPROP_TEXT, text);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE,  fontSize);
      ObjectSetString(0, name, OBJPROP_FONT, font);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   }

   void CreateRect(string name, int x, int y, int w, int h, color bg)
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_XSIZE,   w);
      ObjectSetInteger(0, name, OBJPROP_YSIZE,   h);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
      ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clrDarkSlateGray);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_ZORDER, 0);
   }

   void CreateButton(string name, string text, int x, int y,
                     int w, int h, color bg, color txtClr)
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
      ObjectSetString(0, name, OBJPROP_TEXT,      text);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_XSIZE,    w);
      ObjectSetInteger(0, name, OBJPROP_YSIZE,    h);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR,  bg);
      ObjectSetInteger(0, name, OBJPROP_COLOR,    txtClr);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
      ObjectSetInteger(0, name, OBJPROP_CORNER,   CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   }

   void SetLabel(string name, string text, color clr)
   {
      ObjectSetString(0, name, OBJPROP_TEXT, text);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   }

public:
   CDisplayPanel(int x, int y, bool running,
                 color buyCol, color sellCol, color neutCol,
                 color slCol, color tpCol)
   {
      m_x       = x;   m_y      = y;
      m_buyCol  = buyCol;  m_sellCol = sellCol;
      m_neutCol = neutCol; m_slCol   = slCol;
      m_tpCol   = tpCol;
      m_prefix  = "DeltaForge_";
      BuildPanel(running);
   }

   ~CDisplayPanel()
   {
      ObjectsDeleteAll(0, m_prefix);
   }

   void BuildPanel(bool running)
   {
      int px = m_x, py = m_y;
      int W  = 320, H = 380;

      // Background
      CreateRect(m_prefix+"BG",    px, py, W, H, C'15,20,30');
      CreateRect(m_prefix+"Title", px, py, W, 28, C'20,100,160');

      // Title
      CreateLabel(m_prefix+"TitleTxt","  DeltaForge Agentic AI Bot v1.0",
                  px+4, py+6, 9, clrWhite);

      // Status row
      CreateRect(m_prefix+"StatusBG", px, py+30, W, 24,
                 running ? C'0,80,0' : C'120,0,0');
      CreateLabel(m_prefix+"Status",
                  running ? "  STATUS: RUNNING" : "  STATUS: STOPPED",
                  px+4, py+36, 9,
                  running ? clrLime : clrRed);

      // Toggle button
      CreateButton(m_prefix+"BtnToggle",
                   running ? "STOP BOT" : "START BOT",
                   px+W-80, py+31, 76, 22,
                   running ? C'150,0,0' : C'0,120,0',
                   clrWhite);

      // Price
      CreateLabel(m_prefix+"PriceLbl","  PRICE:", px+4, py+62, 8, clrSilver);
      CreateLabel(m_prefix+"Price",   "---",      px+80, py+62, 9, clrWhite);

      // Separator
      CreateRect(m_prefix+"Sep1", px, py+78, W, 1, C'40,50,70');

      // Signal section
      CreateLabel(m_prefix+"SigHdr","  SIGNAL ANALYSIS",px+4, py+82, 8, clrSilver);

      CreateLabel(m_prefix+"TF15Lbl",  "  M15 :", px+4,   py+100, 8, clrSilver);
      CreateLabel(m_prefix+"TF15Sig",  "---",      px+80,  py+100, 9, m_neutCol);
      CreateLabel(m_prefix+"TF1HLbl",  "  H1  :", px+4,   py+116, 8, clrSilver);
      CreateLabel(m_prefix+"TF1HSig",  "---",      px+80,  py+116, 9, m_neutCol);
      CreateLabel(m_prefix+"TF4HLbl",  "  H4  :", px+4,   py+132, 8, clrSilver);
      CreateLabel(m_prefix+"TF4HSig",  "---",      px+80,  py+132, 9, m_neutCol);
      CreateLabel(m_prefix+"TF1DLbl",  "  D1  :", px+4,   py+148, 8, clrSilver);
      CreateLabel(m_prefix+"TF1DSig",  "---",      px+80,  py+148, 9, m_neutCol);

      // Confluence
      CreateRect(m_prefix+"Sep2", px, py+167, W, 1, C'40,50,70');
      CreateLabel(m_prefix+"ConfLbl", "  CONFLUENCE:",   px+4, py+171, 8, clrSilver);
      CreateLabel(m_prefix+"Conf",    "---",             px+110,py+171,9, clrWhite);
      CreateLabel(m_prefix+"MLLbl",   "  ML SCORE:",     px+4, py+187, 8, clrSilver);
      CreateLabel(m_prefix+"ML",      "---",             px+110,py+187,9, clrWhite);
      CreateLabel(m_prefix+"ProbLbl", "  PROBABILITY:",  px+4, py+203, 8, clrSilver);
      CreateLabel(m_prefix+"Prob",    "---",             px+110,py+203,9, clrWhite);

      // SL/TP
      CreateRect(m_prefix+"Sep3", px, py+222, W, 1, C'40,50,70');
      CreateLabel(m_prefix+"SLLbl","  SUGGESTED SL:", px+4, py+226, 8, clrSilver);
      CreateLabel(m_prefix+"SL",   "---",              px+130,py+226,9, m_slCol);
      CreateLabel(m_prefix+"TPLbl","  SUGGESTED TP:", px+4, py+242, 8, clrSilver);
      CreateLabel(m_prefix+"TP",   "---",              px+130,py+242,9, m_tpCol);

      // Last trade
      CreateRect(m_prefix+"Sep4", px, py+260, W, 1, C'40,50,70');
      CreateLabel(m_prefix+"LastHdr","  LAST TRADE",   px+4,py+264,8,clrSilver);
      CreateLabel(m_prefix+"LastDir","---",            px+4,py+280,9,clrWhite);
      CreateLabel(m_prefix+"LastLot","---",            px+4,py+296,8,clrSilver);

      // Strategies hit
      CreateRect(m_prefix+"Sep5", px, py+314, W, 1, C'40,50,70');
      CreateLabel(m_prefix+"StratHdr","  STRATEGIES HIT:", px+4,py+318,8,clrSilver);
      CreateLabel(m_prefix+"Strats","---", px+4,py+334,7,clrLightBlue);

      // Refresh button
      CreateButton(m_prefix+"BtnRefresh","SCAN NOW",
                   px+W-86, py+H-28, 82, 24, C'20,60,120', clrWhite);

      ChartRedraw(0);
   }

   void Draw(bool running, string symbol, double sl, double tp,
             double conf, double ml, double prob) {}

   void UpdateStatus(bool running, string msg)
   {
      ObjectSetInteger(0, m_prefix+"StatusBG", OBJPROP_BGCOLOR,
                       running ? C'0,80,0' : C'120,0,0');
      SetLabel(m_prefix+"Status",
               "  STATUS: " + msg,
               running ? clrLime : clrRed);
      ObjectSetString(0, m_prefix+"BtnToggle", OBJPROP_TEXT,
                      running ? "STOP BOT" : "START BOT");
      ObjectSetInteger(0, m_prefix+"BtnToggle", OBJPROP_BGCOLOR,
                       running ? C'150,0,0' : C'0,120,0');
      ChartRedraw(0);
   }

   void UpdatePrice(double bid, double ask)
   {
      SetLabel(m_prefix+"Price",
               DoubleToString(bid,_Digits) + " / " + DoubleToString(ask,_Digits),
               clrWhite);
      ChartRedraw(0);
   }

   void UpdateSignal(SSignalResult &sig, ENUM_TIMEFRAMES tf)
   {
      string tfName = "";
      string objSig = "";
      color  sigClr = m_neutCol;

      switch(tf) {
         case PERIOD_M15: tfName="TF15"; break;
         case PERIOD_H1:  tfName="TF1H"; break;
         case PERIOD_H4:  tfName="TF4H"; break;
         case PERIOD_D1:  tfName="TF1D"; break;
         default: return;
      }

      if(sig.direction == SIGNAL_BUY)  { objSig="BUY";  sigClr=m_buyCol;  }
      else if(sig.direction==SIGNAL_SELL){ objSig="SELL"; sigClr=m_sellCol; }
      else                              { objSig="WAIT"; sigClr=m_neutCol;  }

      SetLabel(m_prefix+tfName+"Sig", objSig, sigClr);

      // Update confluence, ML, probability
      SetLabel(m_prefix+"Conf", DoubleToString(sig.confluence,1) + "%", clrWhite);
      SetLabel(m_prefix+"ML",   DoubleToString(sig.ml_score,1)  + "%",
               sig.ml_score >= 70 ? clrLime : sig.ml_score >= 50 ? clrYellow : clrOrangeRed);
      SetLabel(m_prefix+"Prob", DoubleToString(sig.probability, 1) + "%",
               sig.probability >= 65 ? clrLime : clrOrangeRed);
      SetLabel(m_prefix+"SL",   DoubleToString(sig.suggested_sl, _Digits), m_slCol);
      SetLabel(m_prefix+"TP",   DoubleToString(sig.suggested_tp, _Digits), m_tpCol);
      SetLabel(m_prefix+"Strats", StringSubstr(sig.strategy_hits, 0, 60), clrLightBlue);
      ChartRedraw(0);
   }

   void UpdateLastTrade(ENUM_SIGNAL dir, double lots, double sl, double tp)
   {
      string dirStr = (dir == SIGNAL_BUY) ? "BUY" : "SELL";
      color  dirClr = (dir == SIGNAL_BUY) ? m_buyCol : m_sellCol;
      SetLabel(m_prefix+"LastDir",
               "  " + dirStr + " | SL: " + DoubleToString(sl,_Digits) +
               "  TP: " + DoubleToString(tp,_Digits), dirClr);
      SetLabel(m_prefix+"LastLot",
               "  Lots: " + DoubleToString(lots,2), clrSilver);
      ChartRedraw(0);
   }
};
