import json
import logging
import time
from datetime import datetime, timezone
from threading import Lock

import requests

from app.core.config import settings
from app.market_data.factory import get_market_data_provider
from app.strategies.technical import generate_signal
from app.strategies.technical import add_indicators


_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_LOCK = Lock()
_CACHE_TTL_SECONDS = 300
logger = logging.getLogger(__name__)


def generate_stock_intelligence(symbol: str) -> dict:
    if not settings.gemini_api_key:
        raise RuntimeError("Gemini is not configured. Add GEMINI_API_KEY to backend .env and restart the API.")

    now = time.monotonic()
    cache_key = f"{settings.market_data_provider}:{settings.gemini_model}:{symbol}"
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            return {**cached[1], "cached": True}

    started = time.monotonic()
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

    signal = generate_signal(symbol, history)
    logger.info("Prepared Gemini context for %s in %.2fs", symbol, time.monotonic() - started)
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

    prompt = """Act as a seasoned equity research analyst with 20 years of experience across fundamental analysis, technical analysis, and behavioral finance. I am providing you with the following documents for [Company Name]: annual financial statements, Management Discussion & Analysis, concall transcripts, a daily technical chart, key ratios from Screener, and the latest shareholding pattern.

Tear this company apart across these dimensions:

FUNDAMENTALS — Is this business genuinely healthy or just looks good on surface? Dig into revenue quality, margin trajectory, cash flow vs reported profits, debt structure, and ROE sustainability. Flag any accounting red flags.

MANAGEMENT DNA — Read between the lines of the concall transcripts and MDA. Is management confident or defensive? Are they overpromising and underdelivering? Any change in language tone vs last year? Promoter pledge or stake reduction is an automatic red flag — call it out.

VALUATION REALITY — Is the market pricing in perfection? Compare current P/E, EV/EBITDA against historical averages and sector peers. Tell me if I am paying a premium for growth that may never come.

TECHNICAL STRUCTURE — Where is the stock in its trend cycle? Is it in accumulation, markup, distribution, or markdown phase? Key support and resistance levels. Is volume confirming price action or diverging?

RISK FACTORS — What are the 3 things that could destroy this thesis? Sector risk, company-specific risk, macro risk.

FINAL VERDICT — Buy, Hold, or Avoid. Conviction score out of 10. Price at which this becomes interesting if not now. One line that summarizes this stock. Do not give me a balanced, diplomatic answer. I want the truth — even if it is uncomfortable.

Use only evidence in the supplied context and documents. Never fabricate financial metrics, historical averages, peer multiples, management statements, pledge data, or shareholding changes. For each dimension, distinguish verified facts from interpretation. If a required document or metric is absent, explicitly say "Data unavailable" and explain how that limits the conclusion. Do not infer that promoter pledge or stake reduction exists without shareholding evidence. A price level must be derived from supplied market data; if it cannot be justified, return null. This is educational research, not personalized financial advice.

Return valid JSON only with this exact shape:
{
  "fundamentals": "Detailed assessment; cite supplied document names/pages or say Data unavailable.",
  "management_dna": "Detailed assessment; cite supplied document names/pages or say Data unavailable.",
  "valuation_reality": "Detailed assessment; cite supplied metrics or say Data unavailable.",
  "technical_structure": "Trend-cycle assessment, support/resistance and volume confirmation, grounded in supplied chart/candles.",
  "risk_factors": ["Three specific thesis risks; explicitly mark unavailable evidence where applicable."],
  "final_verdict": {
    "rating": "BUY, HOLD, or AVOID",
    "conviction_score": 0,
    "interesting_price": null,
    "one_line_summary": "Blunt one-line conclusion"
  },
  "key_evidence": ["Specific facts with source names and page/period where available."],
  "data_gaps": ["Documents, metrics or comparisons not supplied."],
  "caveats": ["Material limitations and assumptions."]
}

Conviction score must be an integer from 0 to 10. Do not default to HOLD merely because evidence is incomplete; instead give the best-supported verdict and lower conviction when necessary. Keep the analysis direct, specific, and evidence-led."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    response = requests.post(
        url,
        headers={"x-goog-api-key": settings.gemini_api_key},
        json={
            "contents": [{"parts": [{"text": prompt + "\n\nMARKET CONTEXT JSON:\n" + json.dumps(context, default=str)}]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 1200, "thinkingConfig": {"thinkingLevel": "LOW"}},
        },
        timeout=(10, 90),
    )
    logger.info("Gemini request for %s using %s completed with HTTP %s in %.2fs", symbol, settings.gemini_model, response.status_code, time.monotonic() - started)
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
        _CACHE[cache_key] = (now, result)
    return result
