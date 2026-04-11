"""
Data fetcher — pulls OHLCV + fundamental data from Yahoo Finance (NSE .NS symbols).
Uses yfinance with retry logic and caches basic info per session.
"""
import logging
import time
from typing import Optional
from functools import lru_cache

import pandas as pd
import numpy as np
import yfinance as yf

from app.services.nse_stocks import get_nse_symbol
from app.config import settings

logger = logging.getLogger(__name__)

# Simple in-memory cache for fundamentals (per process lifetime)
_fundamental_cache: dict = {}


def fetch_ohlcv(symbol: str, period: str = None, retries: int = 2) -> Optional[pd.DataFrame]:
    """
    Download historical OHLCV data for an NSE stock.
    Returns a clean DataFrame indexed by date, or None on failure.
    """
    period = period or settings.DATA_LOOKBACK_PERIOD
    nse_sym = get_nse_symbol(symbol)

    for attempt in range(retries + 1):
        try:
            ticker = yf.Ticker(nse_sym)
            df = ticker.history(period=period, auto_adjust=True, actions=False)

            if df is None or df.empty:
                logger.warning(f"No data returned for {nse_sym}")
                return None

            # Normalise column names
            df.rename(columns={
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume"
            }, inplace=True)

            # Drop pre-market / after-hours rows (volume == 0)
            df = df[df["volume"] > 0].copy()

            # Sort just in case
            df.sort_index(inplace=True)

            if len(df) < 30:
                logger.warning(f"Insufficient data for {symbol}: {len(df)} rows")
                return None

            return df

        except Exception as exc:
            logger.error(f"[Attempt {attempt+1}] Error fetching OHLCV for {symbol}: {exc}")
            if attempt < retries:
                time.sleep(1.5)

    return None


def fetch_fundamentals(symbol: str) -> dict:
    """
    Fetch fundamental / company info via yfinance.
    Results are cached in memory for the lifetime of the process.
    """
    if symbol in _fundamental_cache:
        return _fundamental_cache[symbol]

    nse_sym = get_nse_symbol(symbol)
    try:
        info = yf.Ticker(nse_sym).info

        # Market cap conversion to Crores (1 Crore = 10M)
        mktcap = info.get("marketCap")
        mktcap_cr = round(mktcap / 1e7, 2) if mktcap else None

        result = {
            "symbol": symbol,
            "company_name": info.get("longName") or info.get("shortName") or symbol,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap_cr": mktcap_cr,
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "eps_ttm": info.get("trailingEps"),
            "debt_to_equity": info.get("debtToEquity"),
            "return_on_equity": info.get("returnOnEquity"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margins": info.get("profitMargins"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "week52_high": info.get("fiftyTwoWeekHigh"),
            "week52_low": info.get("fiftyTwoWeekLow"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "avg_volume": info.get("averageVolume"),
            "float_shares": info.get("floatShares"),
        }

        _fundamental_cache[symbol] = result
        return result

    except Exception as exc:
        logger.error(f"Error fetching fundamentals for {symbol}: {exc}")
        return {"symbol": symbol, "company_name": symbol}


def fetch_index_data(index_symbol: str = "^NSEI", period: str = "3mo") -> Optional[pd.DataFrame]:
    """
    Fetch NIFTY 50 (^NSEI) or NIFTY Bank (^NSEBANK) index data.
    Used to determine overall market trend.
    """
    try:
        ticker = yf.Ticker(index_symbol)
        df = ticker.history(period=period, auto_adjust=True, actions=False)
        if df is None or df.empty:
            return None
        df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume"
        }, inplace=True)
        df.sort_index(inplace=True)
        return df
    except Exception as exc:
        logger.error(f"Error fetching index {index_symbol}: {exc}")
        return None


def clear_fundamental_cache():
    """Clear the in-memory fundamentals cache (call at start of each analysis run)."""
    _fundamental_cache.clear()
