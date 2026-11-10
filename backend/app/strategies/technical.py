import pandas as pd

STRATEGY_VERSION = "baseline-0.1"


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy().sort_values("date").reset_index(drop=True)

    for column in ("open", "high", "low", "close", "volume"):
        df[column] = pd.to_numeric(df[column])

    # Trend indicators
    df["ema_20"] = df.close.ewm(span=20, adjust=False).mean()
    df["ema_50"] = df.close.ewm(span=50, adjust=False).mean()
    df["ema_200"] = df.close.ewm(span=200, adjust=False).mean()

    # RSI (14)
    delta = df.close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # ATR (14)
    previous_close = df.close.shift(1)
    true_range = pd.concat([
        df.high - df.low,
        (df.high - previous_close).abs(),
        (df.low - previous_close).abs(),
    ], axis=1).max(axis=1)
    df["atr_14"] = true_range.ewm(alpha=1 / 14, adjust=False).mean()
    df["volume_sma_20"] = df.volume.rolling(20).mean()

    # MACD (12, 26, 9)
    ema_12 = df.close.ewm(span=12, adjust=False).mean()
    ema_26 = df.close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df.macd.ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df.macd - df.macd_signal

    return df


def generate_signal(symbol: str, frame: pd.DataFrame) -> dict:
    df = add_indicators(frame)
    last = df.iloc[-1]
    price = float(last.close)
    ema50, ema200 = float(last.ema_50), float(last.ema_200)
    rsi = float(last.rsi_14) if pd.notna(last.rsi_14) else 50.0
    atr = float(last.atr_14) if pd.notna(last.atr_14) else price * 0.02
    vol_avg = float(last.volume_sma_20) if pd.notna(last.volume_sma_20) else 0
    volume_confirmed = float(last.volume) > vol_avg if vol_avg else False
    trend = price > ema50 > ema200
    momentum = 50 <= rsi <= 70
    score = sum([trend, momentum, volume_confirmed]) / 3 * 10

    if trend and momentum and volume_confirmed:
        action = "BUY"
        entry = price
        stop = price - 1.5 * atr
        target = price + 3.0 * atr
        rationale = ["Close is above EMA 50 and EMA 200", "EMA 50 is above EMA 200", "RSI is in the 50–70 momentum band", "Volume is above its 20-session average"]
    elif price < ema50 and price < ema200:
        action, entry, stop, target = "AVOID", None, None, None
        rationale = ["Price is below both EMA 50 and EMA 200"]
    else:
        action, entry, stop, target = "WAIT", None, None, None
        rationale = ["The complete baseline entry checklist is not satisfied"]

    return {
        "symbol": symbol, "action": action, "score": round(score, 1),
        "price": round(price, 2), "entry_price": round(entry, 2) if entry else None,
        "stop_loss": round(stop, 2) if stop else None,
        "target_price": round(target, 2) if target else None,
        "rsi_14": round(rsi, 2), "ema_50": round(ema50, 2), "ema_200": round(ema200, 2),
        "atr_14": round(atr, 2), "volume_confirmed": volume_confirmed,
        "holding_period": "1–5 trading days" if action == "BUY" else None,
        "rationale": rationale, "strategy_version": STRATEGY_VERSION,
        "as_of": pd.Timestamp(last.date).isoformat(),
    }
