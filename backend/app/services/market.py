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
        quote = next((item for item in market.get_quotes([symbol]) if item.get("symbol") == symbol), None)
        if quote and not history.empty:
            index = history.index[-1]
            history.loc[index, "close"] = float(quote.get("last_price") or history.loc[index, "close"])
            history.loc[index, "high"] = max(float(history.loc[index, "high"]), float(quote.get("high") or quote.get("last_price") or 0))
            history.loc[index, "low"] = min(float(history.loc[index, "low"]), float(quote.get("low") or quote.get("last_price") or history.loc[index, "low"]))
            history.loc[index, "volume"] = float(quote.get("volume") or history.loc[index, "volume"])
        signal = generate_signal(symbol, history)
        if quote:
            signal["price"] = round(float(quote["last_price"]), 2)
            signal["market_data_timestamp"] = quote.get("timestamp")
        signals.append(signal)
    return signals
