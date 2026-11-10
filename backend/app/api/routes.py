from fastapi import APIRouter, HTTPException, Query

from app.services.market import market_service
from app.strategies.technical import build_signal

router = APIRouter()


@router.get("/market/overview")
async def market_overview():
    return await market_service.overview()


@router.get("/market/watchlist")
async def market_watchlist():
    return await market_service.watchlist()


@router.get("/market/quotes")
async def market_quotes(symbols: str = Query("RELIANCE,HDFCBANK,INFY")):
    return await market_service.quotes([s.strip().upper() for s in symbols.split(",") if s.strip()])


@router.get("/market/history/{symbol}")
async def market_history(symbol: str, interval: str = "day", days: int = 180):
    try:
        return await market_service.history(symbol.upper(), interval, days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/signals")
async def signals(symbols: str = Query("RELIANCE,HDFCBANK,INFY")):
    output = []
    for symbol in [s.strip().upper() for s in symbols.split(",") if s.strip()]:
        candles = await market_service.history(symbol, "day", 260)
        output.append(build_signal(symbol, candles))
    return output


@router.get("/paper/account")
async def paper_account():
    return {"starting_cash": 100000, "cash": 100000, "positions": [], "realized_pnl": 0, "unrealized_pnl": 0}
