"""
Recommendations Router — returns daily buy recommendations.
"""
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import DailyRecommendation, AnalysisRun
from app.config import settings

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


# ── Pydantic response schemas ──────────────────────────────────────────────

class RecommendationOut(BaseModel):
    id: int
    rank: int
    trade_date: date
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

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_reasons(cls, obj: DailyRecommendation):
        d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        raw_reasons = d.pop("reasons", "") or ""
        d["reasons"] = [r for r in raw_reasons.split("|") if r]
        return cls(**d)


class TodayResponse(BaseModel):
    trade_date: date
    nifty_trend: Optional[str]
    total_recommendations: int
    analyzed_at: Optional[str]
    recommendations: list[RecommendationOut]


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/today", response_model=TodayResponse, summary="Today's top-10 buy recommendations")
def get_today_recommendations(db: Session = Depends(get_db)):
    today = date.today()
    recs = (
        db.query(DailyRecommendation)
        .filter(DailyRecommendation.trade_date == today)
        .order_by(DailyRecommendation.rank)
        .all()
    )

    # Get latest analysis run info
    run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.run_date == today)
        .order_by(AnalysisRun.id.desc())
        .first()
    )

    return TodayResponse(
        trade_date=today,
        nifty_trend=run.nifty_trend if run else None,
        total_recommendations=len(recs),
        analyzed_at=str(run.run_at) if run else None,
        recommendations=[RecommendationOut.from_orm_with_reasons(r) for r in recs],
    )


@router.get("/history", summary="Recommendations for a specific date or past N days")
def get_history(
    date_str: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD"),
    days: int = Query(7, ge=1, le=90, description="Number of past trading days"),
    db: Session = Depends(get_db),
):
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        recs = (
            db.query(DailyRecommendation)
            .filter(DailyRecommendation.trade_date == target_date)
            .order_by(DailyRecommendation.rank)
            .all()
        )
    else:
        since = date.today() - timedelta(days=days)
        recs = (
            db.query(DailyRecommendation)
            .filter(DailyRecommendation.trade_date >= since)
            .order_by(DailyRecommendation.trade_date.desc(), DailyRecommendation.rank)
            .all()
        )

    return [RecommendationOut.from_orm_with_reasons(r) for r in recs]


@router.post("/trigger", status_code=202, summary="Manually trigger today's analysis (async)")
def trigger_analysis(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Kick off a fresh analysis in the background — useful for manual runs or testing."""
    from app.scheduler import run_daily_analysis
    background_tasks.add_task(run_daily_analysis)
    return {"message": "Analysis triggered. Check /today in ~5-10 minutes."}
