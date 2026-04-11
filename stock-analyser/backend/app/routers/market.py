"""
Market Router — overall market health & NIFTY snapshot.
"""
from datetime import datetime
import pytz
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/market", tags=["Market"])


class MarketStatusResponse(BaseModel):
    is_open: bool
    status: str
    current_time_ist: str
    market_open: str
    market_close: str
    nifty_trend: Optional[str]
    nifty_last_close: Optional[float]
    nifty_change_pct: Optional[float]


@router.get("/status", response_model=MarketStatusResponse)
def get_market_status():
    """Returns current NSE market status and latest NIFTY snapshot."""
    from app.config import settings
    from app.services.data_fetcher import fetch_index_data
    from app.services.technical_analysis import calculate_all_indicators, get_market_trend

    ist = pytz.timezone(settings.TIMEZONE)
    now_ist = datetime.now(ist)

    open_h, open_m   = map(int, settings.MARKET_OPEN_TIME.split(":"))
    close_h, close_m = map(int, settings.MARKET_CLOSE_TIME.split(":"))

    market_open_dt  = now_ist.replace(hour=open_h,  minute=open_m,  second=0, microsecond=0)
    market_close_dt = now_ist.replace(hour=close_h, minute=close_m, second=0, microsecond=0)

    is_weekday = now_ist.weekday() < 5        # Mon=0 … Fri=4
    is_open    = is_weekday and (market_open_dt <= now_ist <= market_close_dt)

    if not is_weekday:
        status_str = "Closed (Weekend)"
    elif now_ist < market_open_dt:
        status_str = "Pre-Market"
    elif is_open:
        status_str = "Open"
    else:
        status_str = "Closed"

    # NIFTY snapshot
    nifty_last_close  = None
    nifty_change_pct  = None
    nifty_trend       = "neutral"

    try:
        nifty_df = fetch_index_data("^NSEI", period="1mo")
        if nifty_df is not None and len(nifty_df) >= 2:
            nifty_last_close  = round(float(nifty_df["close"].iloc[-1]), 2)
            prev_close        = float(nifty_df["close"].iloc[-2])
            nifty_change_pct  = round((nifty_last_close - prev_close) / prev_close * 100, 2)

            nifty_with_ind = calculate_all_indicators(nifty_df)
            nifty_trend    = get_market_trend(nifty_with_ind)
    except Exception:
        pass

    return MarketStatusResponse(
        is_open=is_open,
        status=status_str,
        current_time_ist=now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        market_open=settings.MARKET_OPEN_TIME,
        market_close=settings.MARKET_CLOSE_TIME,
        nifty_trend=nifty_trend,
        nifty_last_close=nifty_last_close,
        nifty_change_pct=nifty_change_pct,
    )
