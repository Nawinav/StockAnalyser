"""
Long-Term Stock Scorer
=======================
Scores stocks for long-term investment (3 months – 2+ years) using a
fundamentals-heavy approach:

  Fundamental Quality  : 50 pts
  Growth Trajectory    : 25 pts
  Technical Trend      : 15 pts
  Valuation            : 10 pts

Hold-period is estimated from the combined score and momentum phase.
"""
import logging
from typing import Optional

import pandas as pd

from app.services.technical_analysis import calculate_all_indicators, get_market_trend
from app.config import settings

logger = logging.getLogger(__name__)


def _hold_period(total_score: int, momentum: str) -> tuple[str, str]:
    """Return (hold_period_label, rationale) based on score + momentum."""
    if total_score >= 80:
        if momentum == "early":
            return "1-2 years", "High-quality stock in early uptrend — suitable for a multi-year hold."
        return "6-12 months", "Strong fundamentals with confirmed momentum — medium-long hold."
    if total_score >= 65:
        return "6-12 months", "Solid fundamentals; re-evaluate at the 6-month mark."
    if total_score >= 50:
        return "3-6 months", "Decent quality; monitor quarterly results before extending."
    return "3 months", "Marginal fundamentals — short watch period recommended."


def score_long_term(symbol: str, ohlcv_df: pd.DataFrame, fundamentals: dict) -> Optional[dict]:
    """
    Compute a long-term investment score for a stock.
    Returns a result dict or None if data is insufficient.
    """
    if ohlcv_df is None or len(ohlcv_df) < 30:
        return None

    df = calculate_all_indicators(ohlcv_df)
    if df is None:
        return None

    last = df.iloc[-1]
    fund = fundamentals or {}

    fundamental_score = 0
    growth_score = 0
    technical_score = 0
    valuation_score = 0
    reasons: list[str] = []

    # ── Market-cap filter ────────────────────────────────────────────────────
    mktcap = fund.get("market_cap_cr")
    if mktcap is not None and mktcap < settings.MIN_MARKET_CAP_CR:
        return None   # Too small for long-term

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 1 — FUNDAMENTAL QUALITY (50 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Profitability — EPS (10 pts)
    eps = fund.get("eps_ttm")
    if eps is not None:
        if eps > 10:
            fundamental_score += 10; reasons.append(f"Strong EPS ₹{eps:.2f}")
        elif eps > 0:
            fundamental_score += 6;  reasons.append(f"Positive EPS ₹{eps:.2f}")
        else:
            fundamental_score -= 5;  reasons.append(f"Negative EPS ₹{eps:.2f} — loss-making, caution")

    # ROE (12 pts)
    roe = fund.get("return_on_equity")
    if roe is not None:
        if roe >= 0.25:
            fundamental_score += 12; reasons.append(f"Excellent ROE {roe*100:.1f}% — superior capital efficiency")
        elif roe >= 0.15:
            fundamental_score += 8;  reasons.append(f"Good ROE {roe*100:.1f}%")
        elif roe >= 0.08:
            fundamental_score += 4;  reasons.append(f"Moderate ROE {roe*100:.1f}%")
        else:
            reasons.append(f"Weak ROE {roe*100:.1f}%")

    # Debt-to-Equity (10 pts)
    de = fund.get("debt_to_equity")
    if de is not None:
        if de < 20:
            fundamental_score += 10; reasons.append(f"Very low D/E {de:.1f} — debt-free balance sheet")
        elif de < 50:
            fundamental_score += 7;  reasons.append(f"Low D/E {de:.1f} — healthy balance sheet")
        elif de < 100:
            fundamental_score += 3;  reasons.append(f"Moderate D/E {de:.1f}")
        else:
            fundamental_score -= 3;  reasons.append(f"High D/E {de:.1f} — leveraged, risk in rising rates")

    # Profit margins (8 pts)
    pm = fund.get("profit_margins")
    if pm is not None:
        if pm >= 0.20:
            fundamental_score += 8; reasons.append(f"High profit margin {pm*100:.1f}%")
        elif pm >= 0.10:
            fundamental_score += 5; reasons.append(f"Decent profit margin {pm*100:.1f}%")
        elif pm > 0:
            fundamental_score += 2; reasons.append(f"Thin margin {pm*100:.1f}%")
        else:
            reasons.append(f"Negative margin {pm*100:.1f}% — unprofitable")

    # Dividend (5 pts) — bonus for income investors
    div = fund.get("dividend_yield")
    if div and div > 0:
        if div >= 0.04:
            fundamental_score += 5; reasons.append(f"Attractive dividend yield {div*100:.1f}%")
        elif div >= 0.02:
            fundamental_score += 2; reasons.append(f"Dividend paying {div*100:.1f}%")

    # Market cap quality (5 pts — large/mid cap preferred)
    if mktcap is not None:
        if mktcap >= 20000:
            fundamental_score += 5; reasons.append(f"Large-cap ₹{mktcap:,.0f}Cr — institutional-grade")
        elif mktcap >= 5000:
            fundamental_score += 3; reasons.append(f"Mid-cap ₹{mktcap:,.0f}Cr")
        else:
            fundamental_score += 1; reasons.append(f"Small-cap ₹{mktcap:,.0f}Cr — higher risk")

    fundamental_score = max(0, min(fundamental_score, 50))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 2 — GROWTH TRAJECTORY (25 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Revenue growth (12 pts)
    rev_g = fund.get("revenue_growth")
    if rev_g is not None:
        if rev_g >= 0.25:
            growth_score += 12; reasons.append(f"Exceptional revenue growth {rev_g*100:.1f}% YoY")
        elif rev_g >= 0.15:
            growth_score += 9;  reasons.append(f"Strong revenue growth {rev_g*100:.1f}% YoY")
        elif rev_g >= 0.08:
            growth_score += 5;  reasons.append(f"Moderate revenue growth {rev_g*100:.1f}% YoY")
        elif rev_g >= 0:
            growth_score += 2
        else:
            reasons.append(f"Revenue declining {rev_g*100:.1f}% — watch closely")

    # Earnings growth (13 pts)
    earn_g = fund.get("earnings_growth")
    if earn_g is not None:
        if earn_g >= 0.30:
            growth_score += 13; reasons.append(f"Exceptional earnings growth {earn_g*100:.1f}% YoY")
        elif earn_g >= 0.20:
            growth_score += 10; reasons.append(f"Strong earnings growth {earn_g*100:.1f}% YoY")
        elif earn_g >= 0.10:
            growth_score += 6;  reasons.append(f"Healthy earnings growth {earn_g*100:.1f}% YoY")
        elif earn_g >= 0:
            growth_score += 3
        else:
            reasons.append(f"Earnings shrinking {earn_g*100:.1f}% — caution")

    growth_score = min(growth_score, 25)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 3 — TECHNICAL TREND (15 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Price vs EMA50 / EMA200 (weekly trend matters more for long-term)
    momentum_phase = "mid"
    if not pd.isna(last.get("ema200", float("nan"))):
        if last["close"] > last["ema200"]:
            technical_score += 5; reasons.append("Price above EMA(200) — long-term uptrend confirmed")
            # Early uptrend: EMA50 recently crossed above EMA200
            if not pd.isna(last.get("ema50")) and last["ema50"] > last["ema200"]:
                prev5 = df.iloc[-5]
                if not pd.isna(prev5.get("ema50")) and prev5["ema50"] <= prev5.get("ema200", float("inf")):
                    technical_score += 4; reasons.append("Golden cross (EMA50 > EMA200) — early bull phase")
                    momentum_phase = "early"
        else:
            technical_score -= 2; reasons.append("Price below EMA(200) — long-term downtrend, caution")

    if not pd.isna(last.get("ema50")):
        if last["close"] > last["ema50"]:
            technical_score += 3; reasons.append("Price above EMA(50) — medium-term bullish")

    rsi = last.get("rsi")
    if rsi is not None and not pd.isna(rsi):
        if 45 <= rsi <= 65:
            technical_score += 3; reasons.append(f"RSI {rsi:.1f} — healthy momentum zone")
        elif rsi > 70:
            technical_score -= 1; reasons.append(f"RSI {rsi:.1f} — overbought, wait for pullback")
        elif rsi < 35:
            technical_score += 2; reasons.append(f"RSI {rsi:.1f} — oversold, potential accumulation zone")

    technical_score = max(-5, min(technical_score, 15))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 4 — VALUATION (10 pts)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pe = fund.get("pe_ratio")
    if pe is not None and pe > 0:
        if pe < 15:
            valuation_score += 10; reasons.append(f"P/E {pe:.1f} — undervalued, high margin of safety")
        elif pe < 25:
            valuation_score += 7;  reasons.append(f"P/E {pe:.1f} — fairly valued")
        elif pe < 40:
            valuation_score += 4;  reasons.append(f"P/E {pe:.1f} — moderate premium")
        elif pe < 60:
            valuation_score += 1;  reasons.append(f"P/E {pe:.1f} — elevated, growth priced in")
        else:
            reasons.append(f"P/E {pe:.1f} — very expensive, high expectations")

    pb = fund.get("pb_ratio")
    if pb is not None and pb > 0:
        if pb < 1.5:
            valuation_score += 2; reasons.append(f"P/B {pb:.1f} — below book value, deep value")
        elif pb < 3:
            valuation_score += 1; reasons.append(f"P/B {pb:.1f} — fair book multiple")

    valuation_score = min(valuation_score, 10)

    total_score = min(fundamental_score + growth_score + technical_score + valuation_score, 100)
    total_score = max(0, total_score)

    hold_period, hold_rationale = _hold_period(total_score, momentum_phase)

    week52_high = fund.get("week52_high")
    week52_low  = fund.get("week52_low")
    close = float(last["close"])

    return {
        "symbol":            symbol,
        "company_name":      fund.get("company_name", symbol),
        "sector":            fund.get("sector"),
        "industry":          fund.get("industry"),
        "current_price":     round(close, 2),
        "week52_high":       week52_high,
        "week52_low":        week52_low,
        "pe_ratio":          pe,
        "pb_ratio":          pb,
        "eps_ttm":           eps,
        "roe":               round(roe * 100, 2) if roe else None,
        "debt_to_equity":    de,
        "revenue_growth":    round(rev_g * 100, 2) if rev_g is not None else None,
        "earnings_growth":   round(earn_g * 100, 2) if earn_g is not None else None,
        "profit_margins":    round(pm * 100, 2) if pm is not None else None,
        "dividend_yield":    round(div * 100, 2) if div else None,
        "market_cap_cr":     mktcap,
        "fundamental_score": fundamental_score,
        "technical_score":   max(0, technical_score),
        "total_score":       total_score,
        "hold_period":       hold_period,
        "hold_rationale":    hold_rationale,
        "reasons":           reasons,
    }


def run_long_term_analysis() -> list[dict]:
    """
    Scan all symbols, score for long-term, return top-N sorted by total_score.
    """
    from app.services.nse_stocks import get_all_symbols
    from app.services.data_fetcher import fetch_ohlcv, fetch_fundamentals, clear_fundamental_cache

    clear_fundamental_cache()
    symbols = get_all_symbols()
    results: list[dict] = []

    for symbol in symbols:
        try:
            ohlcv = fetch_ohlcv(symbol, period="1y")
            if ohlcv is None:
                continue
            fund = fetch_fundamentals(symbol)
            scored = score_long_term(symbol, ohlcv, fund)
            if scored and scored["total_score"] >= 40:
                results.append(scored)
        except Exception as exc:
            logger.warning(f"[LongTerm] Skipping {symbol}: {exc}")

    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results[:settings.MAX_RECOMMENDATIONS]
