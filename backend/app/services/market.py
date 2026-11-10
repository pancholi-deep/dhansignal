from app.market_data.factory import get_market_data_provider
from app.market_data.demo import DEFAULT_SYMBOLS
from app.strategies.technical import generate_signal


def provider():
    return get_market_data_provider()


def get_watchlist():
    return DEFAULT_SYMBOLS


def get_signals(symbols: list[str]):
    market = provider()
    signals = []
    for symbol in symbols:
        history = market.get_history(symbol, interval="day", days=240)
        signals.append(generate_signal(symbol, history))
    return signals
