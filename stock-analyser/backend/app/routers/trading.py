"""
Trading router for staged rollout:
- broker readiness
- backtesting over stored daily recommendations
- paper trade seeding and monitoring
- emergency controls
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.brokerage import broker_status_dict
from app.services.trading_engine import (
    emergency_square_off,
    ensure_trading_control,
    list_orders,
    run_backtest,
    run_paper_monitor,
    serialize_control,
    start_paper_trading,
    submit_live_order,
    update_control,
)

router = APIRouter(prefix="/trading", tags=["Trading"])


class TradingControlUpdateIn(BaseModel):
    emergency_stop: Optional[bool] = None
    trading_mode: Optional[str] = Field(default=None, pattern="^(paper|live)$")
    paper_trading_enabled: Optional[bool] = None
    live_trading_enabled: Optional[bool] = None
    notes: Optional[str] = None


class PaperStartIn(BaseModel):
    source: str = Field(default="intraday", pattern="^(intraday|daily)$")
    max_trades: int = Field(default=2, ge=1, le=10)
    capital_per_trade: float = Field(default=10000.0, gt=0)


class LiveOrderIn(BaseModel):
    symbol: str
    quantity: int = Field(ge=1)
    instrument_token: str


@router.get("/control", summary="Current trading guardrails and broker readiness")
def get_trading_control(db: Session = Depends(get_db)):
    control = ensure_trading_control(db)
    return serialize_control(control)


@router.post("/control", summary="Update trading guardrails or emergency stop")
def update_trading_control(payload: TradingControlUpdateIn, db: Session = Depends(get_db)):
    control = update_control(
        db,
        emergency_stop=payload.emergency_stop,
        trading_mode=payload.trading_mode,
        paper_trading_enabled=payload.paper_trading_enabled,
        live_trading_enabled=payload.live_trading_enabled,
        notes=payload.notes,
    )
    return serialize_control(control)


@router.get("/broker/status", summary="Configured broker readiness")
def get_broker_status():
    return broker_status_dict()


@router.get("/backtest", summary="Backtest stored daily recommendations")
def backtest_recommendations(
    days: int = Query(default=20, ge=1, le=120),
    db: Session = Depends(get_db),
):
    return run_backtest(db, days=days)


@router.post("/paper/start", summary="Create paper trades from the latest recommendations")
def start_paper_session(payload: PaperStartIn, db: Session = Depends(get_db)):
    return start_paper_trading(
        db,
        source=payload.source,
        max_trades=payload.max_trades,
        capital_per_trade=payload.capital_per_trade,
    )


@router.post("/paper/monitor", summary="Run paper-trade monitoring once now")
def monitor_paper_trades(db: Session = Depends(get_db)):
    return run_paper_monitor(db)


@router.post("/square-off", summary="Force close every open trade immediately")
def force_square_off(db: Session = Depends(get_db)):
    return emergency_square_off(db, reason="manual_square_off")


@router.get("/orders", summary="Recent paper/live orders")
def get_orders(
    status: Optional[str] = Query(default=None, pattern="^(open|closed|submitted)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_orders(db, status=status, limit=limit)


@router.post("/live/order", summary="Submit a live order manually when live mode is enabled")
def place_live_order(payload: LiveOrderIn, db: Session = Depends(get_db)):
    return submit_live_order(
        db,
        symbol=payload.symbol.upper(),
        quantity=payload.quantity,
        instrument_token=payload.instrument_token,
    )
