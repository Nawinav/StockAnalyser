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

export interface IntradayStock {
  id: number;
  snapshot_at?: string;
  rank: number;
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
  nifty_trend?: string;
}

export interface IntradayResponse {
  snapshot_at?: string;
  nifty_trend?: string;
  total: number;
  stocks: IntradayStock[];
}

export interface LongTermStock {
  id: number;
  run_date: string;
  rank: number;
  symbol: string;
  company_name?: string;
  sector?: string;
  industry?: string;
  current_price?: number;
  week52_high?: number;
  week52_low?: number;
  pe_ratio?: number;
  pb_ratio?: number;
  eps_ttm?: number;
  roe?: number;
  debt_to_equity?: number;
  revenue_growth?: number;
  earnings_growth?: number;
  profit_margins?: number;
  dividend_yield?: number;
  market_cap_cr?: number;
  fundamental_score?: number;
  technical_score?: number;
  total_score?: number;
  hold_period?: string;
  hold_rationale?: string;
  reasons?: string[];
}

export interface LongTermResponse {
  run_date: string;
  total: number;
  stocks: LongTermStock[];
}

export interface NewsItem {
  title: string;
  publisher: string;
  link: string;
  published_at: number;  // unix timestamp
}

export interface WatchlistItem {
  id: number;
  symbol: string;
  company_name?: string;
  sector?: string;
  added_price?: number;
  current_price?: number;
  score?: number;
  hold_period?: string;
  notes?: string;
  added_at?: string;
  news?: NewsItem[];
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

