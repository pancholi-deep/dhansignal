from datetime import date, timedelta
import math
import random


class DemoMarketDataProvider:
    """Deterministic synthetic market data. Never represents live exchange prices."""

    symbols = {"RELIANCE": 1280.0, "HDFCBANK": 1720.0, "INFY": 1840.0, "TCS": 3960.0}

    async def overview(self):
        return {"provider": "demo", "is_live": False, "market": "NSE", "nifty": None, "sensex": None,
                "message": "Synthetic demonstration data; live market values are not available."}

    async def watchlist(self):
        quotes = [await self.quote(symbol) for symbol in self.symbols]
        return quotes

    async def quote(self, symbol: str):
        if symbol not in self.symbols:
            raise ValueError(f"Unknown demo symbol: {symbol}")
        base = self.symbols[symbol]
        seed = sum(ord(c) for c in symbol)
        random.seed(seed)
        change = random.uniform(-0.018, 0.018)
        price = round(base * (1 + change), 2)
        return {"symbol": symbol, "last_price": price, "change_percent": round(change * 100, 2),
                "volume": random.randint(800000, 5000000), "provider": "demo", "is_live": False}

    async def history(self, symbol: str, interval: str, days: int):
        if symbol not in self.symbols:
            raise ValueError(f"Unknown demo symbol: {symbol}")
        seed = sum(ord(c) for c in symbol)
        rng = random.Random(seed)
        price = self.symbols[symbol] * 0.78
        rows = []
        for i in range(max(days, 30)):
            drift = 0.0007 + math.sin(i / 18) * 0.001
            move = drift + rng.gauss(0, 0.012)
            open_price = price
            close = max(1, price * (1 + move))
            high = max(open_price, close) * (1 + rng.random() * 0.008)
            low = min(open_price, close) * (1 - rng.random() * 0.008)
            rows.append({"date": (date.today() - timedelta(days=max(days,30)-i-1)).isoformat(),
                         "open": round(open_price,2), "high": round(high,2), "low": round(low,2),
                         "close": round(close,2), "volume": rng.randint(500000, 4500000)})
            price = close
        return rows
