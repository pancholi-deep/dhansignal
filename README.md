# DhanSignal v0.1 — Phase 1

An Indian-equity market intelligence and paper-trading platform. Phase 1 provides a React + TypeScript dashboard, FastAPI backend, PostgreSQL persistence, a clearly labelled synthetic demo market-data provider, an optional Zerodha Kite Connect adapter, and a deterministic technical-signal engine.

> **Disclaimer:** DhanSignal is development software, not investment advice. Signals are experimental rules, not validated profitable strategies. Demo prices are synthetic and are never live market quotes. No broker order-placement endpoint is implemented in this phase.

## Stack

- Frontend: React, TypeScript, Vite
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

## Initial signal logic

A long setup is considered only when the latest close is above EMA 50 and EMA 200, EMA 50 is above EMA 200, RSI(14) is between 50 and 70, and volume exceeds its 20-session average. ATR(14) is used for illustrative volatility-based stop and target levels. This is a starting hypothesis only; it needs walk-forward backtesting, realistic transaction costs, slippage and out-of-sample validation before any real-money use.

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
