from app.market_data.factory import provider


class MarketService:
    async def overview(self):
        return await provider.overview()

    async def watchlist(self):
        return await provider.watchlist()

    async def quotes(self, symbols: list[str]):
        return [await provider.quote(symbol) for symbol in symbols]

    async def history(self, symbol: str, interval: str = "day", days: int = 180):
        return await provider.history(symbol, interval, days)


market_service = MarketService()
