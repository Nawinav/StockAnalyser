"""
Stock Scorer — Core Intelligence
=================================
Scores each stock out of 100 points across 5 categories:
  1. Trend Alignment   (30 pts)
  2. Momentum          (25 pts)
  3. Volume            (20 pts)
  4. Candlestick       (15 pts)
  5. Trend Strength    (10 pts)
Fundamental bonus:    (up to +20 pts, separate from above)

Entry  : Previous day's close price (approximate morning open)
SL     : max(prev_low, entry - 1.5×ATR) capped between 0.4% and 2.0%
Target1: entry + 1.5 × risk  (1:1.5 R:R)
Target2: entry + 2.5 × risk  (1:2.5 R:R)
"""
import logging
import math
from typing import Optional

import numpy as np
import pandas as pd

from app.services.technical_analysis import calculate_all_indicators, detect_candlestick_patterns
from app.services.fundamental_analysis import evaluate_fundamentals
from app.config import settings

logger = logging.getLogger(__name__)


def score_stock(
    symbol: str,
    ohlcv_df: pd.DataFrame,
    fundamentals: dict,
    market_trend: str = "neutral",
) -> Optional[dict]:
    """
    Full analysis + scoring for a single stock.
    Returns a result dict or None if the stock fails minimum criteria.
    """

    # ── 1. Compute indicators ─────────────────────────────────────────────────
    df = calculate_all_indicators(ohlcv_df)
    if df is None:
        logger.debug(f"{symbol}: insufficient data after indicator calculation")
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # ── 2. Guard: need valid core indicators ─────────────────────────────────
    for col in ("rsi", "macd", "ema9", "ema21", "ema50", "atr", "vol_ratio"):
        if pd.isna(last.get(col)):
            logger.debug(f"{symbol}: missing indicator '{col}'")
            return None

    # ── 3. Fundamental filter ────────────────────────────────────────────────
    fund_eval = evaluate_fundamentals(fundamentals)
    if fund_eval.disqualified:
        logger.debug(f"{symbol}: disqualified by fundamentals")
        return None

    score = 0
    reasons: list[str] = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CATEGORY 1 — TREND ALIGNMENT (30 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Long-term trend: price vs EMA200 (6 pts)
    if not pd.isna(last["ema200"]):
        if last["close"] > last["ema200"]:
            score += 6
            reasons.append("Price above EMA(200) — long-term uptrend")
    else:
        score += 3  # neutral if 200 EMA not yet formed

    # Medium-term: price vs EMA50 (5 pts)
    if last["close"] > last["ema50"]:
        score += 5
        reasons.append("Price above EMA(50) — medium-term bullish")

    # Short-term: price vs EMA21 (5 pts)
    if last["close"] > last["ema21"]:
        score += 5
        reasons.append("Price above EMA(21)")

    # EMA9 > EMA21 crossover (9 pts) ← most powerful signal for intraday
    if last["ema9"] > last["ema21"]:
        score += 9
        # Fresh crossover bonus
        if prev["ema9"] <= prev["ema21"]:
            score += 5
            reasons.append("EMA(9) JUST crossed above EMA(21) — fresh bullish signal")
        else:
            reasons.append("EMA(9) above EMA(21) — short-term bullish")

    # EMA21 > EMA50 (5 pts)
    if last["ema21"] > last["ema50"]:
        score += 5
        reasons.append("EMA(21) above EMA(50) — medium momentum confirmed")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CATEGORY 2 — MOMENTUM (25 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    rsi = last["rsi"]
    if 50 <= rsi <= 65:
        score += 12
        reasons.append(f"RSI {rsi:.1f} — ideal momentum zone (50-65)")
    elif 45 <= rsi < 50:
        score += 7
        reasons.append(f"RSI {rsi:.1f} — approaching bullish territory")
    elif 65 < rsi <= 70:
        score += 6
        reasons.append(f"RSI {rsi:.1f} — strong momentum (not yet overbought)")
    elif rsi > 70:
        score += 2
        reasons.append(f"RSI {rsi:.1f} — overbought, risky entry")
    elif rsi < 40:
        reasons.append(f"RSI {rsi:.1f} — oversold, may not be ready")

    # MACD above signal (8 pts)
    if last["macd"] > last["macd_signal"]:
        score += 8
        reasons.append("MACD above signal line — positive momentum")
        # Increasing histogram (5 pts)
        if not pd.isna(prev["macd_hist"]) and last["macd_hist"] > prev["macd_hist"] > 0:
            score += 5
            reasons.append("MACD histogram expanding — momentum accelerating")
        elif last["macd_hist"] > 0 and prev["macd_hist"] <= 0:
            score += 4
            reasons.append("MACD histogram just turned positive — fresh signal")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CATEGORY 3 — VOLUME CONFIRMATION (20 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    vol_ratio = last["vol_ratio"]
    if not pd.isna(vol_ratio):
        if vol_ratio >= 2.5:
            score += 20
            reasons.append(f"Volume surge {vol_ratio:.1f}× average — very strong interest")
        elif vol_ratio >= 2.0:
            score += 16
            reasons.append(f"Volume {vol_ratio:.1f}× average — strong buying pressure")
        elif vol_ratio >= 1.5:
            score += 12
            reasons.append(f"Volume {vol_ratio:.1f}× average — elevated activity")
        elif vol_ratio >= 1.2:
            score += 8
            reasons.append(f"Volume {vol_ratio:.1f}× average — above normal")
        elif vol_ratio >= 1.0:
            score += 4
        else:
            reasons.append(f"Volume below average ({vol_ratio:.1f}×) — weak confirmation")

    # OBV trend (check if OBV is rising over last 5 days)
    if len(df) >= 5:
        obv_last5 = df["obv"].iloc[-5:]
        if not obv_last5.isna().any() and obv_last5.iloc[-1] > obv_last5.iloc[0]:
            score += 2
            reasons.append("OBV rising — institutional accumulation")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CATEGORY 4 — CANDLESTICK PATTERNS (15 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    patterns = detect_candlestick_patterns(df)
    pattern_pts = 0
    if patterns.get("bullish_marubozu"):
        pattern_pts = max(pattern_pts, 15)
        reasons.append("Bullish Marubozu candle — very strong buying")
    if patterns.get("bullish_engulfing"):
        pattern_pts = max(pattern_pts, 13)
        reasons.append("Bullish Engulfing pattern — reversal signal")
    if patterns.get("morning_star"):
        pattern_pts = max(pattern_pts, 12)
        reasons.append("Morning Star pattern — three-candle reversal")
    if patterns.get("hammer"):
        pattern_pts = max(pattern_pts, 10)
        reasons.append("Hammer candle — buyers rejected lower prices")
    if patterns.get("inside_day_breakout"):
        pattern_pts = max(pattern_pts, 9)
        reasons.append("Inside-day breakout — coiling ready to burst")

    # Generic candle quality
    if pattern_pts == 0:
        if last["is_bullish"] == 1 and last["close_to_high"] >= 0.70:
            pattern_pts = 7
            reasons.append("Bullish candle closing near day high")
        elif last["is_bullish"] == 1:
            pattern_pts = 4
            reasons.append("Bullish candle (close > open)")

    score += pattern_pts

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CATEGORY 5 — TREND STRENGTH / ADX (10 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    adx = last["adx"]
    if not pd.isna(adx):
        if adx >= 30:
            score += 10
            reasons.append(f"ADX {adx:.1f} — very strong trend")
        elif adx >= 25:
            score += 7
            reasons.append(f"ADX {adx:.1f} — strong trend")
        elif adx >= 20:
            score += 4
            reasons.append(f"ADX {adx:.1f} — developing trend")
        else:
            reasons.append(f"ADX {adx:.1f} — weak/choppy, wider stop advised")

        # DI+ > DI- confirms bullish trend
        if not pd.isna(last["di_plus"]) and last["di_plus"] > last["di_minus"]:
            score += 3
            reasons.append("DI+ above DI− — bullish directional movement")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MARKET TREND ADJUSTMENT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if market_trend == "bullish":
        score += 5
        reasons.append("Overall market (NIFTY) in uptrend — tailwind")
    elif market_trend == "bearish":
        score = int(score * 0.75)           # 25% penalty in bear market
        reasons.append("Overall market (NIFTY) bearish — caution, score penalised")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FUNDAMENTAL BONUS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    score += fund_eval.score
    reasons += fund_eval.reasons

    # ── Minimum score gate ─────────────────────────────────────────────────
    if score < settings.MIN_SCORE_THRESHOLD:
        return None

    # ── Entry / Stop Loss / Target Calculation ─────────────────────────────
    entry = round(float(last["close"]), 2)
    atr   = float(last["atr"])

    # Stop Loss = highest of (ATR-based or previous candle low)
    atr_sl   = entry - 1.5 * atr
    prev_low  = float(prev["low"])
    raw_sl    = max(atr_sl, prev_low)

    # Cap between 0.4% and 2.0%
    min_sl = entry * (1 - settings.MAX_STOP_LOSS_PCT / 100)
    max_sl = entry * (1 - settings.MIN_STOP_LOSS_PCT / 100)
    stop_loss = round(max(min_sl, min(raw_sl, max_sl)), 2)

    risk    = entry - stop_loss
    target1 = round(entry + risk * settings.TARGET1_RR_RATIO, 2)
    target2 = round(entry + risk * settings.TARGET2_RR_RATIO, 2)

    sl_pct  = round((entry - stop_loss) / entry * 100, 2)
    t1_pct  = round((target1 - entry)   / entry * 100, 2)
    t2_pct  = round((target2 - entry)   / entry * 100, 2)

    final_score = min(int(score), 100)

    return {
        "symbol":             symbol,
        "company_name":       fundamentals.get("company_name", symbol),
        "sector":             fundamentals.get("sector"),
        "entry_price":        entry,
        "stop_loss":          stop_loss,
        "sl_percentage":      sl_pct,
        "target1":            target1,
        "target1_percentage": t1_pct,
        "target2":            target2,
        "target2_percentage": t2_pct,
        "score":              final_score,
        "atr":                round(atr, 2),
        "rsi":                round(float(last["rsi"]), 2),
        "macd":               round(float(last["macd"]), 4),
        "macd_signal":        round(float(last["macd_signal"]), 4),
        "adx":                round(float(last["adx"]), 2) if not pd.isna(last["adx"]) else None,
        "ema9":               round(float(last["ema9"]), 2),
        "ema21":              round(float(last["ema21"]), 2),
        "ema50":              round(float(last["ema50"]), 2),
        "volume_ratio":       round(float(last["vol_ratio"]), 2),
        "pe_ratio":           fundamentals.get("pe_ratio"),
        "market_cap_cr":      fundamentals.get("market_cap_cr"),
        "week52_high":        fundamentals.get("week52_high"),
        "week52_low":         fundamentals.get("week52_low"),
        "pct_change_1d":      round(float(last["pct_change_1d"]), 2) if not pd.isna(last["pct_change_1d"]) else None,
        "pct_change_5d":      round(float(last["pct_change_5d"]), 2) if not pd.isna(last["pct_change_5d"]) else None,
        "patterns":           [k for k, v in patterns.items() if v],
        "reasons":            reasons,
    }


def run_full_analysis(market_trend: str = "neutral") -> list[dict]:
    """
    Scan all stocks in the universe, score each, and return top-N recommendations
    sorted by score (highest first).
    """
    from app.services.nse_stocks import get_all_symbols
    from app.services.data_fetcher import fetch_ohlcv, fetch_fundamentals, clear_fundamental_cache

    clear_fundamental_cache()
    all_symbols = get_all_symbols()
    results = []
    failed = 0

    logger.info(f"Starting scan of {len(all_symbols)} stocks. Market trend: {market_trend}")

    for symbol in all_symbols:
        try:
            ohlcv  = fetch_ohlcv(symbol)
            if ohlcv is None:
                failed += 1
                continue

            fundamentals = fetch_fundamentals(symbol)
            result = score_stock(symbol, ohlcv, fundamentals, market_trend)

            if result:
                results.append(result)

        except Exception as exc:
            logger.error(f"Error processing {symbol}: {exc}")
            failed += 1

    logger.info(f"Scan complete. Qualified: {len(results)}, Failed/skipped: {failed}")

    # Sort by score descending, take top N
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:settings.MAX_RECOMMENDATIONS]
