import pandas as pd

STRATEGY_VERSION = "technical-0.2"


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    df = frame.copy().sort_values("date").reset_index(drop=True)
    for column in ("open", "high", "low", "close", "volume"):
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["ema_20"] = df.close.ewm(span=20, adjust=False).mean()
    df["ema_50"] = df.close.ewm(span=50, adjust=False).mean()
    df["ema_200"] = df.close.ewm(span=200, adjust=False).mean()

    delta = df.close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["rsi_14"] = 100 - (100 / (1 + rs))
    flat_market = (gain == 0) & (loss == 0)
    df.loc[flat_market, "rsi_14"] = 50
    df.loc[(loss == 0) & (gain > 0), "rsi_14"] = 100

    previous_close = df.close.shift(1)
    true_range = pd.concat([
        df.high - df.low,
        (df.high - previous_close).abs(),
        (df.low - previous_close).abs(),
    ], axis=1).max(axis=1)
    df["atr_14"] = true_range.ewm(alpha=1 / 14, adjust=False).mean()
    df["atr_pct"] = (df.atr_14 / df.close) * 100
    df["volume_sma_20"] = df.volume.rolling(20).mean()

    ema_12 = df.close.ewm(span=12, adjust=False).mean()
    ema_26 = df.close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df.macd.ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df.macd - df.macd_signal
    return df


def generate_signal(symbol: str, frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {
            "symbol": symbol, "action": "WAIT", "score": 0.0,
            "price": None, "entry_price": None, "stop_loss": None,
            "target_price": None, "rsi_14": None, "ema_50": None,
            "ema_200": None, "atr_14": None, "volume_confirmed": False,
            "holding_period": None, "rationale": ["No historical candles are available"],
            "checks": {}, "strategy_version": STRATEGY_VERSION, "as_of": None,
        }

    df = add_indicators(frame)
    last = df.iloc[-1]
    price = float(last.close)
    ema50, ema200 = float(last.ema_50), float(last.ema_200)
    rsi = float(last.rsi_14) if pd.notna(last.rsi_14) else 50.0
    atr = float(last.atr_14) if pd.notna(last.atr_14) else price * 0.02
    atr_pct = float(last.atr_pct) if pd.notna(last.atr_pct) else 2.0
    vol_avg = float(last.volume_sma_20) if pd.notna(last.volume_sma_20) else 0.0
    volume_confirmed = float(last.volume) > vol_avg if vol_avg else False
    macd_confirmed = bool(last.macd > last.macd_signal) if pd.notna(last.macd_signal) else False

    checks = {
        "trend": price > ema50 > ema200,
        "momentum": 50 <= rsi <= 70,
        "volume": volume_confirmed,
        "macd": macd_confirmed,
        "volatility": atr_pct <= 5.0,
    }
    weights = {"trend": 3, "momentum": 2, "volume": 2, "macd": 2, "volatility": 1}
    score = sum(weights[name] for name, passed in checks.items() if passed)

    entry = stop = target = None
    if checks["trend"] and checks["momentum"] and checks["volume"] and checks["macd"] and score >= 8:
        action = "BUY"
        entry = price
        stop = price - 1.5 * atr
        target = price + 3.0 * atr
    elif price < ema50 and price < ema200:
        action = "AVOID"
    else:
        action = "WAIT"

    labels = {
        "trend": "Price is above EMA 50 and EMA 200, with EMA 50 above EMA 200",
        "momentum": "RSI(14) is within the 50–70 momentum band",
        "volume": "Volume is above its 20-session average",
        "macd": "MACD is above its signal line",
        "volatility": "ATR is no more than 5% of the current price",
    }
    rationale = [
        (labels[name] if passed else f"Not confirmed: {labels[name]}")
        for name, passed in checks.items()
    ]
    if len(df) < 200:
        rationale.append(f"Only {len(df)} candles available; long-term EMA context is still warming up")

    as_of = pd.Timestamp(last.date).isoformat() if pd.notna(last.date) else None
    return {
        "symbol": symbol, "action": action, "score": float(score),
        "price": round(price, 2),
        "entry_price": round(entry, 2) if entry is not None else None,
        "stop_loss": round(stop, 2) if stop is not None else None,
        "target_price": round(target, 2) if target is not None else None,
        "rsi_14": round(rsi, 2), "ema_50": round(ema50, 2),
        "ema_200": round(ema200, 2), "atr_14": round(atr, 2),
        "volume_confirmed": volume_confirmed,
        "holding_period": "1–5 trading days" if action == "BUY" else None,
        "rationale": rationale, "checks": checks,
        "strategy_version": STRATEGY_VERSION, "as_of": as_of,
    }
