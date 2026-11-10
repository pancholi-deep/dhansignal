import json
import time
from datetime import datetime, timezone
from threading import Lock

import requests

from app.core.config import settings
from app.market_data.factory import get_market_data_provider
from app.services.market import get_signals
from app.strategies.technical import add_indicators


_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_LOCK = Lock()
_CACHE_TTL_SECONDS = 300


def generate_stock_intelligence(symbol: str) -> dict:
    if not settings.gemini_api_key:
        raise RuntimeError("Gemini is not configured. Add GEMINI_API_KEY to backend .env and restart the API.")

    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(symbol)
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            return {**cached[1], "cached": True}

    market = get_market_data_provider()
    quote = next((row for row in market.get_quotes([symbol]) if row.get("symbol") == symbol), None)
    if not quote or not quote.get("last_price"):
        raise LookupError(f"No usable market quote is available for {symbol}")

    history = market.get_history(symbol, interval="day", days=240)
    if history.empty:
        raise LookupError(f"No historical candles are available for {symbol}")
    enriched = add_indicators(history.copy())
    last = enriched.iloc[-1]

    def number(field):
        try:
            value = float(last.get(field))
            return round(value, 4) if value == value and abs(value) != float("inf") else None
        except (TypeError, ValueError):
            return None

    signal = next((row for row in get_signals([symbol]) if row.get("symbol") == symbol), {})
    columns = [field for field in ["date", "open", "high", "low", "close", "volume"] if field in enriched.columns]
    context = {
        "symbol": symbol,
        "exchange": "NSE",
        "market_data_provider": market.name,
        "quote_timestamp": quote.get("timestamp"),
        "price": quote.get("last_price"),
        "day_change_percent": quote.get("change_percent"),
        "day_volume": quote.get("volume"),
        "indicators": {field: number(field) for field in ["ema_20", "ema_50", "ema_200", "rsi_14", "macd", "macd_signal", "macd_histogram", "atr_14"]},
        "rule_based_signal": {field: signal.get(field) for field in ["action", "score", "entry_price", "stop_loss", "target_price", "rationale", "strategy_version"]},
        "recent_daily_candles": enriched.tail(20)[columns].to_dict(orient="records"),
    }

    prompt = """You are DhanSignal's equity research assistant. Analyze this NSE-listed stock using ONLY the supplied market context. Do not invent company fundamentals, news, events, analyst views, or live facts. Distinguish observed data from interpretation. This is educational market analysis, not personalized financial advice. Do not promise returns or issue a guaranteed prediction.
Return valid JSON only with this exact shape:
{
  "stance": "BULLISH | NEUTRAL | BEARISH",
  "confidence": "LOW | MEDIUM | HIGH",
  "summary": "2-3 sentence assessment",
  "trend": "brief trend assessment",
  "momentum": "brief momentum assessment",
  "volume": "brief volume assessment",
  "risk": "brief risk assessment",
  "key_levels": ["price level and why it matters"],
  "watch_points": ["what to monitor next"],
  "caveats": ["data limitations"]
}
Keep each field concise. If data is incomplete or stale, say so and lower confidence."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    response = requests.post(
        url,
        params={"key": settings.gemini_api_key},
        json={
            "contents": [{"parts": [{"text": prompt + "\n\nMARKET CONTEXT JSON:\n" + json.dumps(context, default=str)}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        },
        timeout=35,
    )
    if response.status_code >= 400:
        try:
            message = response.json().get("error", {}).get("message", "Gemini API request failed")
        except ValueError:
            message = "Gemini API request failed"
        raise RuntimeError(f"Gemini API error: {message}")
    try:
        raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        analysis = json.loads(raw)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini returned an invalid analysis response") from exc

    result = {
        "symbol": symbol,
        "provider": market.name,
        "market_timestamp": quote.get("timestamp"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": settings.gemini_model,
        "analysis": analysis,
        "cached": False,
        "disclaimer": "AI-generated educational analysis from the supplied market snapshot. Not investment advice. Verify prices and information independently.",
    }
    with _CACHE_LOCK:
        _CACHE[symbol] = (now, result)
    return result
