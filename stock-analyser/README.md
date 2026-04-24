# Indian Stock Analyser

A **personal-use** cross-platform (mobile + desktop) application that analyses Indian NSE stocks every morning and recommends the **top 10 intraday trades** with entry price, stop-loss, and two profit targets.

---

## Architecture

```
stock-analyser/
├── backend/           ← Python FastAPI — analysis engine + REST API
│   ├── app/
│   │   ├── main.py               FastAPI app
│   │   ├── config.py             All settings
│   │   ├── models.py             SQLite DB models
│   │   ├── scheduler.py          Daily 08:30 IST cron job
│   │   └── services/
│   │       ├── nse_stocks.py     NSE stock universe (~150 stocks)
│   │       ├── data_fetcher.py   yfinance OHLCV + fundamental data
│   │       ├── technical_analysis.py  All indicators (RSI, MACD, EMA, ATR, ADX…)
│   │       ├── fundamental_analysis.py  PE, DE, ROE, revenue growth filter
│   │       └── stock_scorer.py   Scoring algorithm + SL/Target calc
│   └── routers/
│       ├── recommendations.py    GET /today, /history, POST /trigger
│       ├── stocks.py             GET /<symbol> — on-demand analysis
│       └── market.py             GET /status — NIFTY trend + market hours
│
└── frontend/          ← React Native (Expo) — iOS / Android / Web
    ├── App.tsx
    └── src/
        ├── screens/
        │   ├── HomeScreen.tsx         Today's top-10 picks
        │   ├── HistoryScreen.tsx      Past recommendations
        │   ├── StockDetailScreen.tsx  Full analysis for a single stock
        │   └── SearchScreen.tsx       Analyse any NSE symbol on demand
        ├── components/
        │   ├── StockCard.tsx          Compact recommendation card
        │   └── MarketStatusBar.tsx    NIFTY live status banner
        └── services/api.ts            Axios wrapper
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11 or later |
| Node.js | 18 or later |
| npm | 9 or later |

---

## Quick Start (Windows)

```bat
# One-time setup (installs all dependencies)
setup.bat

# Start backend
start_backend.bat

# In a separate terminal — start the app
cd frontend
npx expo start
```

Press **`w`** in the Expo terminal to open the **web version** (desktop browser).
Scan the QR code with **Expo Go** on your phone for mobile.

---

## Running Manually

### Backend
```bat
cd backend
venv\Scripts\activate
python run.py
```
API runs at **http://localhost:8000**
Swagger docs at **http://localhost:8000/docs**

### Frontend
```bat
cd frontend
npm install        # first time only
npx expo start
```

---

## How the Analysis Works

### Daily Schedule
The backend runs a stock scan every weekday at **08:30 AM IST** (before market opens at 09:15 AM).

### Stock Universe
~150 NSE-listed stocks across:
- NIFTY 50 (large-cap)
- NIFTY Next 50 (large-mid cap)
- NIFTY Midcap 100 (mid-cap)

### Scoring (0–100)

| Category | Max Points | Key Signals |
|----------|-----------|-------------|
| Trend Alignment | 30 | EMA 9/21/50/200 position & crossovers |
| Momentum | 25 | RSI (40-68 ideal zone), MACD crossover, histogram expansion |
| Volume | 20 | Volume vs 20-day average; OBV trend |
| Candlestick | 15 | Marubozu, Engulfing, Hammer, Morning Star |
| Trend Strength | 10 | ADX > 20, DI+ > DI- |
| Fundamental Bonus | +20 | PE, EPS, Debt/Equity, Revenue growth, ROE |

Market trend (NIFTY overall) adds +5 (bullish) or applies a −25% penalty (bearish).

### Risk Management

| Parameter | Formula |
|-----------|---------|
| **Entry** | Previous day's close (approximate morning open) |
| **Stop Loss** | `max(prev_candle_low, entry − 1.5×ATR)` — capped 0.4% to 2.0% |
| **Target 1** | `entry + 1.5 × risk` (1:1.5 R:R) |
| **Target 2** | `entry + 2.5 × risk` (1:2.5 R:R) |

> ⚠️ **Square off all positions before 3:25 PM IST** — this is a same-day intraday strategy.

---

## Manual Analysis Trigger

You don't have to wait for 08:30 AM. Trigger a fresh analysis anytime:

**Via Swagger UI:** http://localhost:8000/docs → `POST /api/recommendations/trigger`

**Via the app:** Tap the refresh ↺ icon on the Home screen → "Start"

The analysis scans ~150 stocks and takes **5–10 minutes** depending on your internet speed (Yahoo Finance rate limits apply).

---

## Staged Trading Rollout

The backend now includes a staged execution layer with **Upstox** as the first broker target.

### Safety Defaults
- `TRADING_MODE=paper`
- `ALLOW_LIVE_TRADING=False`
- paper trades are created only from the latest recommendation set
- server-side stop-loss, target monitoring, max daily loss, and emergency stop are enforced

### Key API Endpoints
- `GET /api/trading/control` â€” trading guardrails + broker readiness
- `GET /api/trading/broker/status` â€” Upstox configuration status
- `GET /api/trading/backtest?days=20` â€” backtest stored daily recommendations
- `POST /api/trading/paper/start` â€” start paper trades from `intraday` or `daily` picks
- `POST /api/trading/paper/monitor` â€” run one monitoring cycle now
- `GET /api/trading/orders` â€” recent paper/live order state
- `POST /api/trading/control` â€” toggle emergency stop or paper/live flags
- `POST /api/trading/square-off` â€” close every open position immediately

### Live Broker Notes
- Live orders remain blocked until `ALLOW_LIVE_TRADING=True`
- Upstox live order submission currently expects an `instrument_token` per order
- paper mode and backtests should be validated before enabling any live route

---

## Phone / Tablet Access

Update the `BASE_URL` in `frontend/src/services/api.ts` with your PC's local IP:

```ts
const BASE_URL = 'http://192.168.1.XXX:8000/api';
```

Run the backend with `HOST=0.0.0.0` (already the default) so it accepts connections from other devices on the same Wi-Fi.

---

## Data Sources

- **Price data:** Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) (free, no API key needed)
- **Fundamental data:** Yahoo Finance `.info` endpoint
- **Index data:** `^NSEI` (NIFTY 50) from Yahoo Finance

---

## Disclaimer

> This application is for **personal educational use only**. It does not constitute financial advice. Always do your own research and trade at your own risk. Past analysis performance does not guarantee future results.

---

## License

MIT — Personal use only.
