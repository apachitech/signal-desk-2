import asyncio
import json
import logging
from typing import Dict, List, Optional, Deque
from collections import deque
import websockets

logger = logging.getLogger("LiveFeed")

# Global in-memory storage for WebSocket candles: key -> deque(maxlen=300)
_WS_CANDLE_BUFFER: Dict[str, Deque[Dict]] = {}
_ACTIVE_TASKS: List[asyncio.Task] = []


class BinanceWebSocketFeed:
    """
    Maintains persistent, real-time WebSocket tick connection with Binance.
    Sub-100ms real market candle updates for cryptocurrencies.
    Fails over gracefully with silent exponential backoff if regional ISP blocks Binance.
    """
    def __init__(self, symbols: List[str] = None, intervals: List[str] = None):
        self.symbols = [s.lower() for s in (symbols or ["btcusdt", "ethusdt", "solusdt"])]
        self.intervals = intervals or ["1m", "5m"]
        self.running = False

    def _get_stream_urls(self) -> List[str]:
        urls = []
        for s in self.symbols:
            for tf in self.intervals:
                urls.append(f"wss://stream.binance.com:9443/ws/{s}@kline_{tf}")
        return urls

    async def _stream_worker(self, url: str):
        backoff = 5
        while self.running:
            try:
                async with websockets.connect(
                    url,
                    open_timeout=15,
                    ping_interval=20,
                    ping_timeout=20,
                    user_agent_header="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                ) as ws:
                    logger.info(f"Connected to stream: {url.split('/')[-1]}")
                    backoff = 5
                    while self.running:
                        raw = await ws.recv()
                        msg = json.loads(raw)
                        if "k" in msg:
                            k = msg["k"]
                            symbol = str(k["s"]).upper()
                            tf = str(k["i"])
                            buffer_key = f"{symbol}:{tf}"

                            if buffer_key not in _WS_CANDLE_BUFFER:
                                _WS_CANDLE_BUFFER[buffer_key] = deque(maxlen=300)

                            candle = {
                                "time": int(k["t"] // 1000),
                                "open": float(k["o"]),
                                "high": float(k["h"]),
                                "low": float(k["l"]),
                                "close": float(k["c"]),
                                "volume": float(k["v"]),
                                "is_closed": bool(k["x"])
                            }

                            buf = _WS_CANDLE_BUFFER[buffer_key]
                            if buf and buf[-1]["time"] == candle["time"]:
                                buf[-1] = candle
                            else:
                                buf.append(candle)
            except asyncio.CancelledError:
                break
            except Exception:
                # Silent exponential backoff so terminal doesn't get flooded with errors
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, 60)

    async def run(self):
        self.running = True
        urls = self._get_stream_urls()
        logger.info(f"Starting {len(urls)} real-time feed workers...")
        workers = [asyncio.create_task(self._stream_worker(u)) for u in urls]
        try:
            await asyncio.gather(*workers)
        except asyncio.CancelledError:
            self.running = False
            for w in workers:
                w.cancel()


def get_ws_candles(symbol: str, timeframe: str, limit: int = 200) -> Optional[List[Dict]]:
    """Retrieve buffered real-time WebSocket candles if available."""
    key = f"{symbol.upper()}:{timeframe}"
    if key in _WS_CANDLE_BUFFER and len(_WS_CANDLE_BUFFER[key]) >= 30:
        data = list(_WS_CANDLE_BUFFER[key])
        return data[-limit:] if len(data) >= limit else data
    return None


async def start_live_feeds():
    """Startup task to initialize real-time WebSocket workers."""
    # Start with top primary liquid pairs
    supported_crypto = ["btcusdt", "ethusdt", "solusdt"]
    feed = BinanceWebSocketFeed(supported_crypto, ["1m", "5m"])
    task = asyncio.create_task(feed.run())
    _ACTIVE_TASKS.append(task)
    return task

