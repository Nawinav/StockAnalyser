"""
Fundamental Analysis Filter
Screens stocks based on fundamental quality to avoid weak companies.
This is a secondary filter — stocks failing fundamental checks are penalised
rather than hard-excluded (few Indian small-caps have full fundamental data).
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FundamentalScore:
    """Holds a fundamental sub-score and disqualification flag."""
    def __init__(self, score: int = 0, disqualified: bool = False, reasons: list = None):
        self.score = score                  # 0-20
        self.disqualified = disqualified    # Hard fail
        self.reasons = reasons or []


def evaluate_fundamentals(fundamentals: dict, config=None) -> FundamentalScore:
    """
    Evaluate fundamental quality of a stock.
    Returns a FundamentalScore with sub-score (0-20) added to technical score.
    Hard disqualifications:
      - Market cap < 500 Cr
      - Negative EPS (loss-making)
    """
    from app.config import settings
    cfg = config or settings

    score = 0
    reasons = []
    disqualified = False

    if not fundamentals:
        # No data — neutral, no bonus or penalty
        return FundamentalScore(score=0, disqualified=False, reasons=["No fundamental data available"])

    # ── Hard filters ─────────────────────────────────────────────────────────
    mktcap = fundamentals.get("market_cap_cr")
    if mktcap is not None and mktcap < cfg.MIN_MARKET_CAP_CR:
        disqualified = True
        reasons.append(f"Market cap ₹{mktcap:.0f}Cr below minimum ₹{cfg.MIN_MARKET_CAP_CR:.0f}Cr — disqualified")
        return FundamentalScore(score=0, disqualified=True, reasons=reasons)

    # ── Positive earnings ─────────────────────────────────────────────────────
    eps = fundamentals.get("eps_ttm")
    if eps is not None:
        if eps > 0:
            score += 5
            reasons.append(f"Positive EPS ₹{eps:.2f} — profitable company")
        else:
            score -= 5
            reasons.append(f"Negative EPS ₹{eps:.2f} — loss-making, caution")

    # ── Valuation ─────────────────────────────────────────────────────────────
    pe = fundamentals.get("pe_ratio")
    if pe is not None and pe > 0:
        if 5 <= pe <= 30:
            score += 4
            reasons.append(f"Attractive PE ratio {pe:.1f}")
        elif 30 < pe <= 60:
            score += 2
            reasons.append(f"Moderate PE ratio {pe:.1f}")
        elif pe > 100:
            score -= 2
            reasons.append(f"Elevated PE ratio {pe:.1f} — high expectations priced in")

    # ── Promoter quality proxy (debt-to-equity) ───────────────────────────────
    de = fundamentals.get("debt_to_equity")
    if de is not None:
        if de < 30:
            score += 4
            reasons.append(f"Low debt/equity {de:.1f} — strong balance sheet")
        elif de < 100:
            score += 2
            reasons.append(f"Manageable debt/equity {de:.1f}")
        else:
            score -= 2
            reasons.append(f"High debt/equity {de:.1f} — leveraged balance sheet")

    # ── Revenue / earnings growth ─────────────────────────────────────────────
    rev_growth = fundamentals.get("revenue_growth")
    if rev_growth is not None:
        if rev_growth >= 0.15:
            score += 4
            reasons.append(f"Strong revenue growth {rev_growth*100:.1f}% YoY")
        elif rev_growth >= 0.05:
            score += 2
            reasons.append(f"Moderate revenue growth {rev_growth*100:.1f}% YoY")
        elif rev_growth < 0:
            score -= 2
            reasons.append(f"Declining revenue {rev_growth*100:.1f}% YoY — caution")

    # ── Return on equity ─────────────────────────────────────────────────────
    roe = fundamentals.get("return_on_equity")
    if roe is not None:
        if roe >= 0.18:
            score += 3
            reasons.append(f"High ROE {roe*100:.1f}% — efficient capital use")
        elif roe >= 0.10:
            score += 1
            reasons.append(f"Decent ROE {roe*100:.1f}%")

    score = max(0, min(score, 20))
    return FundamentalScore(score=score, disqualified=False, reasons=reasons)
