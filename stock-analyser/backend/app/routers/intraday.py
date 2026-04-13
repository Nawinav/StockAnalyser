"""
Intraday Router — returns latest top-10 intraday stocks refreshed every 10 min.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import IntradaySnapshot

router = APIRouter(prefix="/intraday", tags=["Intraday"])
logger = logging.getLogger(__name__)


class IntradayStockOut(BaseModel):
    id: int
    snapshot_at: Optional[datetime]
    rank: int
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
    reasons: Optional[list[str]]
    nifty_trend: Optional[str]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_obj(cls, obj: IntradaySnapshot):
        d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        raw = d.pop("reasons", "") or ""
        d["reasons"] = [r for r in raw.split("|") if r]
        return cls(**d)


class IntradayResponse(BaseModel):
    snapshot_at: Optional[datetime]
    nifty_trend: Optional[str]
    total: int
    stocks: list[IntradayStockOut]


@router.get("/top10", response_model=IntradayResponse, summary="Latest intraday top-10 stocks")
def get_intraday_top10(db: Session = Depends(get_db)):
    """Returns the most recent intraday snapshot (updated every 10 minutes during market hours)."""
    # Find the latest snapshot_at timestamp
    latest_row = (
        db.query(IntradaySnapshot.snapshot_at)
        .order_by(IntradaySnapshot.snapshot_at.desc())
        .first()
    )

    if not latest_row:
        return IntradayResponse(snapshot_at=None, nifty_trend=None, total=0, stocks=[])

    latest_ts = latest_row[0]
    rows = (
        db.query(IntradaySnapshot)
        .filter(IntradaySnapshot.snapshot_at == latest_ts)
        .order_by(IntradaySnapshot.rank.asc())
        .all()
    )

    nifty_trend = rows[0].nifty_trend if rows else None
    return IntradayResponse(
        snapshot_at=latest_ts,
        nifty_trend=nifty_trend,
        total=len(rows),
        stocks=[IntradayStockOut.from_orm_obj(r) for r in rows],
    )
