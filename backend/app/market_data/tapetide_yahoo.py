import logging
import os
import time
from threading import Lock

import pandas as pd
import requests

from app.market_data.base import MarketDataProvider
from app.market_data.yahoo import YahooFinanceProvider

logger = logging.getLogger(__name__)


class TapetideYahooProvider(MarketDataProvider):
    """Tapetide REST quotes with Yahoo historical OHLC and quote fallback."""

    name = "TAPETIDE + YAHOO FINANCE"
    is_live = False  # REST snapshots; this adapter does not maintain a stream.
    BASE_URL = "https://api.tapetide.com/v1"
    CACHE_SECONDS = 600  # Protect the Tapetide 50-successful-calls/day free quota.

    def __init__(self, token: str = ""):
        self.token = token or os.getenv("TAPETIDE_TOKEN", "")
        self.yahoo = YahooFinanceProvider()
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        self._quotes_cache: dict[tuple[str, ...], tuple[float, list[dict]]] = {}
        self._cache_lock = Lock()

    def get_history(self, symbol: str, interval: str = "day", days: int = 180) -> pd.DataFrame:
        return self.yahoo.get_history(symbol, interval, days)

    def _tapetide_quotes(self, symbols: list[str]) -> list[dict]:
        if not self.token or not symbols:
            return []
        response = self.session.get(f"{self.BASE_URL}/quotes/live", params={"symbols": ",".join(symbols[:50])}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])
        if isinstance(data, dict):
            data = data.get("quotes", data.get("items", data))
        if isinstance(data, dict):
            data = [dict(value, symbol=key) for key, value in data.items() if isinstance(value, dict)]
        quotes = []
        for item in data if isinstance(data, list) else []:
            symbol = str(item.get("symbol") or item.get("tradingsymbol") or "").upper()
            price = item.get("ltp", item.get("price", item.get("last_price")))
            if not symbol or item.get("found", True) is False or price is None:
                continue
            quotes.append({
                "symbol": symbol, "exchange": str(item.get("exchange") or "NSE"),
                "last_price": float(price), "change": float(item.get("change") or 0),
                "change_percent": float(item.get("change_pct", item.get("change_percent", 0)) or 0),
                "volume": int(item.get("volume") or 0),
                "timestamp": item.get("last_trade_at") or (payload.get("meta") or {}).get("as_of"),
                "open": float(item.get("open") or 0), "high": float(item.get("high") or 0),
                "low": float(item.get("low") or 0),
                "close": float(item.get("prev_close") or item.get("previous_close") or item.get("close") or 0),
                "source": "tapetide_rest",
            })
        return quotes

    def get_quotes(self, symbols: list[str]) -> list[dict]:
        key = tuple(sorted(set(symbols)))
        now = time.monotonic()
        with self._cache_lock:
            cached = self._quotes_cache.get(key)
            if cached and now - cached[0] < self.CACHE_SECONDS:
                return [dict(item) for item in cached[1]]
        quotes = []
        try:
            quotes = self._tapetide_quotes(symbols)
        except (requests.RequestException, ValueError, KeyError, TypeError):
            logger.exception("Tapetide quote request failed; falling back to Yahoo Finance")
        by_symbol = {item["symbol"]: item for item in quotes}
        missing = [symbol for symbol in symbols if symbol not in by_symbol]
        if missing:
            by_symbol.update({item["symbol"]: item for item in self.yahoo.get_quotes(missing)})
        result = [by_symbol[symbol] for symbol in symbols if symbol in by_symbol]
        with self._cache_lock:
            self._quotes_cache[key] = (now, [dict(item) for item in result])
        return result

    def get_indices(self) -> list[dict]:
        return self.yahoo.get_indices()
