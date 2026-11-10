import asyncio
import logging
import threading
from datetime import datetime, timezone

from fastapi import WebSocket
from app.core.config import settings
from app.market_data.demo import DEFAULT_SYMBOLS

logger = logging.getLogger(__name__)


class MarketStream:
    """Fan-out live Kite ticks to connected browser sessions."""

    def __init__(self):
        self.loop = None
        self.ticker = None
        self.connected = False
        self.clients: set[asyncio.Queue] = set()
        self.latest: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.tokens: dict[int, str] = {}

    def start(self):
        if settings.market_data_provider.lower() != "zerodha":
            return
        if not settings.kite_api_key or not settings.kite_access_token:
            logger.warning("Kite stream not started: API key/access token missing")
            return
        try:
            from kiteconnect import KiteConnect, KiteTicker

            self.loop = asyncio.get_running_loop()
            client = KiteConnect(api_key=settings.kite_api_key)
            client.set_access_token(settings.kite_access_token)
            instruments = client.instruments("NSE")
            wanted = set(DEFAULT_SYMBOLS)
            self.tokens = {
                int(row["instrument_token"]): row["tradingsymbol"]
                for row in instruments if row["tradingsymbol"] in wanted and row["segment"] == "NSE"
            }
            self.ticker = KiteTicker(settings.kite_api_key, settings.kite_access_token)
        except Exception:
            logger.exception("Could not initialise Kite market stream; API will continue without streaming")
            return

        def on_connect(ws, response):
            self.connected = True
            token_ids = list(self.tokens)
            if token_ids:
                ws.subscribe(token_ids)
                ws.set_mode(ws.MODE_FULL, token_ids)
            logger.info("Kite stream connected; subscribed to %s instruments", len(token_ids))
            if self.loop and not self.loop.is_closed():
                asyncio.run_coroutine_threadsafe(self.publish({"type": "status", "provider": "ZERODHA KITE CONNECT", "is_live": True, "data": self.snapshot()}), self.loop)

        def on_ticks(ws, ticks):
            updates = []
            now = datetime.now(timezone.utc).isoformat()
            for tick in ticks:
                symbol = self.tokens.get(int(tick.get("instrument_token", 0)))
                if not symbol:
                    continue
                ohlc = tick.get("ohlc") or {}
                update = {
                    "symbol": symbol,
                    "exchange": "NSE",
                    "last_price": float(tick.get("last_price") or 0),
                    "change": float(tick.get("last_price") or 0) - float(ohlc.get("close") or tick.get("last_price") or 0),
                    "change_percent": float(tick.get("change") or 0),
                    "volume": int(tick.get("volume_traded") or tick.get("volume") or 0),
                    "open": float(ohlc.get("open") or 0),
                    "high": float(ohlc.get("high") or 0),
                    "low": float(ohlc.get("low") or 0),
                    "close": float(ohlc.get("close") or 0),
                    "timestamp": now,
                    "source": "zerodha_websocket",
                }
                with self.lock:
                    self.latest[symbol] = update
                updates.append(update)
            if updates and self.loop and not self.loop.is_closed():
                asyncio.run_coroutine_threadsafe(self.publish({"type": "ticks", "data": updates}), self.loop)

        self.ticker.on_connect = on_connect
        self.ticker.on_ticks = on_ticks
        def on_close(ws, code, reason):
            self.connected = False
            logger.warning("Kite stream closed: %s %s", code, reason)
            if self.loop and not self.loop.is_closed():
                asyncio.run_coroutine_threadsafe(self.publish({"type": "status", "provider": "ZERODHA KITE CONNECT", "is_live": False, "data": []}), self.loop)

        def on_error(ws, code, reason):
            self.connected = False
            logger.error("Kite stream error %s: %s", code, reason)
            if self.loop and not self.loop.is_closed():
                asyncio.run_coroutine_threadsafe(self.publish({"type": "status", "provider": "ZERODHA KITE CONNECT", "is_live": False, "data": []}), self.loop)
        self.ticker.on_error = on_error
        try:
            self.ticker.connect(threaded=True)
        except Exception:
            logger.exception("Could not start Kite WebSocket connection")

    async def publish(self, message: dict):
        dead = []
        for queue in list(self.clients):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(message)
                except Exception:
                    dead.append(queue)
        for queue in dead:
            self.clients.discard(queue)

    def snapshot(self, symbols: list[str] | None = None):
        with self.lock:
            values = list(self.latest.values())
        if symbols:
            wanted = set(symbols)
            values = [value for value in values if value["symbol"] in wanted]
        return values


market_stream = MarketStream()
