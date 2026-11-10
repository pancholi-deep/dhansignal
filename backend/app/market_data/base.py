from abc import ABC, abstractmethod
import pandas as pd


class MarketDataProvider(ABC):
    name: str
    is_live: bool = False

    @abstractmethod
    def get_quotes(self, symbols: list[str]) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_history(self, symbol: str, interval: str = "day", days: int = 180) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_indices(self) -> list[dict]:
        raise NotImplementedError
