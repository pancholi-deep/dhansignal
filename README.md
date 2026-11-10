# DhanSignal v0.1 — Phase 1

An Indian-equity market intelligence and paper-trading platform. Phase 1 provides a React + TypeScript dashboard, FastAPI backend, PostgreSQL persistence, a clearly labelled synthetic demo market-data provider, a Zerodha Kite Connect WebSocket market-data adapter, a real-time paper-trading simulator, and an experimental technical-signal engine.

> **Disclaimer:** DhanSignal is development software, not investment advice. Signals are experimental rules, not validated profitable strategies. Demo prices are synthetic and are never live market quotes. Paper orders are simulated locally and never submitted to a broker.

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

Keep `MARKET_DATA_PROVIDER=demo` for UI development; those prices are synthetic. For authorized live NSE market data, set `MARKET_DATA_PROVIDER=zerodha`, `KITE_API_KEY`, and a valid daily `KITE_ACCESS_TOKEN` in `.env`. Kite Connect's paid Connect plan is required for WebSocket live data and historical candles (currently ₹500/month per API key); the free Personal tier does not include market data. Never commit credentials or expose them to the browser. The access token expires daily and must be refreshed through the Kite login flow. Set the Kite app's redirect URL to `http://localhost:8000/api/v1/auth/zerodha/callback`; after restarting the backend, use **Connect Zerodha** in the dashboard. The generated access token is held in backend memory and is not written to source control or persisted across backend restarts.

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
- `GET /api/v1/auth/zerodha/status` and `GET /api/v1/auth/zerodha/login` — broker connection status and login redirect
- `GET /api/v1/auth/zerodha/callback` — Kite login callback
- `GET /api/v1/market/overview`
- `GET /api/v1/market/watchlist`
- `GET /api/v1/market/quotes?symbols=RELIANCE,HDFCBANK,INFY`
- `GET /api/v1/market/history/{symbol}?interval=day&days=180`
- `GET /api/v1/signals?symbols=RELIANCE,HDFCBANK,INFY`
- `GET /api/v1/paper/account`
- `GET /api/v1/paper/control` and `PUT /api/v1/paper/control` — persistent simulator pause/resume switch

## Experimental technical signal engine

Strategy version `technical-0.2` evaluates five explainable checks:

| Check | Weight | Rule |
|---|---:|---|
| Trend | 3 | Close > EMA 50 > EMA 200 |
| Momentum | 2 | RSI(14) between 50 and 70 |
| Volume | 2 | Volume above its 20-session average |
| MACD | 2 | MACD above its signal line |
| Volatility | 1 | ATR(14) no more than 5% of price |

The score is the sum of passed check weights, from 0 to 10. In Zerodha mode, the latest streamed/quoted LTP and day volume are overlaid on the latest daily candle before the rating is recalculated; the dashboard refreshes ratings every 15 seconds. A BUY candidate requires trend, momentum, volume and MACD confirmation, with a score of at least 8. AVOID is used when price is below both EMA 50 and EMA 200; other cases are WAIT. ATR(14) provides illustrative stop and target levels at 1.5x and 3x ATR respectively.

The API includes a `checks` breakdown and human-readable rationale. This scoring is a screening heuristic, not a probability or expected return. It has not been validated through backtesting. It needs walk-forward and out-of-sample testing with realistic transaction costs and slippage before it can inform real-money decisions.

## Paper trading simulator

The paper simulator supports immediate simulated BUY and SELL fills at the configured provider's latest quote. In Zerodha mode, fresh WebSocket ticks are used when available, falling back to a broker quote snapshot when the stream has no tick newer than 30 seconds. It tracks cash, weighted-average position cost, open positions, realized and unrealized P&L, and a persistent trade journal. A simplified 0.10% fee is applied on each side; this is not a full brokerage, STT, exchange, GST or stamp-duty model. SELL orders cannot exceed the current position, and BUY orders cannot exceed available cash. A persistent kill switch can pause new paper orders, and each order is capped at ₹25,000 by default. The simulator never sends orders to a broker. The paper ledger is stored in PostgreSQL and is not reset when containers restart.

API endpoints:

- `GET /api/v1/paper/account`
- `POST /api/v1/paper/orders` with `{ "symbol": "RELIANCE", "side": "BUY", "quantity": 1 }`
- `GET /api/v1/paper/trades?limit=50`


## Company research library — ingestion milestone

The research workspace accepts PDF sources in six categories: annual reports, management discussion and analysis, earnings-call transcripts, technical charts, financial screeners, and shareholding patterns. Uploads are associated with a company name and optional NSE symbol/reporting period. PDF text is extracted and stored alongside metadata; original PDFs are persisted in the `dhansignal_research` Docker volume. SHA-256 duplicate detection avoids storing the same PDF twice.

Research API endpoints:

- `POST /api/v1/research/documents` — multipart PDF upload with `file`, `document_type`, `company_name`, optional `title`, `symbol`, and `reporting_period`.
- `GET /api/v1/research/documents` — list documents, optionally filter by `document_type` or `symbol`.
- `GET /api/v1/research/documents/{id}` — retrieve metadata and extracted text.
- `GET /api/v1/research/search?q=...` — document-level keyword search with snippets.
- `GET /api/v1/research/retrieve?q=...` — ranked evidence passages with document metadata and 1-based PDF page citations.
- `POST /api/v1/research/documents/{id}/index` — build the page-aware index for a document uploaded before this milestone.

Current ingestion limits: PDF only, maximum 20 MB, text-based PDFs only. Scanned/image-only PDFs need OCR and are not processed in this milestone. Each uploaded PDF is split into overlapping text passages while preserving 1-based PDF page numbers. The first evidence retriever is a dependency-free lexical ranker; it is not semantic/vector retrieval and does not understand paraphrases. Previously uploaded PDFs can be indexed with the document index endpoint. No LLM-generated analysis is produced yet. The current app has no user authentication or per-user document isolation; run it only in a trusted local environment until access controls are implemented.

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

- Kite login callback/token generation is not implemented yet; refresh the daily access token manually. The WebSocket subscribes to the six starter watchlist symbols in full mode. Dynamic watchlist subscription and market-wide scanning are subsequent improvements.
- Market-data access and entitlements depend on the broker account, current plan and applicable terms.
- Demo mode is synthetic, is not connected to NSE/BSE, and must not be interpreted as a live quote.
- Semantic/vector retrieval and embeddings, OCR for scanned PDFs, AI-generated source-grounded research reports, portfolio import, realistic paper-order execution, complete transaction charges and the mobile app are subsequent milestones.
- Before broker order execution, review current SEBI, exchange and broker requirements; add explicit approval, risk limits, audit logs and kill switches.
