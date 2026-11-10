import httpx
from app.core.config import settings


class ZerodhaMarketDataProvider:
    """REST quote/history adapter; access token must be supplied by the supported Kite login flow."""

    base_url = "https://api.kite.trade"

    def _headers(self):
        if not settings.kite_api_key or not settings.kite_access_token:
            raise RuntimeError("Configure KITE_API_KEY and KITE_ACCESS_TOKEN")
        return {"X-Kite-Version": "3", "Authorization": f"token {settings.kite_api_key}:{settings.kite_access_token}"}

    async def quote(self, symbol: str):
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.base_url}/quote", params={"i": f"NSE:{symbol}"}, headers=self._headers())
            response.raise_for_status()
            data = response.json()["data"][f"NSE:{symbol}"]
            return {"symbol": symbol, "last_price": data["last_price"], "volume": data.get("volume", 0),
                    "change_percent": data.get("net_change", 0), "provider": "zerodha", "is_live": True}

    async def history(self, instrument_token: str, interval: str, days: int):
        from datetime import datetime, timedelta
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/instruments/historical/{instrument_token}/{interval}",
                params={"from": from_date.strftime("%Y-%m-%d"), "to": to_date.strftime("%Y-%m-%d")},
                headers=self._headers())
            response.raise_for_status()
            return response.json()["data"]["candles"]

    async def overview(self):
        return {"provider": "zerodha", "is_live": True, "market": "NSE"}

    async def watchlist(self):
        return [await self.quote(symbol) for symbol in ("RELIANCE", "HDFCBANK", "INFY")]
