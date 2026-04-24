"""
Trading orchestration for staged rollout:
1. Backtest stored recommendations
2. Start paper trades from current candidates
3. Monitor open paper trades with stop-loss / target / square-off logic
4. Keep live order flow hard-gated behind config + control flags
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from math import floor
from typing import Optional

import pytz
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    DailyRecommendation,
    IntradaySnapshot,
    TradeEvent,
    TradeOrder,
    TradingControl,
)
from app.services.brokerage import (
    OrderRequest,
    broker_status_dict,
    get_broker_adapter,
    payload_to_text,
)
from app.services.data_fetcher import fetch_latest_price, fetch_trade_day_candle

logger = logging.getLogger(__name__)

IST = pytz.timezone(settings.TIMEZONE)


def ist_now() -> datetime:
    return datetime.now(IST)


def ensure_trading_control(db: Session) -> TradingControl:
    control = db.get(TradingControl, 1)
    if control:
        return control

    control = TradingControl(
        id=1,
        broker=settings.TRADING_BROKER,
        trading_mode=settings.TRADING_MODE,
        paper_trading_enabled=True,
        live_trading_enabled=settings.ALLOW_LIVE_TRADING,
        emergency_stop=False,
        max_daily_loss_pct=settings.MAX_DAILY_LOSS_PCT,
        max_open_positions=settings.MAX_OPEN_POSITIONS,
        max_position_value=settings.MAX_POSITION_VALUE,
        max_trades_per_day=settings.MAX_TRADES_PER_DAY,
        auto_square_off_time=settings.AUTO_SQUARE_OFF_TIME,
    )
    db.add(control)
    db.commit()
    db.refresh(control)
    return control


def log_trade_event(
    db: Session,
    event_type: str,
    message: str,
    order: Optional[TradeOrder] = None,
    payload: Optional[str] = None,
) -> None:
    db.add(
        TradeEvent(
            order_id=order.id if order else None,
            symbol=order.symbol if order else None,
            event_type=event_type,
            message=message,
            payload=payload,
        )
    )


def serialize_control(control: TradingControl) -> dict:
    status = broker_status_dict()
    return {
        "broker": control.broker,
        "trading_mode": control.trading_mode,
        "paper_trading_enabled": control.paper_trading_enabled,
        "live_trading_enabled": control.live_trading_enabled,
        "emergency_stop": control.emergency_stop,
        "max_daily_loss_pct": control.max_daily_loss_pct,
        "max_open_positions": control.max_open_positions,
        "max_position_value": control.max_position_value,
        "max_trades_per_day": control.max_trades_per_day,
        "auto_square_off_time": control.auto_square_off_time,
        "notes": control.notes,
        "broker_status": status,
        "updated_at": control.updated_at,
    }


def update_control(
    db: Session,
    *,
    emergency_stop: Optional[bool] = None,
    trading_mode: Optional[str] = None,
    live_trading_enabled: Optional[bool] = None,
    paper_trading_enabled: Optional[bool] = None,
    notes: Optional[str] = None,
) -> TradingControl:
    control = ensure_trading_control(db)

    if emergency_stop is not None:
        control.emergency_stop = emergency_stop
    if trading_mode is not None:
        control.trading_mode = trading_mode
    if live_trading_enabled is not None:
        control.live_trading_enabled = live_trading_enabled
    if paper_trading_enabled is not None:
        control.paper_trading_enabled = paper_trading_enabled
    if notes is not None:
        control.notes = notes

    db.add(control)
    db.commit()
    db.refresh(control)
    return control


def _get_latest_intraday_candidates(db: Session, limit: int) -> list[dict]:
    latest_row = (
        db.query(IntradaySnapshot.snapshot_at)
        .order_by(IntradaySnapshot.snapshot_at.desc())
        .first()
    )
    if not latest_row:
        return []

    latest_ts = latest_row[0]
    rows = (
        db.query(IntradaySnapshot)
        .filter(IntradaySnapshot.snapshot_at == latest_ts)
        .order_by(IntradaySnapshot.rank.asc())
        .limit(limit)
        .all()
    )

    return [
        {
            "symbol": row.symbol,
            "company_name": row.company_name,
            "entry_price": row.entry_price,
            "stop_loss": row.stop_loss,
            "target1": row.target1,
            "target2": row.target2,
            "rank": row.rank,
            "source": "intraday",
        }
        for row in rows
    ]


def _get_latest_daily_candidates(db: Session, limit: int) -> list[dict]:
    today = datetime.now(IST).date()
    rows = (
        db.query(DailyRecommendation)
        .filter(DailyRecommendation.trade_date == today)
        .order_by(DailyRecommendation.rank.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "symbol": row.symbol,
            "company_name": row.company_name,
            "entry_price": row.entry_price,
            "stop_loss": row.stop_loss,
            "target1": row.target1,
            "target2": row.target2,
            "rank": row.rank,
            "source": "daily",
        }
        for row in rows
    ]


def get_trade_candidates(db: Session, source: str, limit: int) -> list[dict]:
    source = source.lower()
    if source == "intraday":
        candidates = _get_latest_intraday_candidates(db, limit)
        if candidates:
            return candidates
        return _get_latest_daily_candidates(db, limit)
    if source == "daily":
        return _get_latest_daily_candidates(db, limit)
    raise HTTPException(status_code=400, detail="source must be 'intraday' or 'daily'")


def _current_open_positions(db: Session) -> int:
    return (
        db.query(TradeOrder)
        .filter(TradeOrder.status == "open")
        .count()
    )


def _current_day_trade_count(db: Session) -> int:
    today = datetime.now(IST).date()
    return (
        db.query(TradeOrder)
        .filter(TradeOrder.trade_date == today)
        .count()
    )


def _current_drawdown(db: Session) -> float:
    today = date.today()
    realized = (
        db.query(TradeOrder)
        .filter(TradeOrder.trade_date == today)
        .filter(TradeOrder.realized_pnl.isnot(None))
        .all()
    )
    open_orders = (
        db.query(TradeOrder)
        .filter(TradeOrder.trade_date == today, TradeOrder.status == "open")
        .all()
    )
    realized_loss = sum(min(order.realized_pnl or 0.0, 0.0) for order in realized)
    unrealized_loss = sum(min(order.unrealized_pnl or 0.0, 0.0) for order in open_orders)
    return abs(realized_loss + unrealized_loss)


def _risk_budget_exceeded(db: Session, control: TradingControl) -> bool:
    if settings.PAPER_STARTING_CAPITAL <= 0:
        return False
    drawdown = _current_drawdown(db)
    drawdown_pct = drawdown / settings.PAPER_STARTING_CAPITAL * 100
    return drawdown_pct >= control.max_daily_loss_pct


def _close_order(order: TradeOrder, last_price: float, reason: str) -> None:
    order.status = "closed"
    order.exit_price = round(last_price, 2)
    order.exit_reason = reason
    order.closed_at = ist_now()
    order.current_price = round(last_price, 2)
    pnl = (order.exit_price - (order.entry_price or 0.0)) * order.quantity
    order.realized_pnl = round(pnl, 2)
    if order.entry_price:
        order.realized_pnl_pct = round((order.exit_price - order.entry_price) / order.entry_price * 100, 2)
    order.unrealized_pnl = 0.0


def _paper_entry_price(candidate: dict) -> Optional[float]:
    live_price = fetch_latest_price(candidate["symbol"])
    if live_price is None:
        return candidate.get("entry_price")

    target1 = candidate.get("target1")
    stop_loss = candidate.get("stop_loss")
    if stop_loss and live_price <= stop_loss:
        return None
    if target1 and live_price > target1:
        return None
    return live_price


def start_paper_trading(
    db: Session,
    *,
    source: str,
    max_trades: int,
    capital_per_trade: float,
) -> dict:
    control = ensure_trading_control(db)
    if not control.paper_trading_enabled:
        raise HTTPException(status_code=400, detail="Paper trading is disabled in trading control.")
    if control.emergency_stop:
        raise HTTPException(status_code=409, detail="Emergency stop is active. Clear it before starting new paper trades.")

    open_positions = _current_open_positions(db)
    remaining_slots = max(control.max_open_positions - open_positions, 0)
    if remaining_slots <= 0:
        raise HTTPException(status_code=409, detail="Max open positions already reached.")

    trades_left_today = max(control.max_trades_per_day - _current_day_trade_count(db), 0)
    if trades_left_today <= 0:
        raise HTTPException(status_code=409, detail="Max trades for today already reached.")

    allowed_count = min(max_trades, remaining_slots, trades_left_today)
    candidates = get_trade_candidates(db, source=source, limit=max(max_trades * 2, 5))
    created_orders: list[TradeOrder] = []
    skipped: list[dict] = []

    for candidate in candidates:
        if len(created_orders) >= allowed_count:
            break

        entry_price = _paper_entry_price(candidate)
        if entry_price is None:
            skipped.append({"symbol": candidate["symbol"], "reason": "price already breached stop-loss or target1"})
            continue

        ticket_value = min(capital_per_trade, control.max_position_value)
        quantity = floor(ticket_value / entry_price)
        if quantity < 1:
            skipped.append({"symbol": candidate["symbol"], "reason": "capital per trade too small for 1 share"})
            continue

        risk_per_share = round(max(entry_price - (candidate.get("stop_loss") or entry_price), 0.0), 2)
        order = TradeOrder(
            trade_date=datetime.now(IST).date(),
            symbol=candidate["symbol"],
            company_name=candidate.get("company_name"),
            quantity=quantity,
            status="open",
            broker=control.broker,
            mode="paper",
            source=candidate.get("source", source),
            source_rank=candidate.get("rank"),
            requested_price=candidate.get("entry_price"),
            entry_price=round(entry_price, 2),
            current_price=round(entry_price, 2),
            stop_loss=candidate.get("stop_loss"),
            target1=candidate.get("target1"),
            target2=candidate.get("target2"),
            risk_per_share=risk_per_share,
            position_value=round(entry_price * quantity, 2),
            opened_at=ist_now(),
        )
        db.add(order)
        db.flush()
        log_trade_event(
            db,
            event_type="paper_opened",
            message=f"Opened paper trade for {order.symbol} at {order.entry_price} x {order.quantity}.",
            order=order,
        )
        created_orders.append(order)

    db.commit()

    return {
        "created": len(created_orders),
        "orders": [serialize_order(order) for order in created_orders],
        "skipped": skipped,
    }


def serialize_order(order: TradeOrder) -> dict:
    return {
        "id": order.id,
        "trade_date": order.trade_date,
        "symbol": order.symbol,
        "company_name": order.company_name,
        "quantity": order.quantity,
        "status": order.status,
        "broker": order.broker,
        "mode": order.mode,
        "source": order.source,
        "source_rank": order.source_rank,
        "requested_price": order.requested_price,
        "entry_price": order.entry_price,
        "current_price": order.current_price,
        "stop_loss": order.stop_loss,
        "target1": order.target1,
        "target2": order.target2,
        "position_value": order.position_value,
        "unrealized_pnl": order.unrealized_pnl,
        "realized_pnl": order.realized_pnl,
        "realized_pnl_pct": order.realized_pnl_pct,
        "target1_reached": order.target1_reached,
        "exit_reason": order.exit_reason,
        "opened_at": order.opened_at,
        "closed_at": order.closed_at,
        "instrument_token": order.instrument_token,
        "broker_order_id": order.broker_order_id,
    }


def list_orders(db: Session, *, status: Optional[str] = None, limit: int = 50) -> list[dict]:
    query = db.query(TradeOrder).order_by(TradeOrder.created_at.desc())
    if status:
        query = query.filter(TradeOrder.status == status)
    return [serialize_order(order) for order in query.limit(limit).all()]


def run_paper_monitor(db: Session) -> dict:
    control = ensure_trading_control(db)
    open_orders = (
        db.query(TradeOrder)
        .filter(TradeOrder.status == "open", TradeOrder.mode == "paper")
        .order_by(TradeOrder.opened_at.asc())
        .all()
    )

    updates = []
    now = ist_now()
    square_off_time = datetime.strptime(control.auto_square_off_time, "%H:%M").time()

    for order in open_orders:
        last_price = fetch_latest_price(order.symbol)
        if last_price is None:
            updates.append({"id": order.id, "symbol": order.symbol, "status": "stale", "reason": "price unavailable"})
            continue

        order.current_price = round(last_price, 2)
        order.unrealized_pnl = round((order.current_price - (order.entry_price or 0.0)) * order.quantity, 2)

        if control.emergency_stop:
            _close_order(order, last_price, "emergency_stop")
        elif now.time() >= square_off_time:
            _close_order(order, last_price, "auto_square_off")
        elif order.stop_loss and last_price <= order.stop_loss:
            _close_order(order, last_price, "stop_loss")
        elif order.target2 and last_price >= order.target2:
            _close_order(order, last_price, "target2")
        elif order.target1 and last_price >= order.target1 and not order.target1_reached:
            order.target1_reached = True
            log_trade_event(
                db,
                event_type="target1_reached",
                message=f"{order.symbol} reached target1 at {last_price}.",
                order=order,
            )

        updates.append(
            {
                "id": order.id,
                "symbol": order.symbol,
                "status": order.status,
                "current_price": order.current_price,
                "unrealized_pnl": order.unrealized_pnl,
                "exit_reason": order.exit_reason,
            }
        )

    if _risk_budget_exceeded(db, control):
        control.emergency_stop = True
        for order in open_orders:
            if order.status == "open":
                last_price = order.current_price or order.entry_price or 0.0
                _close_order(order, last_price, "max_daily_loss")
        log_trade_event(
            db,
            event_type="risk_trip",
            message="Emergency stop activated because paper drawdown exceeded max daily loss.",
        )

    db.add(control)
    db.commit()
    return {
        "checked": len(open_orders),
        "updates": updates,
        "emergency_stop": control.emergency_stop,
    }


def emergency_square_off(db: Session, reason: str = "manual_square_off") -> dict:
    open_orders = (
        db.query(TradeOrder)
        .filter(TradeOrder.status == "open")
        .all()
    )
    closed = []

    for order in open_orders:
        last_price = fetch_latest_price(order.symbol) or order.current_price or order.entry_price or 0.0
        _close_order(order, last_price, reason)
        log_trade_event(
            db,
            event_type="forced_exit",
            message=f"Closed {order.symbol} due to {reason}.",
            order=order,
        )
        closed.append(order.symbol)

    db.commit()
    return {"closed_symbols": closed, "count": len(closed)}


def submit_live_order(
    db: Session,
    *,
    symbol: str,
    quantity: int,
    instrument_token: str,
) -> dict:
    control = ensure_trading_control(db)
    if control.emergency_stop:
        raise HTTPException(status_code=409, detail="Emergency stop is active.")
    if not control.live_trading_enabled or not settings.ALLOW_LIVE_TRADING:
        raise HTTPException(status_code=403, detail="Live trading is disabled in configuration.")

    broker = get_broker_adapter()
    response = broker.place_intraday_order(
        OrderRequest(symbol=symbol, quantity=quantity, instrument_token=instrument_token)
    )
    if not response.accepted:
        raise HTTPException(status_code=400, detail=response.message)

    last_price = fetch_latest_price(symbol)
    order = TradeOrder(
        trade_date=datetime.now(IST).date(),
        symbol=symbol,
        company_name=symbol,
        quantity=quantity,
        status="submitted",
        broker=control.broker,
        mode="live",
        source="manual",
        instrument_token=instrument_token,
        broker_order_id=response.broker_order_id,
        entry_price=last_price,
        current_price=last_price,
        opened_at=ist_now(),
    )
    db.add(order)
    db.flush()
    log_trade_event(
        db,
        event_type="live_submitted",
        message=response.message,
        order=order,
        payload=payload_to_text(response.payload),
    )
    db.commit()
    return serialize_order(order)


def run_backtest(db: Session, days: int = 20) -> dict:
    today = datetime.now(IST).date()
    since = today.fromordinal(today.toordinal() - days)
    recommendations = (
        db.query(DailyRecommendation)
        .filter(DailyRecommendation.trade_date >= since)
        .order_by(DailyRecommendation.trade_date.desc(), DailyRecommendation.rank.asc())
        .all()
    )

    results = []
    total_pnl = 0.0
    wins = 0

    for rec in recommendations:
        candle = fetch_trade_day_candle(rec.symbol, rec.trade_date)
        if not candle:
            continue

        exit_price = candle["close"]
        outcome = "close"

        if candle["low"] <= (rec.stop_loss or -1) and candle["high"] >= (rec.target2 or 10**9):
            exit_price = rec.stop_loss
            outcome = "stop_loss_priority"
        elif candle["low"] <= (rec.stop_loss or -1):
            exit_price = rec.stop_loss
            outcome = "stop_loss"
        elif candle["high"] >= (rec.target2 or 10**9):
            exit_price = rec.target2
            outcome = "target2"
        elif candle["high"] >= (rec.target1 or 10**9):
            exit_price = rec.target1
            outcome = "target1"

        entry = rec.entry_price or candle["open"]
        pnl_pct = round((exit_price - entry) / entry * 100, 2) if entry else 0.0
        total_pnl += pnl_pct
        if pnl_pct > 0:
            wins += 1

        results.append(
            {
                "trade_date": rec.trade_date,
                "symbol": rec.symbol,
                "rank": rec.rank,
                "entry_price": entry,
                "stop_loss": rec.stop_loss,
                "target1": rec.target1,
                "target2": rec.target2,
                "day_open": candle["open"],
                "day_high": candle["high"],
                "day_low": candle["low"],
                "day_close": candle["close"],
                "outcome": outcome,
                "exit_price": exit_price,
                "pnl_pct": pnl_pct,
            }
        )

    total = len(results)
    avg_pnl = round(total_pnl / total, 2) if total else 0.0
    win_rate = round(wins / total * 100, 2) if total else 0.0

    return {
        "days_requested": days,
        "trades_evaluated": total,
        "win_rate_pct": win_rate,
        "average_pnl_pct": avg_pnl,
        "total_pnl_pct": round(total_pnl, 2),
        "results": results,
    }
