"""
Long-Term Router — top-10 long-term investment picks with news.
"""
import logging
from typing import Optional
from datetime import date, datetime

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import LongTermRecommendation

router = APIRouter(prefix="/longterm", tags=["LongTerm"])
logger = logging.getLogger(__name__)


class NewsItem(BaseModel):
    title: str
    publisher: str
    link: str
    published_at: int   # unix timestamp


class LongTermStockOut(BaseModel):
    id: int
    run_date: date
    rank: int
    symbol: str
    company_name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    current_price: Optional[float]
    week52_high: Optional[float]
    week52_low: Optional[float]
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    eps_ttm: Optional[float]
    roe: Optional[float]
    debt_to_equity: Optional[float]
    revenue_growth: Optional[float]
    earnings_growth: Optional[float]
    profit_margins: Optional[float]
    dividend_yield: Optional[float]
    market_cap_cr: Optional[float]
    fundamental_score: Optional[int]
    technical_score: Optional[int]
    total_score: Optional[int]
    hold_period: Optional[str]
    hold_rationale: Optional[str]
    reasons: Optional[list[str]]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_obj(cls, obj: LongTermRecommendation):
        d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        raw = d.pop("reasons", "") or ""
        d["reasons"] = [r for r in raw.split("|") if r]
        return cls(**d)


class LongTermResponse(BaseModel):
    run_date: date
    total: int
    stocks: list[LongTermStockOut]


@router.get("/top10", response_model=LongTermResponse, summary="Long-term top-10 picks")
def get_longterm_top10(db: Session = Depends(get_db)):
    """Returns the latest long-term fundamental picks (updated daily)."""
    latest_row = (
        db.query(LongTermRecommendation.run_date)
        .order_by(LongTermRecommendation.run_date.desc())
        .first()
    )

    if not latest_row:
        return LongTermResponse(run_date=date.today(), total=0, stocks=[])

    run_date = latest_row[0]
    rows = (
        db.query(LongTermRecommendation)
        .filter(LongTermRecommendation.run_date == run_date)
        .order_by(LongTermRecommendation.rank.asc())
        .all()
    )

    return LongTermResponse(
        run_date=run_date,
        total=len(rows),
        stocks=[LongTermStockOut.from_orm_obj(r) for r in rows],
    )


@router.get("/{symbol}/news", response_model=list[NewsItem], summary="Latest news for a stock")
def get_stock_news(symbol: str):
    """Returns latest news articles for this stock via yfinance."""
    from app.services.data_fetcher import fetch_stock_news
    return fetch_stock_news(symbol.upper(), max_items=8)
