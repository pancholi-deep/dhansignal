from abc import ABC, abstractmethod


class MarketDataProvider(ABC):
    @abstractmethod
    async def overview(self) -> dict: ...

    @abstractmethod
    async def watchlist(self) -> list[dict]: ...

    @abstractmethod
    async def quote(self, symbol: str) -> dict: ...

    @abstractmethod
    async def history(self, symbol: str, interval: str, days: int) -> list[dict]: ...
