"""
Watchlist Router — CRUD for user's long-term watchlist.
"""
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import WatchlistItem

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])
logger = logging.getLogger(__name__)


class WatchlistItemOut(BaseModel):
    id: int
    symbol: str
    company_name: Optional[str]
    sector: Optional[str]
    added_price: Optional[float]
    current_price: Optional[float]
    score: Optional[int]
    hold_period: Optional[str]
    notes: Optional[str]
    added_at: Optional[datetime]
    news: Optional[list[dict]] = None

    class Config:
        from_attributes = True


class AddToWatchlistRequest(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    added_price: Optional[float] = None
    score: Optional[int] = None
    hold_period: Optional[str] = None
    notes: Optional[str] = None


@router.get("/", response_model=list[WatchlistItemOut], summary="Get all watchlist items")
def get_watchlist(include_news: bool = False, db: Session = Depends(get_db)):
    items = db.query(WatchlistItem).order_by(WatchlistItem.added_at.desc()).all()
    result = []
    for item in items:
        d = WatchlistItemOut.from_orm(item)
        if include_news:
            from app.services.data_fetcher import fetch_stock_news
            try:
                d.news = fetch_stock_news(item.symbol, max_items=3)
            except Exception:
                d.news = []
        result.append(d)
    return result


@router.post("/", response_model=WatchlistItemOut, status_code=201, summary="Add stock to watchlist")
def add_to_watchlist(req: AddToWatchlistRequest, db: Session = Depends(get_db)):
    existing = db.query(WatchlistItem).filter(WatchlistItem.symbol == req.symbol.upper()).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"{req.symbol.upper()} is already in watchlist")

    item = WatchlistItem(
        symbol=req.symbol.upper(),
        company_name=req.company_name,
        sector=req.sector,
        added_price=req.added_price,
        score=req.score,
        hold_period=req.hold_period,
        notes=req.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return WatchlistItemOut.from_orm(item)


@router.delete("/{symbol}", status_code=204, summary="Remove stock from watchlist")
def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    item = db.query(WatchlistItem).filter(WatchlistItem.symbol == symbol.upper()).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"{symbol.upper()} not in watchlist")
    db.delete(item)
    db.commit()


@router.get("/{symbol}/news", summary="News for a watchlist stock")
def get_watchlist_news(symbol: str, db: Session = Depends(get_db)):
    item = db.query(WatchlistItem).filter(WatchlistItem.symbol == symbol.upper()).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"{symbol.upper()} not in watchlist")
    from app.services.data_fetcher import fetch_stock_news
    return fetch_stock_news(symbol.upper(), max_items=8)
