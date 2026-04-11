"""
Scheduler — triggers the daily pre-market analysis at 08:30 IST.
Uses APScheduler with IST timezone (Asia/Kolkata).
"""
import logging
from datetime import date, datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def run_daily_analysis():
    """
    Core job: scan the market, score stocks, persist top-10 to the database.
    Runs at 08:30 IST every weekday (Mon–Fri).
    """
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import DailyRecommendation, AnalysisRun
    from app.services.data_fetcher import fetch_index_data
    from app.services.technical_analysis import calculate_all_indicators, get_market_trend
    from app.services.stock_scorer import run_full_analysis

    db: Session = SessionLocal()
    today = date.today()
    status = "failed"
    error_msg = None
    nifty_trend = "neutral"
    scanned = 0
    qualified = 0

    try:
        logger.info(f"[Scheduler] Daily analysis started for {today}")

        # 1. Determine overall market trend
        nifty_df = fetch_index_data("^NSEI", period="3mo")
        if nifty_df is not None:
            nifty_with_indicators = calculate_all_indicators(nifty_df)
            nifty_trend = get_market_trend(nifty_with_indicators)
        logger.info(f"[Scheduler] NIFTY trend: {nifty_trend}")

        # 2. Scan stocks
        from app.services.nse_stocks import get_all_symbols
        scanned = len(get_all_symbols())
        top_stocks = run_full_analysis(market_trend=nifty_trend)
        qualified = len(top_stocks)

        # 3. Remove previous recommendations for today (idempotent re-run)
        db.query(DailyRecommendation).filter(
            DailyRecommendation.trade_date == today
        ).delete(synchronize_session=False)

        # 4. Persist new recommendations
        for rank, stock in enumerate(top_stocks, start=1):
            rec = DailyRecommendation(
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
            db.add(rec)

        db.commit()
        status = "success"
        logger.info(f"[Scheduler] Saved {qualified} recommendations for {today}")

    except Exception as exc:
        db.rollback()
        error_msg = str(exc)
        logger.exception(f"[Scheduler] Analysis failed: {exc}")
    finally:
        # Log the run
        run_log = AnalysisRun(
            run_date=today,
            stocks_scanned=scanned,
            stocks_qualified=qualified,
            nifty_trend=nifty_trend,
            status=status,
            error_message=error_msg,
        )
        db.add(run_log)
        db.commit()
        db.close()


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    ist = pytz.timezone(settings.TIMEZONE)
    _scheduler = BackgroundScheduler(timezone=ist)

    # Parse analysis time (default 08:30)
    hour, minute = map(int, settings.PRE_MARKET_ANALYSIS_TIME.split(":"))

    _scheduler.add_job(
        func=run_daily_analysis,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=hour,
            minute=minute,
            timezone=ist,
        ),
        id="daily_analysis",
        name="Daily Pre-Market Stock Analysis",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        f"[Scheduler] Started — daily analysis scheduled at "
        f"{settings.PRE_MARKET_ANALYSIS_TIME} IST (Mon-Fri)"
    )


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")
