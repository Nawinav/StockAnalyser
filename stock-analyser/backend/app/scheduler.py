"""
Scheduler — two automatic jobs:
  1. Intraday refresh: every 10 minutes during market hours (09:15–15:30 IST, Mon–Fri)
  2. Long-term analysis: once daily at 08:00 IST (Mon–Fri)

The manual "Run Analysis Now" trigger has been removed — everything is automatic.
"""
import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
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

def run_daily_analysis():
    """
    Runs once per trading day before market open.
    Persists the main recommendation set used for backtesting and paper-trade seeding.
    """
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import AnalysisRun, DailyRecommendation
    from app.services.data_fetcher import fetch_index_data
    from app.services.stock_scorer import run_full_analysis
    from app.services.technical_analysis import calculate_all_indicators, get_market_trend

    db: Session = SessionLocal()
    today = datetime.now(IST).date()

    try:
        logger.info(f"[Daily] Analysis started for {today}")

        nifty_df = fetch_index_data("^NSEI", period="3mo")
        nifty_trend = "neutral"
        if nifty_df is not None:
            nifty_trend = get_market_trend(calculate_all_indicators(nifty_df))

        top_stocks = run_full_analysis(market_trend=nifty_trend)

        db.query(DailyRecommendation).filter(
            DailyRecommendation.trade_date == today
        ).delete(synchronize_session=False)

        for rank, stock in enumerate(top_stocks, start=1):
            db.add(
                DailyRecommendation(
                    trade_date=today,
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
                )
            )

        db.add(
            AnalysisRun(
                run_date=today,
                stocks_scanned=None,
                stocks_qualified=len(top_stocks),
                nifty_trend=nifty_trend,
                status="success",
            )
        )
        db.commit()
        logger.info(f"[Daily] Saved {len(top_stocks)} recommendations for {today}")

    except Exception as exc:
        db.rollback()
        db.add(
            AnalysisRun(
                run_date=today,
                stocks_scanned=None,
                stocks_qualified=0,
                nifty_trend="unknown",
                status="failed",
                error_message=str(exc),
            )
        )
        db.commit()
        logger.exception(f"[Daily] Analysis failed: {exc}")
    finally:
        db.close()


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


def run_trade_monitoring():
    """
    Monitor all open paper trades and enforce stop-loss / target / square-off rules.
    """
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.services.trading_engine import run_paper_monitor

    if not _is_market_hours():
        logger.debug("[Trading] Outside market hours - skipping")
        return

    db: Session = SessionLocal()
    try:
        result = run_paper_monitor(db)
        if result["checked"]:
            logger.info(f"[Trading] Monitored {result['checked']} open trade(s)")
    except Exception as exc:
        logger.exception(f"[Trading] Monitoring failed: {exc}")
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
    today = datetime.now(IST).date()

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
    pre_market_hour, pre_market_minute = map(int, settings.PRE_MARKET_ANALYSIS_TIME.split(":"))

    # Job 1 — Intraday refresh every 10 minutes (market-hours guard is inside the job)
    _scheduler.add_job(
        func=run_intraday_refresh,
        trigger=IntervalTrigger(minutes=10, timezone=IST),
        id="intraday_refresh",
        name="Intraday 10-min Stock Refresh",
        replace_existing=True,
    )

    # Job 2 — Market open: first snapshot exactly at 09:16 IST so data is ready immediately
    _scheduler.add_job(
        func=run_intraday_refresh,
        trigger=CronTrigger(day_of_week="mon-fri", hour=9, minute=16, timezone=IST),
        id="market_open_snapshot",
        name="Market Open First Intraday Snapshot",
        replace_existing=True,
    )

    # Job 3 — Market close: final snapshot at 15:25 IST to capture end-of-day state
    _scheduler.add_job(
        func=run_intraday_refresh,
        trigger=CronTrigger(day_of_week="mon-fri", hour=15, minute=25, timezone=IST),
        id="market_close_snapshot",
        name="Market Close Final Intraday Snapshot",
        replace_existing=True,
    )

    _scheduler.add_job(
        func=run_daily_analysis,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=pre_market_hour,
            minute=pre_market_minute,
            timezone=IST,
        ),
        id="daily_recommendation_analysis",
        name="Daily Intraday Recommendation Analysis",
        replace_existing=True,
    )

    _scheduler.add_job(
        func=run_trade_monitoring,
        trigger=IntervalTrigger(minutes=1, timezone=IST),
        id="paper_trade_monitor",
        name="Paper Trade Monitor",
        replace_existing=True,
    )

    # Job 4 — Long-term analysis once daily at 08:00 IST (Mon–Fri)
    _scheduler.add_job(
        func=run_long_term_analysis_job,
        trigger=CronTrigger(day_of_week="mon-fri", hour=8, minute=0, timezone=IST),
        id="longterm_analysis",
        name="Daily Long-Term Fundamental Analysis",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "[Scheduler] Started - daily recommendations at %s | intraday every 10 min (+09:16, 15:25) | paper monitor every 1 min | long-term daily at 08:00 IST",
        settings.PRE_MARKET_ANALYSIS_TIME,
    )
    logger.info("[Scheduler] Started — intraday every 10 min (+ 09:16 open, 15:25 close) | long-term daily at 08:00 IST")


def seed_if_empty():
    """
    Called once on startup.
    If the DB has no data yet (fresh install), immediately queues background
    analyses so the UI is never blank when first opened.
    """
    import threading
    from app.database import SessionLocal
    from app.models import DailyRecommendation, LongTermRecommendation, IntradaySnapshot

    db = SessionLocal()
    try:
        has_daily = db.query(DailyRecommendation.id).first() is not None
        has_longterm = db.query(LongTermRecommendation.id).first() is not None
        has_intraday = db.query(IntradaySnapshot.id).first() is not None
    finally:
        db.close()

    if not has_daily:
        logger.info("[Startup] No daily recommendations found - queuing pre-market analysis...")
        threading.Thread(target=run_daily_analysis, daemon=True).start()

    if not has_longterm:
        logger.info("[Startup] No long-term data found — queuing initial fundamental analysis…")
        threading.Thread(target=run_long_term_analysis_job, daemon=True).start()

    if not has_intraday and _is_market_hours():
        logger.info("[Startup] No intraday data and market is open — queuing initial scan…")
        threading.Thread(target=run_intraday_refresh, daemon=True).start()


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")

