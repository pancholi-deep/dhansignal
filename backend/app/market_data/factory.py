from functools import lru_cache
from app.core.config import settings
from app.market_data.demo import DemoMarketDataProvider
from app.market_data.zerodha import ZerodhaMarketDataProvider


@lru_cache(maxsize=4)
def _build_provider(provider_name: str, api_key: str, access_token: str):
    if provider_name == "zerodha":
        return ZerodhaMarketDataProvider(api_key, access_token)
    return DemoMarketDataProvider()


def get_market_data_provider():
    return _build_provider(
        settings.market_data_provider.lower(),
        settings.kite_api_key,
        settings.kite_access_token,
    )
