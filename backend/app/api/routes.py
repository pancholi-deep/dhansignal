import json
from datetime import timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import PaperAccount, PaperPosition, PaperTrade, WatchlistItem
from app.core.config import settings
from app.market_data.factory import get_market_data_provider
from app.market_data.demo import DEFAULT_SYMBOLS
from app.services.market import get_signals
from app.strategies.technical import add_indicators

router = APIRouter()
PAPER_FEE_RATE = 0.001  # 0.10% simulated fee per side


class PaperOrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9&_-]+$")
    side: str = Field(pattern=r"^(BUY|SELL)$")
    quantity: int = Field(gt=0, le=10000)


def get_or_create_paper_account(db: Session) -> PaperAccount:
    account = db.query(PaperAccount).order_by(PaperAccount.id).with_for_update().first()
    if account is None:
        account = PaperAccount(name="Default paper account", starting_cash=settings.paper_starting_cash, cash_balance=settings.paper_starting_cash)
        db.add(account)
        db.flush()
    return account


def paper_snapshot(db: Session, account: PaperAccount):
    market = get_market_data_provider()
    positions = db.query(PaperPosition).filter(PaperPosition.account_id == account.id, PaperPosition.quantity > 0).order_by(PaperPosition.symbol).all()
    quotes = {q["symbol"]: q for q in market.get_quotes([p.symbol for p in positions])} if positions else {}
    position_rows = []
    invested_value = unrealized_pnl = 0.0
    for position in positions:
        quote = quotes.get(position.symbol, {})
        ltp = float(quote.get("last_price") or position.average_price)
        market_value = ltp * position.quantity
        cost_value = position.average_price * position.quantity
        pnl = market_value - cost_value
        invested_value += market_value
        unrealized_pnl += pnl
        position_rows.append({
            "symbol": position.symbol, "quantity": position.quantity,
            "average_price": round(position.average_price, 2), "last_price": round(ltp, 2),
            "market_value": round(market_value, 2), "unrealized_pnl": round(pnl, 2),
            "realized_pnl": round(position.realized_pnl, 2),
        })
    realized_pnl = sum(p.realized_pnl for p in db.query(PaperPosition).filter(PaperPosition.account_id == account.id).all())
    return {
        "id": account.id, "currency": "INR", "starting_cash": round(account.starting_cash, 2),
        "cash_balance": round(account.cash_balance, 2), "invested_value": round(invested_value, 2),
        "total_value": round(account.cash_balance + invested_value, 2),
        "realized_pnl": round(realized_pnl, 2), "unrealized_pnl": round(unrealized_pnl, 2),
        "positions": position_rows, "mode": "PAPER", "provider": market.name,
    }


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
def history(symbol: str, interval: str = "day", days: int = Query(365, ge=30, le=2000)):
    if interval not in {"minute", "5minute", "15minute", "30minute", "60minute", "day"}:
        raise HTTPException(status_code=400, detail="Unsupported candle interval")
    market = get_market_data_provider()
    frame = market.get_history(symbol.upper(), interval=interval, days=days)
    if frame.empty:
        raise HTTPException(status_code=404, detail="No historical data found")
    frame = add_indicators(frame)
    frame["date"] = frame["date"].map(lambda value: value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value)[:10])
    candles = json.loads(frame.to_json(orient="records"))
    return {"symbol": symbol.upper(), "provider": market.name, "is_live": market.is_live, "candles": candles}


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
        account = get_or_create_paper_account(db)
        db.commit()
        return paper_snapshot(db, account)
    finally:
        db.close()


@router.post("/paper/orders")
def place_paper_order(order: PaperOrderRequest):
    symbol, side = order.symbol.upper(), order.side.upper()
    db: Session = SessionLocal()
    try:
        account = get_or_create_paper_account(db)
        market = get_market_data_provider()
        quote_rows = market.get_quotes([symbol])
        quote = next((q for q in quote_rows if q.get("symbol") == symbol), None)
        if not quote or not quote.get("last_price") or float(quote["last_price"]) <= 0:
            raise HTTPException(status_code=404, detail=f"No usable quote found for {symbol}")
        price = float(quote["last_price"])
        notional = price * order.quantity
        fees = round(notional * PAPER_FEE_RATE, 2)
        position = db.query(PaperPosition).filter_by(account_id=account.id, symbol=symbol).with_for_update().first()

        if side == "BUY":
            total_cost = notional + fees
            if total_cost > account.cash_balance:
                raise HTTPException(status_code=400, detail="Insufficient paper cash for this order, including simulated fees")
            if position is None:
                position = PaperPosition(account_id=account.id, symbol=symbol, quantity=0, average_price=0, realized_pnl=0)
                db.add(position)
                db.flush()
            new_quantity = position.quantity + order.quantity
            position.average_price = ((position.quantity * position.average_price) + notional) / new_quantity
            position.quantity = new_quantity
            account.cash_balance -= total_cost
            realized = 0.0
        else:
            if position is None or position.quantity < order.quantity:
                available = position.quantity if position else 0
                raise HTTPException(status_code=400, detail=f"Insufficient shares to sell. Available: {available}")
            proceeds = notional - fees
            realized = (price - position.average_price) * order.quantity - fees
            position.quantity -= order.quantity
            position.realized_pnl += realized
            account.cash_balance += proceeds
            if position.quantity == 0:
                position.average_price = 0.0

        trade = PaperTrade(account_id=account.id, symbol=symbol, side=side, quantity=order.quantity, price=price, fees=fees, realized_pnl=realized)
        db.add(trade)
        db.commit()
        db.refresh(trade)
        return {
            "message": f"Paper {side.lower()} order filled",
            "trade": {"id": trade.id, "symbol": symbol, "side": side, "quantity": order.quantity,
                      "price": round(price, 2), "fees": fees, "realized_pnl": round(realized, 2),
                      "created_at": trade.created_at.isoformat() if trade.created_at else None},
            "account": paper_snapshot(db, account),
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/paper/trades")
def paper_trades(limit: int = Query(50, ge=1, le=200)):
    db: Session = SessionLocal()
    try:
        account = get_or_create_paper_account(db)
        db.commit()
        trades = db.query(PaperTrade).filter(PaperTrade.account_id == account.id).order_by(PaperTrade.id.desc()).limit(limit).all()
        return {"trades": [{
            "id": t.id, "symbol": t.symbol, "side": t.side, "quantity": t.quantity,
            "price": round(t.price, 2), "fees": round(t.fees, 2),
            "realized_pnl": round(t.realized_pnl, 2),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in trades]}
    finally:
        db.close()
