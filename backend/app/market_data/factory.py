from app.core.config import settings
from app.market_data.demo import DemoMarketDataProvider
from app.market_data.zerodha import ZerodhaMarketDataProvider


def get_market_data_provider():
    if settings.market_data_provider.lower() == "zerodha":
        return ZerodhaMarketDataProvider(settings.kite_api_key, settings.kite_access_token)
    return DemoMarketDataProvider()
