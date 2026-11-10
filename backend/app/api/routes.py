from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import PaperAccount, WatchlistItem
from app.core.config import settings
from app.market_data.factory import get_market_data_provider
from app.market_data.demo import DEFAULT_SYMBOLS
from app.services.market import get_signals

router = APIRouter()


@router.get("/market/overview")
def market_overview():
    market = get_market_data_provider()
    return {"provider": market.name, "is_live": market.is_live, "indices": market.get_indices()}


@router.get("/market/watchlist")
def watchlist():
    market = get_market_data_provider()
    db: Session = SessionLocal()
    try:
        symbols = [row.symbol for row in db.query(WatchlistItem).order_by(WatchlistItem.id).all()] or DEFAULT_SYMBOLS
    finally:
        db.close()
    return {"symbols": symbols, "quotes": market.get_quotes(symbols), "provider": market.name, "is_live": market.is_live}


@router.get("/market/quotes")
def quotes(symbols: str = Query(..., description="Comma-separated NSE symbols")):
    requested = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
    if not requested or len(requested) > 50:
        raise HTTPException(status_code=400, detail="Provide between 1 and 50 symbols")
    market = get_market_data_provider()
    return {"quotes": market.get_quotes(requested), "provider": market.name, "is_live": market.is_live}


@router.get("/market/history/{symbol}")
def history(symbol: str, interval: str = "day", days: int = Query(180, ge=30, le=2000)):
    if interval not in {"minute", "5minute", "15minute", "30minute", "60minute", "day"}:
        raise HTTPException(status_code=400, detail="Unsupported candle interval")
    market = get_market_data_provider()
    frame = market.get_history(symbol.upper(), interval=interval, days=days)
    return {"symbol": symbol.upper(), "provider": market.name, "is_live": market.is_live, "candles": frame.assign(date=frame.date.astype(str)).to_dict(orient="records")}


@router.get("/signals")
def signals(symbols: str = ",".join(DEFAULT_SYMBOLS)):
    requested = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
    if not requested or len(requested) > 30:
        raise HTTPException(status_code=400, detail="Provide between 1 and 30 symbols")
    return {"signals": get_signals(requested), "provider": get_market_data_provider().name}


@router.get("/paper/account")
def paper_account():
    db: Session = SessionLocal()
    try:
        account = db.query(PaperAccount).order_by(PaperAccount.id).first()
        if account is None:
            account = PaperAccount(name="Default paper account", starting_cash=settings.paper_starting_cash, cash_balance=settings.paper_starting_cash)
            db.add(account)
            db.commit()
            db.refresh(account)
        return {"id": account.id, "currency": "INR", "starting_cash": account.starting_cash, "cash_balance": account.cash_balance, "invested_value": 0, "realized_pnl": 0, "unrealized_pnl": 0, "positions": [], "mode": "PAPER"}
    finally:
        db.close()
