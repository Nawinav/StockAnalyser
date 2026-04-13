"""
Scheduler — two automatic jobs:
  1. Intraday refresh: every 10 minutes during market hours (09:15–15:30 IST, Mon–Fri)
  2. Long-term analysis: once daily at 08:00 IST (Mon–Fri)

The manual "Run Analysis Now" trigger has been removed — everything is automatic.
"""
import logging
from datetime import date, datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

IST = pytz.timezone("Asia/Kolkata")


def _is_market_hours() -> bool:
    """Return True if current IST time is within 09:15–15:30 on a weekday."""
    now = datetime.now(IST)
    if now.weekday() >= 5:   # Saturday / Sunday
        return False
    t = now.time()
    market_open  = datetime.strptime(settings.MARKET_OPEN_TIME,  "%H:%M").time()
    market_close = datetime.strptime(settings.MARKET_CLOSE_TIME, "%H:%M").time()
    return market_open <= t <= market_close


# ── Job 1: Intraday — every 10 minutes during market hours ───────────────────

def run_intraday_refresh():
    """
    Runs every 10 minutes during market hours.
    Scans all NSE stocks using pure technical analysis and saves a fresh snapshot.
    """
    if not _is_market_hours():
        logger.debug("[Intraday] Outside market hours — skipping")
        return

    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import IntradaySnapshot
    from app.services.data_fetcher import fetch_index_data
    from app.services.technical_analysis import calculate_all_indicators, get_market_trend
    from app.services.stock_scorer import run_full_analysis

    db: Session = SessionLocal()
    now_ist = datetime.now(IST)

    try:
        logger.info(f"[Intraday] Refresh started at {now_ist.strftime('%H:%M IST')}")

        nifty_df = fetch_index_data("^NSEI", period="3mo")
        nifty_trend = "neutral"
        if nifty_df is not None:
            nifty_trend = get_market_trend(calculate_all_indicators(nifty_df))

        top_stocks = run_full_analysis(market_trend=nifty_trend)

        snapshot_at = datetime.now(IST)
        for rank, stock in enumerate(top_stocks, start=1):
            row = IntradaySnapshot(
                snapshot_at=snapshot_at,
                rank=rank,
                symbol=stock["symbol"],
                company_name=stock.get("company_name"),
                sector=stock.get("sector"),
                entry_price=stock.get("entry_price"),
                stop_loss=stock.get("stop_loss"),
                sl_percentage=stock.get("sl_percentage"),
                target1=stock.get("target1"),
                target1_percentage=stock.get("target1_percentage"),
                target2=stock.get("target2"),
                target2_percentage=stock.get("target2_percentage"),
                score=stock.get("score"),
                rsi=stock.get("rsi"),
                macd=stock.get("macd"),
                macd_signal=stock.get("macd_signal"),
                adx=stock.get("adx"),
                ema9=stock.get("ema9"),
                ema21=stock.get("ema21"),
                ema50=stock.get("ema50"),
                atr=stock.get("atr"),
                volume_ratio=stock.get("volume_ratio"),
                pe_ratio=stock.get("pe_ratio"),
                market_cap_cr=stock.get("market_cap_cr"),
                reasons="|".join(stock.get("reasons", [])),
                nifty_trend=nifty_trend,
            )
            db.add(row)

        db.commit()
        logger.info(f"[Intraday] Saved {len(top_stocks)} picks  (NIFTY: {nifty_trend})")

    except Exception as exc:
        db.rollback()
        logger.exception(f"[Intraday] Refresh failed: {exc}")
    finally:
        db.close()


# ── Job 2: Long-term — once daily at 08:00 IST ───────────────────────────────

def run_long_term_analysis_job():
    """
    Runs once per trading day at 08:00 IST.
    Scores stocks on fundamental quality + growth and persists top-10.
    """
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import LongTermRecommendation
    from app.services.long_term_scorer import run_long_term_analysis

    db: Session = SessionLocal()
    today = date.today()

    try:
        logger.info(f"[LongTerm] Analysis started for {today}")
        top_stocks = run_long_term_analysis()

        db.query(LongTermRecommendation).filter(
            LongTermRecommendation.run_date == today
        ).delete(synchronize_session=False)

        for rank, stock in enumerate(top_stocks, start=1):
            row = LongTermRecommendation(
                run_date=today,
                rank=rank,
                symbol=stock["symbol"],
                company_name=stock.get("company_name"),
                sector=stock.get("sector"),
                industry=stock.get("industry"),
                current_price=stock.get("current_price"),
                week52_high=stock.get("week52_high"),
                week52_low=stock.get("week52_low"),
                pe_ratio=stock.get("pe_ratio"),
                pb_ratio=stock.get("pb_ratio"),
                eps_ttm=stock.get("eps_ttm"),
                roe=stock.get("roe"),
                debt_to_equity=stock.get("debt_to_equity"),
                revenue_growth=stock.get("revenue_growth"),
                earnings_growth=stock.get("earnings_growth"),
                profit_margins=stock.get("profit_margins"),
                dividend_yield=stock.get("dividend_yield"),
                market_cap_cr=stock.get("market_cap_cr"),
                fundamental_score=stock.get("fundamental_score"),
                technical_score=stock.get("technical_score"),
                total_score=stock.get("total_score"),
                hold_period=stock.get("hold_period"),
                hold_rationale=stock.get("hold_rationale"),
                reasons="|".join(stock.get("reasons", [])),
            )
            db.add(row)

        db.commit()
        logger.info(f"[LongTerm] Saved {len(top_stocks)} picks for {today}")

    except Exception as exc:
        db.rollback()
        logger.exception(f"[LongTerm] Analysis failed: {exc}")
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone=IST)

    # Job 1 — Intraday refresh every 10 minutes
    _scheduler.add_job(
        func=run_intraday_refresh,
        trigger=IntervalTrigger(minutes=10, timezone=IST),
        id="intraday_refresh",
        name="Intraday 10-min Stock Refresh",
        replace_existing=True,
    )

    # Job 2 — Long-term analysis once daily at 08:00 IST (Mon–Fri)
    _scheduler.add_job(
        func=run_long_term_analysis_job,
        trigger=CronTrigger(day_of_week="mon-fri", hour=8, minute=0, timezone=IST),
        id="longterm_analysis",
        name="Daily Long-Term Fundamental Analysis",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("[Scheduler] Started — intraday every 10 min | long-term daily at 08:00 IST")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")

