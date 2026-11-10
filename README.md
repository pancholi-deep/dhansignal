# TradeLens v0.1 — Phase 1

A personal Indian-equity research and paper-trading starter platform. Phase 1 includes a React dashboard, FastAPI backend, PostgreSQL persistence, a demo market-data provider, an optional Zerodha Kite Connect adapter, and a deterministic technical-signal engine.

> **Important:** This is development software, not investment advice. Signals are rule-based examples, not validated profitable strategies. Demo prices are synthetic. Live quotes require an appropriately licensed/authorized data source and valid Zerodha credentials. No order-placement endpoint is implemented in this phase.

## Stack

- Frontend: React, TypeScript, Vite, lightweight custom UI
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2, Pydantic
- Database: PostgreSQL 16
- Market data: Demo provider by default; optional Kite Connect quote/history adapter
- Indicators: pandas, NumPy

## Run locally

### Prerequisites

- Docker + Docker Compose
- Node.js 20+
- Python 3.12+ (optional if running backend through Docker)

### 1. Configure environment

```bash
cp .env.example .env
```

Leave `MARKET_DATA_PROVIDER=demo` initially. To enable Kite market data, configure `KITE_API_KEY` and a valid `KITE_ACCESS_TOKEN` in `.env` and set `MARKET_DATA_PROVIDER=zerodha`.

Kite access tokens expire and must be obtained through the supported Kite login flow. Do not commit credentials or expose them to the browser.

### 2. Start services

```bash
docker compose up --build
```

- Dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- PostgreSQL: localhost:5432

### 3. Stop

```bash
docker compose down
```

To remove the local database volume too (destructive):

```bash
docker compose down -v
```

## Useful API endpoints

- `GET /health`
- `GET /api/v1/market/overview`
- `GET /api/v1/market/watchlist`
- `GET /api/v1/market/quotes?symbols=RELIANCE,HDFCBANK,INFY`
- `GET /api/v1/market/history/{symbol}?interval=day&days=180`
- `GET /api/v1/signals?symbols=RELIANCE,HDFCBANK,INFY`
- `GET /api/v1/paper/account`

The current demo provider supplies deterministic synthetic candles and quotes. The Zerodha adapter expects NSE instrument symbols and a valid Kite access token; it is deliberately isolated behind `MarketDataProvider`.

## Signal logic (initial baseline)

A long setup is considered only when:

1. Last close is above EMA 50 and EMA 200.
2. EMA 50 is above EMA 200.
3. RSI(14) is between 50 and 70.
4. Latest volume is above the 20-session average.

A `WAIT` or `EXIT` result is returned otherwise. ATR(14) is used for an illustrative volatility-based stop and target. This is a starting hypothesis only; it needs walk-forward backtesting, realistic costs, slippage and out-of-sample validation before any live use.

## Project layout

```text
TradeLens/
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

## Current limitations / next steps

- Kite login callback/token generation is not implemented; use a valid access token for local development.
- Kite historical API access and market-data entitlements depend on the broker account and current plan.
- Demo mode is not connected to NSE/BSE and must not be used to infer real prices.
- Portfolio holdings import, PDF research, paper order execution, transaction charges and mobile app are subsequent milestones.
- Before broker order execution, review current SEBI/exchange/broker requirements and add explicit approval, risk limits, audit logs and kill switches.
