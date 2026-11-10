import pandas as pd
from kiteconnect import KiteConnect
from app.market_data.base import MarketDataProvider


class ZerodhaMarketDataProvider(MarketDataProvider):
    """Kite Connect adapter. Requires a valid access token and instrument tokens."""
    name = "ZERODHA KITE CONNECT"
    is_live = True

    def __init__(self, api_key: str, access_token: str):
        if not api_key:
            raise RuntimeError("KITE_API_KEY is required for Zerodha mode")
        self.client = KiteConnect(api_key=api_key)
        self.is_live = bool(access_token)
        if access_token:
            self.client.set_access_token(access_token)
        self._instrument_tokens: dict[str, int] = {}
        self._instrument_master_loaded = False

    def _load_instrument_master(self):
        if self._instrument_master_loaded:
            return
        instruments = self.client.instruments("NSE")
        self._instrument_tokens = {
            row["tradingsymbol"]: int(row["instrument_token"])
            for row in instruments if row.get("segment") == "NSE"
        }
        self._instrument_master_loaded = True

    def _token(self, symbol: str) -> int:
        self._load_instrument_master()
        token = self._instrument_tokens.get(symbol)
        if token is None:
            raise ValueError(f"NSE instrument not found: {symbol}")
        return token

    def get_quotes(self, symbols: list[str]) -> list[dict]:
        if not self.is_live:
            return []
        from datetime import datetime, timezone
        from app.services.stream import market_stream

        cached = {item["symbol"]: item for item in market_stream.snapshot(symbols)}
        fresh = {}
        for symbol, item in cached.items():
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(item["timestamp"])).total_seconds()
                if age <= 30:
                    fresh[symbol] = item
            except (KeyError, TypeError, ValueError):
                continue

        missing = [symbol for symbol in symbols if symbol not in fresh]
        raw = self.client.quote([f"NSE:{symbol}" for symbol in missing]) if missing else {}
        result = []
        for symbol in symbols:
            if symbol in fresh:
                result.append(fresh[symbol])
                continue
            quote = raw.get(f"NSE:{symbol}")
            if not quote:
                continue
            ohlc = quote.get("ohlc", {})
            last = float(quote.get("last_price", 0))
            close = float(ohlc.get("close", last))
            change = last - close
            timestamp = quote.get("timestamp")
            result.append({
                "symbol": symbol, "exchange": "NSE", "last_price": last,
                "change": change, "change_percent": (change / close * 100) if close else 0,
                "volume": int(quote.get("volume", 0)),
                "timestamp": timestamp.isoformat() if timestamp else None,
                "open": float(ohlc.get("open", 0)), "high": float(ohlc.get("high", 0)),
                "low": float(ohlc.get("low", 0)), "close": close,
                "source": "zerodha_quote_snapshot",
            })
        return result

    def get_history(self, symbol: str, interval: str = "day", days: int = 180) -> pd.DataFrame:
        if not self.is_live:
            return pd.DataFrame()
        from datetime import datetime, timedelta
        token = self._token(symbol)
        end = datetime.now()
        start = end - timedelta(days=days)
        rows = self.client.historical_data(token, start, end, interval)
        return pd.DataFrame(rows).rename(columns={"date": "date"})

    def get_indices(self) -> list[dict]:
        if not self.is_live:
            return []
        raw = self.client.quote(["NSE:NIFTY 50", "BSE:SENSEX"])
        result = []
        for key, quote in raw.items():
            symbol = key.split(":", 1)[1]
            result.append({"symbol": symbol, "last_price": quote.get("last_price", 0), "change_percent": quote.get("net_change", 0)})
        return result
