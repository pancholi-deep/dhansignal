from datetime import datetime, timedelta, time as day_time
import hashlib
import numpy as np
import pandas as pd
from app.market_data.base import MarketDataProvider


DEFAULT_SYMBOLS = ["RELIANCE", "HDFCBANK", "INFY", "ICICIBANK", "TCS", "LT"]


class DemoMarketDataProvider(MarketDataProvider):
    name = "DEMO DATA"
    is_live = False

    def _seed(self, symbol: str) -> int:
        return int(hashlib.sha256(symbol.encode()).hexdigest()[:8], 16)

    def get_history(self, symbol: str, interval: str = "day", days: int = 220) -> pd.DataFrame:
        rng = np.random.default_rng(self._seed(symbol) + (days * 17))
        base = 450 + (self._seed(symbol) % 2600)
        drift = 0.00035 + ((self._seed(symbol) % 7) - 3) * 0.00008

        if interval in {"minute", "5minute", "15minute"}:
            minutes = {"minute": 1, "5minute": 5, "15minute": 15}[interval]
            sessions = []
            end_date = pd.Timestamp.now(tz="Asia/Kolkata").date()
            start_date = end_date - timedelta(days=max(days, 1) - 1)
            for session_date in pd.date_range(start=start_date, end=end_date, freq="B"):
                day = session_date.date()
                start = pd.Timestamp(datetime.combine(day, day_time(9, 15)), tz="Asia/Kolkata")
                end = pd.Timestamp(datetime.combine(day, day_time(15, 30)), tz="Asia/Kolkata")
                sessions.extend(pd.date_range(start=start, end=end, freq=f"{minutes}min", inclusive="left"))
            dates = pd.DatetimeIndex(sessions)
            count = len(dates)
            if not count:
                return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
            returns = rng.normal(drift / 75, 0.0025 * np.sqrt(minutes / 5), count)
            close = base * np.exp(np.cumsum(returns))
            open_ = np.concatenate(([base], close[:-1]))
            high = np.maximum(open_, close) * (1 + rng.uniform(0.0002, 0.002, count))
            low = np.minimum(open_, close) * (1 - rng.uniform(0.0002, 0.002, count))
            volume = rng.integers(5_000, 80_000, count)
            return pd.DataFrame({"date": dates, "open": open_, "high": high, "low": low, "close": close, "volume": volume})

        count = max(days, 210)
        dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=count)
        returns = rng.normal(drift, 0.014, count)
        close = base * np.exp(np.cumsum(returns))
        open_ = close * (1 + rng.normal(0, 0.004, count))
        high = np.maximum(open_, close) * (1 + rng.uniform(0.001, 0.012, count))
        low = np.minimum(open_, close) * (1 - rng.uniform(0.001, 0.012, count))
        volume = rng.integers(300_000, 2_500_000, count)
        return pd.DataFrame({"date": dates, "open": open_, "high": high, "low": low, "close": close, "volume": volume})

    def get_quotes(self, symbols: list[str]) -> list[dict]:
        quotes = []
        for symbol in symbols:
            hist = self.get_history(symbol, days=220)
            last = hist.iloc[-1]
            prev = hist.iloc[-2]
            price = float(last.close)
            change = price - float(prev.close)
            quotes.append({
                "symbol": symbol,
                "exchange": "NSE",
                "last_price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change / float(prev.close) * 100, 2),
                "volume": int(last.volume),
                "timestamp": datetime.now().astimezone().isoformat(),
            })
        return quotes

    def get_indices(self) -> list[dict]:
        return [
            {"symbol": "NIFTY 50", "last_price": 24850.0, "change_percent": 0.72},
            {"symbol": "SENSEX", "last_price": 81420.0, "change_percent": 0.54},
        ]
