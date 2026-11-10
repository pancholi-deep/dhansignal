import pandas as pd
from app.strategies.technical import add_indicators, generate_signal


def sample_frame(n=240):
    dates = pd.bdate_range("2025-01-01", periods=n)
    close = [100 + i * 0.8 for i in range(n)]
    return pd.DataFrame({
        "date": dates, "open": close,
        "high": [x + 1 for x in close],
        "low": [x - 1 for x in close],
        "close": close, "volume": [2_000_000] * n,
    })


def test_indicators_are_calculated():
    result = add_indicators(sample_frame())
    assert result.ema_50.notna().all()
    assert result.ema_200.notna().all()
    assert result.atr_14.notna().all()
    assert result.macd.notna().all()
    assert result.atr_pct.notna().all()


def test_signal_has_explainable_checks():
    signal = generate_signal("TEST", sample_frame())
    assert signal["action"] in {"BUY", "WAIT", "AVOID"}
    assert signal["symbol"] == "TEST"
    assert set(signal["checks"]) == {"trend", "momentum", "volume", "macd", "volatility"}
    assert len(signal["rationale"]) >= 5
    assert signal["strategy_version"] == "technical-0.2"


def test_empty_history_returns_wait_instead_of_crashing():
    signal = generate_signal("EMPTY", sample_frame(0))
    assert signal["action"] == "WAIT"
    assert signal["score"] == 0
    assert signal["price"] is None


def test_flat_prices_produce_neutral_rsi():
    frame = sample_frame()
    frame["close"] = 100.0
    result = add_indicators(frame)
    assert result.rsi_14.iloc[-1] == 50.0
