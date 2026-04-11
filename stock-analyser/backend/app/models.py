from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Date
from sqlalchemy.sql import func
from app.database import Base
import datetime


class DailyRecommendation(Base):
    """Stores top-10 intraday stock recommendations for each trading day."""
    __tablename__ = "daily_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    rank = Column(Integer, nullable=False)               # 1-10
    symbol = Column(String(20), nullable=False)
    company_name = Column(String(100))
    sector = Column(String(60))

    # Entry / Risk
    entry_price = Column(Float)
    stop_loss = Column(Float)
    sl_percentage = Column(Float)
    target1 = Column(Float)
    target1_percentage = Column(Float)
    target2 = Column(Float)
    target2_percentage = Column(Float)

    # Score
    score = Column(Integer)

    # Technical snapshot
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    adx = Column(Float)
    ema9 = Column(Float)
    ema21 = Column(Float)
    ema50 = Column(Float)
    atr = Column(Float)
    volume_ratio = Column(Float)

    # Fundamental snapshot
    pe_ratio = Column(Float)
    market_cap_cr = Column(Float)

    # Analysis reasons (pipe-separated bullets)
    reasons = Column(Text)

    # Outcome tracking (filled EOD or next day)
    high_of_day = Column(Float, nullable=True)
    low_of_day = Column(Float, nullable=True)
    close_price = Column(Float, nullable=True)
    target1_hit = Column(Boolean, nullable=True)
    target2_hit = Column(Boolean, nullable=True)
    stop_loss_hit = Column(Boolean, nullable=True)
    pnl_percentage = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalysisRun(Base):
    """Log of each analysis run."""
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_date = Column(Date, nullable=False, index=True)
    run_at = Column(DateTime(timezone=True), server_default=func.now())
    stocks_scanned = Column(Integer)
    stocks_qualified = Column(Integer)
    nifty_trend = Column(String(20))       # bullish / bearish / neutral
    status = Column(String(20))            # success / partial / failed
    error_message = Column(Text, nullable=True)
