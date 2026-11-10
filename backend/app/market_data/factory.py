from functools import lru_cache
from app.core.config import settings
from app.market_data.demo import DemoMarketDataProvider
from app.market_data.zerodha import ZerodhaMarketDataProvider
from app.market_data.tapetide_yahoo import TapetideYahooProvider


@lru_cache(maxsize=4)
def _build_provider(provider_name: str, api_key: str, access_token: str, tapetide_token: str):
    if provider_name == "zerodha":
        return ZerodhaMarketDataProvider(api_key, access_token)
    if provider_name in {"tapetide_yahoo", "yahoo_tapetide", "hybrid"}:
        return TapetideYahooProvider(tapetide_token)
    if provider_name == "yahoo":
        from app.market_data.yahoo import YahooFinanceProvider
        return YahooFinanceProvider()
    return DemoMarketDataProvider()


def get_market_data_provider():
    return _build_provider(
        settings.market_data_provider.lower(),
        settings.kite_api_key,
        settings.kite_access_token,
        settings.tapetide_token,
    )
