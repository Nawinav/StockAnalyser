"""
FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_cors_origins, settings
from app.database import init_db
from app.scheduler import start_scheduler, stop_scheduler, seed_if_empty
from app.routers import recommendations, stocks, market, intraday, longterm, watchlist, trading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting Indian Stock Analyser API...")
    init_db()
    if settings.ENABLE_SCHEDULER:
        start_scheduler()
        seed_if_empty()
    else:
        logger.info("Scheduler disabled by configuration.")
    logger.info("API ready.")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    if settings.ENABLE_SCHEDULER:
        stop_scheduler()
    logger.info("API shut down cleanly.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Daily intraday stock recommendation engine for the Indian market. "
        "Analyses NSE-listed stocks every morning using technical + fundamental factors "
        "and provides top-10 picks with entry, stop-loss and target prices."
    ),
    lifespan=lifespan,
)

# Allow requests from local React Native / Expo dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(recommendations.router, prefix="/api")
app.include_router(stocks.router,          prefix="/api")
app.include_router(market.router,          prefix="/api")
app.include_router(intraday.router,        prefix="/api")
app.include_router(longterm.router,        prefix="/api")
app.include_router(watchlist.router,       prefix="/api")
app.include_router(trading.router,         prefix="/api")


@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
