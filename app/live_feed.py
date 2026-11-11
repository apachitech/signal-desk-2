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
    Sub-100ms real market candle updates for cryptocurrencies & gold proxies.
    """
    def __init__(self, symbols: List[str] = None, intervals: List[str] = None):
        self.symbols = [s.lower() for s in (symbols or ["btcusdt", "ethusdt", "solusdt"])]
        self.intervals = intervals or ["1m", "5m", "15m"]
        self.running = False

    def _get_stream_url(self) -> str:
        streams = []
        for s in self.symbols:
            for tf in self.intervals:
                streams.append(f"{s}@kline_{tf}")
        stream_path = "/".join(streams)
        return f"wss://stream.binance.com:9443/ws/{stream_path}"

    async def run(self):
        self.running = True
        url = self._get_stream_url()
        while self.running:
            try:
                logger.info(f"Connecting to Binance Stream: {len(self.symbols)} assets...")
                async with websockets.connect(url, ping_interval=20, ping_timeout=15) as ws:
                    logger.info("Binance WebSocket stream established successfully.")
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
                self.running = False
                break
            except Exception as e:
                logger.warning(f"Binance WS connection error: {e}. Reconnecting in 3 seconds...")
                await asyncio.sleep(3)


def get_ws_candles(symbol: str, timeframe: str, limit: int = 200) -> Optional[List[Dict]]:
    """Retrieve buffered real-time WebSocket candles if available."""
    key = f"{symbol.upper()}:{timeframe}"
    if key in _WS_CANDLE_BUFFER and len(_WS_CANDLE_BUFFER[key]) >= 30:
        data = list(_WS_CANDLE_BUFFER[key])
        return data[-limit:] if len(data) >= limit else data
    return None


async def start_live_feeds():
    """Startup task to initialize real-time WebSocket workers."""
    supported_crypto = ["btcusdt", "ethusdt", "solusdt", "bnbusdt", "xrpusdt", "dogeusdt", "adausdt"]
    feed = BinanceWebSocketFeed(supported_crypto, ["1m", "5m", "15m"])
    task = asyncio.create_task(feed.run())
    _ACTIVE_TASKS.append(task)
    return task

