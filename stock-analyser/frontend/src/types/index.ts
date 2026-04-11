// ─── Types ──────────────────────────────────────────────────────────────────

export interface Recommendation {
  id: number;
  rank: number;
  trade_date: string;
  symbol: string;
  company_name?: string;
  sector?: string;
  entry_price?: number;
  stop_loss?: number;
  sl_percentage?: number;
  target1?: number;
  target1_percentage?: number;
  target2?: number;
  target2_percentage?: number;
  score?: number;
  rsi?: number;
  macd?: number;
  adx?: number;
  ema9?: number;
  ema21?: number;
  ema50?: number;
  volume_ratio?: number;
  pe_ratio?: number;
  market_cap_cr?: number;
  reasons?: string[];
}

export interface TodayResponse {
  trade_date: string;
  nifty_trend?: string;
  total_recommendations: number;
  analyzed_at?: string;
  recommendations: Recommendation[];
}

export interface MarketStatus {
  is_open: boolean;
  status: string;
  current_time_ist: string;
  market_open: string;
  market_close: string;
  nifty_trend?: string;
  nifty_last_close?: number;
  nifty_change_pct?: number;
}

export interface StockAnalysis extends Recommendation {
  week52_high?: number;
  week52_low?: number;
  pct_change_1d?: number;
  pct_change_5d?: number;
  patterns?: string[];
}

export type NiftyTrend = 'bullish' | 'bearish' | 'neutral';
