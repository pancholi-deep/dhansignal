from app.market_data.factory import get_market_data_provider
from app.market_data.demo import DEFAULT_SYMBOLS
from app.strategies.technical import generate_signal
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import time
from threading import Lock


def provider():
    return get_market_data_provider()


def get_watchlist():
    return DEFAULT_SYMBOLS


_HISTORY_CACHE: dict[str, tuple[float, pd.DataFrame]] = {}
_HISTORY_CACHE_LOCK = Lock()
HISTORY_CACHE_SECONDS = 300


def cached_daily_history(market, symbol: str) -> pd.DataFrame:
    now = time.monotonic()
    with _HISTORY_CACHE_LOCK:
        cached = _HISTORY_CACHE.get(symbol)
        if cached and now - cached[0] < HISTORY_CACHE_SECONDS:
            return cached[1].copy()
    frame = market.get_history(symbol, interval="day", days=240)
    with _HISTORY_CACHE_LOCK:
        _HISTORY_CACHE[symbol] = (now, frame.copy())
    return frame


def get_signals(symbols: list[str]):
    market = provider()
    signals = []
    quotes = {item.get("symbol"): item for item in market.get_quotes(symbols)}
    for symbol in symbols:
        history = cached_daily_history(market, symbol)
        quote = quotes.get(symbol)
        if quote and not history.empty:
            today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
            last_date = pd.Timestamp(history.iloc[-1]["date"]).date()
            live_row = {
                "date": pd.Timestamp.now(tz="Asia/Kolkata"),
                "open": float(quote.get("open") or quote.get("last_price") or history.iloc[-1]["open"]),
                "high": float(quote.get("high") or quote.get("last_price") or history.iloc[-1]["high"]),
                "low": float(quote.get("low") or quote.get("last_price") or history.iloc[-1]["low"]),
                "close": float(quote.get("last_price") or history.iloc[-1]["close"]),
                "volume": float(quote.get("volume") or history.iloc[-1]["volume"]),
            }
            if last_date < today:
                history = pd.concat([history, pd.DataFrame([live_row])], ignore_index=True)
            else:
                index = history.index[-1]
                history.loc[index, "close"] = live_row["close"]
                history.loc[index, "high"] = max(float(history.loc[index, "high"]), live_row["high"])
                history.loc[index, "low"] = min(float(history.loc[index, "low"]), live_row["low"])
                history.loc[index, "volume"] = live_row["volume"]
        signal = generate_signal(symbol, history)
        if quote:
            signal["price"] = round(float(quote["last_price"]), 2)
            signal["market_data_timestamp"] = quote.get("timestamp")
        signals.append(signal)
    return signals
