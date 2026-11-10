from app.core.config import settings
from app.market_data.demo import DemoMarketDataProvider
from app.market_data.zerodha import ZerodhaMarketDataProvider

provider = ZerodhaMarketDataProvider() if settings.market_data_provider.lower() == "zerodha" else DemoMarketDataProvider()
