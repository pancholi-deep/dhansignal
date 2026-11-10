import pandas as pd
import yfinance as yf

from app.market_data.base import MarketDataProvider


class YahooFinanceProvider(MarketDataProvider):
    """Unofficial Yahoo Finance adapter for historical NSE/BSE data."""

    name = "YAHOO FINANCE (HISTORICAL)"
    is_live = False

    @staticmethod
    def _ticker(symbol: str) -> str:
        return symbol if symbol.startswith("^") else f"{symbol}.NS"

    def get_history(self, symbol: str, interval: str = "day", days: int = 180) -> pd.DataFrame:
        intervals = {"day": "1d", "minute": "1m", "5minute": "5m", "15minute": "15m", "60minute": "60m", "hour": "60m"}
        yf_interval = intervals.get(interval, interval)
        period = f"{max(1, min(days, 3650))}d" if yf_interval == "1d" else ("7d" if yf_interval == "1m" else "60d")
        frame = yf.Ticker(self._ticker(symbol)).history(period=period, interval=yf_interval, auto_adjust=False, actions=False)
        if frame is None or frame.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        frame = frame.reset_index()
        date_column = "Datetime" if "Datetime" in frame.columns else "Date"
        frame = frame.rename(columns={date_column: "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        return frame[["date", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])

    def get_quotes(self, symbols: list[str]) -> list[dict]:
        result = []
        for symbol in symbols:
            try:
                history = self.get_history(symbol, "day", 5)
                if history.empty:
                    continue
                last = history.iloc[-1]
                previous = history.iloc[-2] if len(history) > 1 else last
                price, previous_close = float(last["close"]), float(previous["close"])
                change = price - previous_close
                result.append({
                    "symbol": symbol, "exchange": "NSE", "last_price": price,
                    "change": change, "change_percent": change / previous_close * 100 if previous_close else 0,
                    "volume": int(last["volume"] or 0), "timestamp": pd.Timestamp(last["date"]).isoformat(),
                    "open": float(last["open"]), "high": float(last["high"]), "low": float(last["low"]),
                    "close": previous_close, "source": "yahoo_finance",
                })
            except Exception:
                continue
        return result

    def get_indices(self) -> list[dict]:
        result = []
        for symbol, ticker in (("NIFTY 50", "^NSEI"), ("SENSEX", "^BSESN")):
            try:
                history = yf.Ticker(ticker).history(period="5d", interval="1d")
                if history.empty:
                    continue
                last = float(history["Close"].iloc[-1])
                previous = float(history["Close"].iloc[-2]) if len(history) > 1 else last
                result.append({"symbol": symbol, "last_price": last, "change_percent": (last - previous) / previous * 100 if previous else 0})
            except Exception:
                continue
        return result
