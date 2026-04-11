import axios from 'axios';
import Constants from 'expo-constants';
import { TodayResponse, MarketStatus, StockAnalysis, Recommendation } from '../types';

// Priority order:
//   1. EXPO_PUBLIC_API_URL env var  (set in .env or Vercel/Netlify env)
//   2. extra.apiUrl from app.json   (EAS build config)
//   3. localhost fallback           (local dev)
const BASE_URL: string =
  process.env.EXPO_PUBLIC_API_URL ||
  (Constants.expoConfig?.extra?.apiUrl as string | undefined) ||
  'http://localhost:8000/api';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Interceptors ──────────────────────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('[API Error]', err?.response?.data || err.message);
    return Promise.reject(err);
  }
);

// ── API calls ─────────────────────────────────────────────────────────────

export const getTodayRecommendations = async (): Promise<TodayResponse> => {
  const { data } = await api.get<TodayResponse>('/recommendations/today');
  return data;
};

export const getHistoryRecommendations = async (days = 7): Promise<Recommendation[]> => {
  const { data } = await api.get<Recommendation[]>(`/recommendations/history?days=${days}`);
  return data;
};

export const getMarketStatus = async (): Promise<MarketStatus> => {
  const { data } = await api.get<MarketStatus>('/market/status');
  return data;
};

export const getStockAnalysis = async (symbol: string): Promise<StockAnalysis> => {
  const { data } = await api.get<StockAnalysis>(`/stocks/${symbol}`);
  return data;
};

export const triggerAnalysis = async (): Promise<{ message: string }> => {
  const { data } = await api.post<{ message: string }>('/recommendations/trigger');
  return data;
};

export default api;
