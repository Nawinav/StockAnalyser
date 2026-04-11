"""
Stocks Router — on-demand analysis for a single symbol.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/stocks", tags=["Stocks"])
logger = logging.getLogger(__name__)


class StockAnalysisResponse(BaseModel):
    symbol: str
    company_name: Optional[str]
    sector: Optional[str]
    entry_price: Optional[float]
    stop_loss: Optional[float]
    sl_percentage: Optional[float]
    target1: Optional[float]
    target1_percentage: Optional[float]
    target2: Optional[float]
    target2_percentage: Optional[float]
    score: Optional[int]
    rsi: Optional[float]
    macd: Optional[float]
    adx: Optional[float]
    ema9: Optional[float]
    ema21: Optional[float]
    ema50: Optional[float]
    volume_ratio: Optional[float]
    pe_ratio: Optional[float]
    market_cap_cr: Optional[float]
    week52_high: Optional[float]
    week52_low: Optional[float]
    pct_change_1d: Optional[float]
    pct_change_5d: Optional[float]
    patterns: Optional[list[str]]
    reasons: Optional[list[str]]


@router.get("/{symbol}", response_model=StockAnalysisResponse, summary="Analyse a single stock on demand")
def analyse_stock(symbol: str):
    """
    Fetch data and run the full analysis for any NSE symbol.
    Useful for checking a specific stock outside the daily batch.
    """
    from app.services.data_fetcher import fetch_ohlcv, fetch_fundamentals
    from app.services.stock_scorer import score_stock

    symbol = symbol.upper().strip()

    ohlcv = fetch_ohlcv(symbol)
    if ohlcv is None:
        raise HTTPException(status_code=404, detail=f"No data found for symbol '{symbol}'. Check the NSE symbol.")

    fundamentals = fetch_fundamentals(symbol)

    # Override score threshold to always return analysis even if score is low
    from app.config import settings
    orig_threshold = settings.MIN_SCORE_THRESHOLD
    settings.MIN_SCORE_THRESHOLD = 0  # temporarily disable for single-stock view

    result = score_stock(symbol, ohlcv, fundamentals, market_trend="neutral")

    settings.MIN_SCORE_THRESHOLD = orig_threshold

    if result is None:
        # Re-run without fundamental filter to still return indicators
        from app.services.technical_analysis import calculate_all_indicators
        df = calculate_all_indicators(ohlcv)
        if df is not None:
            last = df.iloc[-1]
            return StockAnalysisResponse(
                symbol=symbol,
                company_name=fundamentals.get("company_name", symbol),
                sector=fundamentals.get("sector"),
                entry_price=round(float(last["close"]), 2),
                stop_loss=None,
                sl_percentage=None,
                target1=None,
                target1_percentage=None,
                target2=None,
                target2_percentage=None,
                score=0,
                rsi=round(float(last["rsi"]), 2) if not __import__("pandas").isna(last["rsi"]) else None,
                macd=None,
                adx=None,
                ema9=None,
                ema21=None,
                ema50=None,
                volume_ratio=None,
                pe_ratio=fundamentals.get("pe_ratio"),
                market_cap_cr=fundamentals.get("market_cap_cr"),
                week52_high=fundamentals.get("week52_high"),
                week52_low=fundamentals.get("week52_low"),
                pct_change_1d=None,
                pct_change_5d=None,
                patterns=[],
                reasons=["Score too low for recommendation"],
            )
        raise HTTPException(status_code=422, detail="Unable to compute indicators for this symbol.")

    return StockAnalysisResponse(**result)


@router.get("/", summary="Search stocks in the universe")
def list_stocks(q: Optional[str] = Query(None, description="Filter by symbol name (partial match)")):
    from app.services.nse_stocks import get_all_symbols
    symbols = get_all_symbols()
    if q:
        q_upper = q.upper()
        symbols = [s for s in symbols if q_upper in s]
    return {"symbols": symbols, "total": len(symbols)}
