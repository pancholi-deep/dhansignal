# DhanSignal v0.1 — Phase 1

An Indian-equity market intelligence and paper-trading platform. Phase 1 provides a React + TypeScript dashboard, FastAPI backend, PostgreSQL persistence, a clearly labelled synthetic demo market-data provider, an optional Zerodha Kite Connect adapter, and an experimental technical-signal engine.

> **Disclaimer:** DhanSignal is development software, not investment advice. Signals are experimental rules, not validated profitable strategies. Demo prices are synthetic and are never live market quotes. No broker order-placement endpoint is implemented in this phase.

## Stack

- Frontend: React, TypeScript, Vite, TradingView Lightweight Charts
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2, Pydantic
- Database: PostgreSQL 16
- Market data: deterministic demo provider by default; optional Zerodha Kite Connect adapter
- Indicators: pandas, NumPy

## Run locally

### Prerequisites

- Docker + Docker Compose
- Node.js 20+ (optional when using Docker)
- Python 3.12+ (optional when using Docker)

### 1. Configure environment

```bash
cp .env.example .env
```

Keep `MARKET_DATA_PROVIDER=demo` for local development. To enable Kite market data, configure `KITE_API_KEY` and a valid `KITE_ACCESS_TOKEN` in `.env`, then set `MARKET_DATA_PROVIDER=zerodha`. Never commit credentials or expose them to the browser.

### 2. Start services

```bash
docker compose up --build
```

- Dashboard: http://localhost:5173
- API documentation: http://localhost:8000/docs
- Health: http://localhost:8000/health
- PostgreSQL: localhost:5432

### 3. Stop services

```bash
docker compose down
```

To also remove the local database volume (destructive):

```bash
docker compose down -v
```

## API endpoints

- `GET /health`
- `GET /api/v1/market/overview`
- `GET /api/v1/market/watchlist`
- `GET /api/v1/market/quotes?symbols=RELIANCE,HDFCBANK,INFY`
- `GET /api/v1/market/history/{symbol}?interval=day&days=180`
- `GET /api/v1/signals?symbols=RELIANCE,HDFCBANK,INFY`
- `GET /api/v1/paper/account`

## Experimental technical signal engine

Strategy version `technical-0.2` evaluates five explainable checks:

| Check | Weight | Rule |
|---|---:|---|
| Trend | 3 | Close > EMA 50 > EMA 200 |
| Momentum | 2 | RSI(14) between 50 and 70 |
| Volume | 2 | Volume above its 20-session average |
| MACD | 2 | MACD above its signal line |
| Volatility | 1 | ATR(14) no more than 5% of price |

The score is the sum of passed check weights, from 0 to 10. A BUY candidate requires trend, momentum, volume and MACD confirmation, with a score of at least 8. AVOID is used when price is below both EMA 50 and EMA 200; other cases are WAIT. ATR(14) provides illustrative stop and target levels at 1.5x and 3x ATR respectively.

The API includes a `checks` breakdown and human-readable rationale. This scoring is a screening heuristic, not a probability or expected return. It has not been validated through backtesting. It needs walk-forward and out-of-sample testing with realistic transaction costs and slippage before it can inform real-money decisions.

## Project layout

```text
DhanSignal/
├── backend/
│   ├── app/
│   │   ├── api/              # HTTP routes
│   │   ├── core/             # Settings
│   │   ├── db/               # SQLAlchemy models/session
│   │   ├── market_data/      # Provider interface, demo and Kite adapters
│   │   ├── schemas/          # API response models
│   │   ├── services/         # Market data orchestration
│   │   └── strategies/       # Indicators and signal rules
│   └── tests/
├── frontend/src/
├── docker-compose.yml
└── .env.example
```

## Current limitations and next steps

- Kite login callback/token generation and WebSocket streaming are not implemented yet; the current adapter uses the configured access token for its supported REST endpoints.
- Market-data access and entitlements depend on the broker account, current plan and applicable terms.
- Demo mode is synthetic, is not connected to NSE/BSE, and must not be interpreted as a live quote.
- Portfolio import, PDF research, realistic paper-order execution, transaction charges and the mobile app are subsequent milestones.
- Before broker order execution, review current SEBI, exchange and broker requirements; add explicit approval, risk limits, audit logs and kill switches.
