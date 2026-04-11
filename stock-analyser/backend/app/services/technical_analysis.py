"""
Technical Analysis Engine
Computes all indicators needed for intraday stock selection:
  Trend   : EMA(9/21/50/200), SMA(20)
  Momentum: RSI(14), MACD(12,26,9), Stochastic(14,3)
  Volatility: ATR(14), Bollinger Bands(20,2)
  Strength: ADX(14), DI+, DI-
  Volume  : OBV, Volume MA(20), Volume Ratio
  Candle  : Body size, shadows, close-to-high ratio
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd
import ta

logger = logging.getLogger(__name__)


def calculate_all_indicators(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Accepts a DataFrame with columns: open, high, low, close, volume.
    Returns the DataFrame enriched with indicator columns,
    or None if there is insufficient data.
    """
    if df is None or len(df) < 50:
        return None

    df = df.copy()

    try:
        close = df["close"]
        high  = df["high"]
        low   = df["low"]
        vol   = df["volume"]

        # ── Trend ────────────────────────────────────────────────────────────
        df["ema9"]   = ta.trend.EMAIndicator(close, window=9).ema_indicator()
        df["ema21"]  = ta.trend.EMAIndicator(close, window=21).ema_indicator()
        df["ema50"]  = ta.trend.EMAIndicator(close, window=50).ema_indicator()
        df["ema200"] = ta.trend.EMAIndicator(close, window=200).ema_indicator()
        df["sma20"]  = ta.trend.SMAIndicator(close, window=20).sma_indicator()

        # ── Momentum ─────────────────────────────────────────────────────────
        df["rsi"] = ta.momentum.RSIIndicator(close, window=14).rsi()

        _macd = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
        df["macd"]        = _macd.macd()
        df["macd_signal"] = _macd.macd_signal()
        df["macd_hist"]   = _macd.macd_diff()

        _stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
        df["stoch_k"] = _stoch.stoch()
        df["stoch_d"] = _stoch.stoch_signal()

        # ── Volatility ───────────────────────────────────────────────────────
        df["atr"] = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()

        _bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        df["bb_upper"]  = _bb.bollinger_hband()
        df["bb_middle"] = _bb.bollinger_mavg()
        df["bb_lower"]  = _bb.bollinger_lband()
        df["bb_width"]  = (_bb.bollinger_hband() - _bb.bollinger_lband()) / _bb.bollinger_mavg()
        df["bb_pct"]    = _bb.bollinger_pband()   # % position within bands (0=lower, 1=upper)

        # ── Trend Strength ───────────────────────────────────────────────────
        _adx = ta.trend.ADXIndicator(high, low, close, window=14)
        df["adx"]      = _adx.adx()
        df["di_plus"]  = _adx.adx_pos()
        df["di_minus"] = _adx.adx_neg()

        # ── Volume ───────────────────────────────────────────────────────────
        df["obv"]        = ta.volume.OnBalanceVolumeIndicator(close, vol).on_balance_volume()
        df["vol_ma20"]   = vol.rolling(window=20).mean()
        df["vol_ratio"]  = vol / df["vol_ma20"]

        # ── Candle Analysis ──────────────────────────────────────────────────
        df["body"]            = (df["close"] - df["open"]).abs()
        df["full_range"]      = df["high"] - df["low"]
        df["upper_shadow"]    = df["high"] - df[["open", "close"]].max(axis=1)
        df["lower_shadow"]    = df[["open", "close"]].min(axis=1) - df["low"]
        df["is_bullish"]      = (df["close"] > df["open"]).astype(int)
        # Where is close relative to the full range? 1.0 = closed at high
        df["close_to_high"]   = (df["close"] - df["low"]) / (df["full_range"].replace(0, np.nan))

        # ── Support / Resistance (rolling 10 & 20-day) ───────────────────────
        df["resist_20"] = df["high"].rolling(window=20).max()
        df["support_20"] = df["low"].rolling(window=20).min()
        df["resist_10"] = df["high"].rolling(window=10).max()
        df["support_10"] = df["low"].rolling(window=10).min()

        # ── Price change ─────────────────────────────────────────────────────
        df["pct_change_1d"] = close.pct_change(1) * 100
        df["pct_change_5d"] = close.pct_change(5) * 100

        return df

    except Exception as exc:
        logger.error(f"Technical analysis error: {exc}")
        return None


def detect_candlestick_patterns(df: pd.DataFrame) -> dict:
    """
    Detect key bullish candlestick patterns on the last two candles.
    Returns a dict of pattern_name -> True/False.
    """
    if df is None or len(df) < 3:
        return {}

    last  = df.iloc[-1]
    prev  = df.iloc[-2]
    prev2 = df.iloc[-3]

    patterns = {}

    body_size = last["body"]
    full_range = last["full_range"] if last["full_range"] > 0 else 0.0001

    # Bullish Marubozu — large body, tiny shadows
    patterns["bullish_marubozu"] = (
        last["is_bullish"] == 1
        and body_size / full_range >= 0.85
        and last["upper_shadow"] / full_range <= 0.05
        and last["lower_shadow"] / full_range <= 0.05
    )

    # Hammer — small body at top, long lower shadow
    patterns["hammer"] = (
        last["lower_shadow"] >= 2 * body_size
        and last["upper_shadow"] / full_range <= 0.1
        and last["close_to_high"] >= 0.6
    )

    # Bullish Engulfing
    patterns["bullish_engulfing"] = (
        prev["is_bullish"] == 0           # previous was red
        and last["is_bullish"] == 1        # current is green
        and last["open"] < prev["close"]   # opened below prev close
        and last["close"] > prev["open"]   # closed above prev open
    )

    # Morning Star (3-candle)
    patterns["morning_star"] = (
        prev2["is_bullish"] == 0           # first candle red
        and prev["body"] < prev2["body"] * 0.3  # small middle candle
        and last["is_bullish"] == 1        # third candle green
        and last["close"] > (prev2["open"] + prev2["close"]) / 2  # closes above midpoint
    )

    # Inside-day breakout: today's range fully inside prev range but closing near high
    patterns["inside_day_breakout"] = (
        last["high"] < prev["high"]
        and last["low"] > prev["low"]
        and last["close_to_high"] >= 0.75
        and last["is_bullish"] == 1
    )

    return patterns


def get_market_trend(df: pd.DataFrame) -> str:
    """
    Given processed NIFTY index data, return 'bullish', 'bearish', or 'neutral'.
    """
    if df is None or len(df) < 50:
        return "neutral"

    last = df.iloc[-1]

    ema50_ok  = not pd.isna(last.get("ema50"))  and last["close"] > last.get("ema50", 0)
    ema21_ok  = not pd.isna(last.get("ema21"))  and last["close"] > last.get("ema21", 0)
    ema9_ok   = not pd.isna(last.get("ema9"))   and last["ema9"]  > last.get("ema21", 0)
    rsi_ok    = not pd.isna(last.get("rsi"))    and last["rsi"] > 50
    macd_ok   = not pd.isna(last.get("macd"))   and last["macd"]  > last.get("macd_signal", 0)

    bull_points = sum([ema50_ok, ema21_ok, ema9_ok, rsi_ok, macd_ok])

    if bull_points >= 4:
        return "bullish"
    elif bull_points <= 1:
        return "bearish"
    else:
        return "neutral"
