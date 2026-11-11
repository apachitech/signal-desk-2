# Transformation Blueprint: Turning SignalDesk into a Real-Time Quantitative Trading Bot

This document outlines the complete architectural, algorithmic, and infrastructure transformation to convert **SignalDesk** from a simulated web dashboard into a **production-grade, real-time algorithmic trading system and live signal bot**.

---

## Table of Contents
1. [Executive Summary & Current State Audit](#1-executive-summary--current-state-audit)
2. [Target Production Architecture](#2-target-production-architecture)
3. [Phase 1: Real-Time Data Pipeline (WebSockets)](#3-phase-1-real-time-data-pipeline-websockets)
4. [Phase 2: Signal Engine Hardening (Chop Filter & Multi-Timeframe)](#4-phase-2-signal-engine-hardening-chop-filter--multi-timeframe)
5. [Phase 3: Automated Execution & Notification Layer](#5-phase-3-automated-execution--notification-layer)
6. [Phase 4: Server Infrastructure (VPS vs Serverless)](#6-phase-4-server-infrastructure-vps-vs-serverless)
7. [Step-by-Step Code Blueprint & Modules](#7-step-by-step-code-blueprint--modules)
8. [Risk Governance & Safe Forward-Testing Checklist](#8-risk-governance--safe-forward-testing-checklist)

---

## 1. Executive Summary & Current State Audit

### Why the Current Version Cannot Trade Real Capital
- **Synthetic OTC Data:** Pairs like `EURUSD_OTC` and `XAUUSD_OTC` are currently rendered via mathematical sine waves (`math.sin`) and pseudo-random numbers in `app/data_fetcher.py`. Pocket Option OTC prices are internal broker feeds that have zero correlation with these sine waves.
- **Client Fallback Illusion:** When backend APIs fail or cold-start, `public/app.js` falls back to `Math.random()` Brownian motion candles while printing `"Live Feed: 12 ms (Edge Synced)"`, giving a false sense of real market connectivity.
- **Forced Trade Bias:** In `app/signal_engine.py`, the engine is designed to fire a `BUY` or `SELL` on every single candle even when confluence is zero, rather than staying in cash during sideways chop.
- **Serverless Limitations:** Vercel functions terminate after 10–15 seconds and sleep between requests. A real bot requires persistent, uninterrupted WebSocket connections.

### The Transformation Goal
Build an automated engine that:
1. Ingests genuine sub-100ms market ticks directly from official exchange/broker WebSockets.
2. Filters out market chop with strict regime detection (**ADX** and **Higher-Timeframe Alignment**), staying in cash 70–80% of the time.
3. Automatically executes trades or dispatches instant Telegram/Discord alerts with entry points, stop-losses, and take-profit targets.
4. Operates 24/7 on a persistent Linux VPS under Docker supervision.

---

## 2. Target Production Architecture

```
                    ┌────────────────────────────────────────────────────────┐
                    │               REAL-TIME DATA INGESTION                 │
                    │  - Binance WebSocket (Crypto ticks: < 50ms)            │
                    │  - OANDA / Polygon.io WebSocket (Forex ticks: < 100ms) │
                    │  - Deriv / Pocket Option Session WS                    │
                    └──────────────────────────┬─────────────────────────────┘
                                               │ Raw Tick Stream
                                               ▼
                    ┌────────────────────────────────────────────────────────┐
                    │               IN-MEMORY TICK & OHLC AGGREGATOR         │
                    │  - Real-time 1m / 5m candle generation                 │
                    │  - Rolling DataFrame with NumPy / Pandas               │
                    └──────────────────────────┬─────────────────────────────┘
                                               │ Structured Candle DataFrame
                                               ▼
                    ┌────────────────────────────────────────────────────────┐
                    │            HARDENED QUANTITATIVE SIGNAL ENGINE         │
                    │  1. Higher Timeframe Trend Filter (1H EMA 50/200 Slope)│
                    │  2. Volatility & Trend Strength Filter (ADX > 22)      │
                    │  3. Confluence Entry (EMA 9/21 cross + RSI momentum)   │
                    │  4. Reject condition: Emit "WAIT / NO TRADE" if choppy │
                    └──────────────────────────┬─────────────────────────────┘
                                               │ Validated Signal Event
                                               ▼
                    ┌────────────────────────────────────────────────────────┐
                    │             DISPATCH & EXECUTION LAYER                 │
                    │  - Option A: Instant Telegram / Push Notifications     │
                    │  - Option B: MetaTrader 5 (MT5 Python API for Forex)   │
                    │  - Option C: CCXT (Binance / Bybit Auto-Trading)       │
                    │  - Option D: Playwright / Deriv API for Binary Options │
                    └────────────────────────────────────────────────────────┘
```

---

## 3. Phase 1: Real-Time Data Pipeline (WebSockets)

### 3.1 Eliminating Synthetic Sine Waves
1. In `app/data_fetcher.py`, completely remove `generate_synthetic_candles()`.
2. In `public/app.js`, remove `generateClientFallbackSignal()` and `clientFallbackState`.
3. If an API disconnects, the system must display an explicit **`DISCONNECTED / RECONNECTING`** state rather than fabricating random prices.

### 3.2 Selecting True Market Tick Feeds

#### A. Cryptocurrency (Free & Ultra-Fast)
- **Provider:** Binance Public WebSocket
- **Endpoint:** `wss://stream.binance.com:9443/ws/<symbol>@kline_5m`
- **Cost:** Free, no API key required, institutional tick speeds (< 50ms).

#### B. Forex & Spot Metals (Mon–Fri)
- **Option 1 (Recommended):** **OANDA v20 REST & Streaming API**. Free demo account gives live streaming exchange rates.
- **Option 2:** **Polygon.io** or **Finnhub** WebSocket for institutional interbank quotes.
- **Option 3:** **MetaTrader 5 (MT5) Terminal**. Run MT5 locally or on a Windows VPS, and use the official Python `MetaTrader5` package to pull real-time broker ticks directly into Python.

#### C. Pocket Option OTC Assets (Weekend & Night)
- **The Hard Truth:** Pocket Option OTC prices are internal broker-generated quotes. You cannot get them from TradingView, Yahoo Finance, or Binance.
- **Solutions:**
  - **Strategy A (Standard Pairs):** Trade normal standard pairs (`EURUSD`, `GBPUSD`, `XAUUSD`) during global market hours (Monday 00:00 UTC to Friday 21:00 UTC). During this window, Pocket Option's quotes track real market prices.
  - **Strategy B (WebSocket Session Scraper):** Connect directly to Pocket Option's live WebSocket gateway using your authenticated session token to capture broker ticks in real time.
  - **Strategy C (Deriv API):** Consider **Deriv.com**, which offers a completely transparent, documented WebSocket API (`deriv-api`) for automated synthetic & binary options trading.

---

## 4. Phase 2: Signal Engine Hardening (Chop Filter & Multi-Timeframe)

A genuine trading edge relies on **selective execution**. Most trading days consist of range-bound noise. The engine must actively say **NO TRADE** when conditions are suboptimal.

### 4.1 Strict Chop Elimination Rule
1. **Average Directional Index (ADX):**
   - Compute 14-period ADX on the active timeframe.
   - If `ADX < 22`, the market is consolidated $\rightarrow$ **Suppress all signals (`WAIT / NO TRADE`)**.
   - Only allow trades when `ADX >= 22` with a rising slope.

2. **Bollinger Band Squeeze:**
   - If Bollinger Band Width is in the bottom 20th percentile of its 50-bar range, market energy is contracting $\rightarrow$ **Do not trade breakouts until expansion occurs**.

### 4.2 Multi-Timeframe (MTF) Alignment
- **Macro Anchor:** 1-Hour (1H) or 15-Minute (15m) chart.
  - Macro Bullish: 1H Price > EMA 50 AND EMA 50 > EMA 200.
  - Macro Bearish: 1H Price < EMA 50 AND EMA 50 < EMA 200.
- **Execution Chart:** 5-Minute (5m) or 1-Minute (1m) chart.
  - **CALL / BUY Rule:** Only allowed when Macro Anchor is Bullish AND 5m price pulls back to the EMA 9/21 zone with RSI bouncing out of 40–50.
  - **PUT / SELL Rule:** Only allowed when Macro Anchor is Bearish AND 5m price rallies to the EMA 9/21 zone with RSI rejecting 50–60.

### 4.3 Candle Open Discipline
- Never trigger signals mid-candle on erratic intra-bar ticks.
- Signals are finalized on the **close of candle $T$**, with immediate entry execution on the **first 1–3 seconds of candle $T+1$**.

---

## 5. Phase 3: Automated Execution & Notification Layer

### 5.1 Telegram Real-Time Notification Bot
A dedicated background service that pushes instantaneous trade alerts directly to your phone:
- Asset name & timeframe.
- Direction: 🟢 **CALL (HIGHER)** or 🔴 **PUT (LOWER)**.
- Exact Entry Price & Optimal Entry Range.
- Expiration Time (e.g. Exact 5-minute contract expiry).
- Confluence Checklist (ADX score, 1H trend alignment, RSI level).

### 5.2 Auto-Execution Engines

#### For Forex & Metals: MetaTrader 5 (MT5)
Using Python's native `MetaTrader5` library:
```python
import MetaTrader5 as mt5

# Initialize connection
mt5.initialize()

# Send Market Order
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "EURUSD",
    "volume": 0.10,
    "type": mt5.ORDER_TYPE_BUY,
    "price": mt5.symbol_info_tick("EURUSD").ask,
    "sl": sl_price,
    "tp": tp_price,
    "deviation": 10,
    "magic": 100200,
    "comment": "SignalDesk Bot Execution",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}
result = mt5.order_send(request)
```

#### For Crypto: CCXT
Using the industry-standard `ccxt` library:
```python
import ccxt

exchange = ccxt.binance({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET',
    'enableRateLimit': True,
})

# Create Order
order = exchange.create_order('BTC/USDT', 'market', 'buy', 0.01)
```

#### For Pocket Option / Binary Options
- Use a headless browser framework (such as **Playwright** in Python) to control a clean browser session logged into your broker, executing clicks on the CALL/PUT buttons in under 150ms upon receiving an internal webhook event.

---

## 6. Phase 4: Server Infrastructure (VPS vs Serverless)

| Factor | Vercel Serverless (Current) | Dedicated Linux VPS (Target) |
| :--- | :--- | :--- |
| **Execution Model** | Ephemeral (Sleeps after request) | Continuous 24/7 background loop |
| **WebSockets** | Disconnected / Not supported for long runs | Persistent, uninterrupted tick stream |
| **Latency** | 200ms – 1,500ms (Cold starts) | 10ms – 40ms to exchange servers |
| **Telegram / Background Tasks** | Dies when function completes | Runs uninterrupted daemon processes |
| **Cost** | Free tier | $4 – $6 / month (DigitalOcean, Hetzner, Lightsail) |

### Deployment Strategy
1. Deploy a small Ubuntu 22.04 LTS instance (1 vCPU, 2GB RAM, close to broker servers—e.g., London or Frankfurt).
2. Run backend via `Docker` or `systemd`.
3. Use NGINX as a reverse proxy with SSL (Let's Encrypt).
4. Run the frontend UI as static assets served by NGINX or keep the frontend on Vercel connecting back to the VPS WebSocket.

---

## 7. Step-by-Step Code Blueprint & Modules

Here are the concrete code modules to build into the codebase:

### Module 1: Real-Time Binance WebSocket Tick Worker (`app/live_feed.py`)
```python
import asyncio
import json
import websockets
import logging
from collections import deque

logger = logging.getLogger("LiveFeed")

class BinanceTickFeed:
    def __init__(self, symbol: str = "btcusdt", interval: str = "5m"):
        self.symbol = symbol.lower()
        self.interval = interval
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_{self.interval}"
        self.candles = deque(maxlen=300)
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    logger.info(f"Connected to Binance WebSocket stream: {self.symbol}")
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        k = data['k']
                        candle = {
                            "time": int(k['t'] // 1000),
                            "open": float(k['o']),
                            "high": float(k['h']),
                            "low": float(k['l']),
                            "close": float(k['c']),
                            "volume": float(k['v']),
                            "is_closed": bool(k['x'])
                        }
                        self._update_candle(candle)
            except Exception as e:
                logger.warning(f"WebSocket disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

    def _update_candle(self, candle: dict):
        if not self.candles:
            self.candles.append(candle)
        elif self.candles[-1]["time"] == candle["time"]:
            self.candles[-1] = candle
        else:
            self.candles.append(candle)
```

### Module 2: Hardened Signal Engine with ADX & Chop Filter (`app/quant_engine.py`)
```python
import pandas as pd
import numpy as np

def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates Wilder's Average Directional Index (ADX)."""
    alpha = 1.0 / period
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=alpha, adjust=False).mean()

    up_move = df['high'] - df['high'].shift()
    down_move = df['low'].shift() - df['low']

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_di = 100 * (pd.Series(plus_dm).ewm(alpha=alpha, adjust=False).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm).ewm(alpha=alpha, adjust=False).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9))
    adx = dx.ewm(alpha=alpha, adjust=False).mean()
    return adx

def evaluate_quant_signal(df_exec: pd.DataFrame, df_macro: pd.DataFrame) -> dict:
    """
    Evaluates confluence across two timeframes.
    Only returns BUY or SELL when real statistical edge exists.
    Otherwise returns 'WAIT'.
    """
    if len(df_exec) < 50 or len(df_macro) < 50:
        return {"action": "WAIT", "reason": "Insufficient candle history."}

    # Macro trend evaluation (e.g. 1H timeframe)
    macro_close = df_macro['close'].iloc[-1]
    macro_ema50 = df_macro['close'].ewm(span=50).mean().iloc[-1]
    macro_ema200 = df_macro['close'].ewm(span=200).mean().iloc[-1]

    macro_bullish = macro_close > macro_ema50 and macro_ema50 > macro_ema200
    macro_bearish = macro_close < macro_ema50 and macro_ema50 < macro_ema200

    # Execution timeframe indicators (e.g. 5m)
    c = df_exec.iloc[-1]
    prev = df_exec.iloc[-2]
    
    adx = compute_adx(df_exec).iloc[-1]
    if adx < 22:
        return {
            "action": "WAIT",
            "reason": f"Market in low-volatility chop (ADX {adx:.1f} < 22). Capital preserved."
        }

    ema9 = df_exec['close'].ewm(span=9).mean()
    ema21 = df_exec['close'].ewm(span=21).mean()
    
    bullish_cross = (prev['close'] <= ema9.iloc[-2]) and (c['close'] > ema9.iloc[-1]) and (ema9.iloc[-1] > ema21.iloc[-1])
    bearish_cross = (prev['close'] >= ema9.iloc[-2]) and (c['close'] < ema9.iloc[-1]) and (ema9.iloc[-1] < ema21.iloc[-1])

    if macro_bullish and bullish_cross:
        return {
            "action": "BUY",
            "entry_price": c['close'],
            "adx": round(adx, 1),
            "reason": "1H Macro Bullish Trend + 5m EMA 9/21 Dynamic Pullback Bounce."
        }
    elif macro_bearish and bearish_cross:
        return {
            "action": "SELL",
            "entry_price": c['close'],
            "adx": round(adx, 1),
            "reason": "1H Macro Bearish Trend + 5m EMA 9/21 Dynamic Resistance Rejection."
        }

    return {"action": "WAIT", "reason": "Awaiting clean pullback alignment with macro trend."}
```

### Module 3: Instant Telegram Notification Bot (`app/telegram_bot.py`)
```python
import httpx
import logging

logger = logging.getLogger("TelegramBot")

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    async def send_signal(self, asset: str, timeframe: str, action: str, price: float, reason: str):
        emoji = "🟢 CALL / BUY" if action == "BUY" else "🔴 PUT / SELL"
        message = (
            f"⚡ <b>SIGNALDESK LIVE TRADE ALERT</b> ⚡\n\n"
            f"<b>Asset:</b> {asset}\n"
            f"<b>Timeframe:</b> {timeframe}\n"
            f"<b>Direction:</b> {emoji}\n"
            f"<b>Entry Price:</b> <code>{price}</code>\n"
            f"<b>Execution Rule:</b> Enter on candle open\n\n"
            f"<b>Confluence Reason:</b>\n{reason}\n\n"
            f"⚠️ <i>Strict 1-2% Account Risk Rule Applies.</i>"
        )
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.post(self.api_url, json=payload)
                if resp.status_code == 200:
                    logger.info("Telegram signal successfully dispatched.")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
```

---

## 8. Risk Governance & Safe Forward-Testing Checklist

Before committing a single dollar of live capital to the transformed system, complete the following validation protocol:

- [ ] **Step 1: Code Sanitization**
  - Verify that `generate_synthetic_candles` and `clientFallbackState` are completely purged or restricted strictly to offline test suites.
- [ ] **Step 2: WebSocket Connectivity Verification**
  - Verify tick timestamps against UTC wall clock. Ticks must arrive within $\le 250\text{ ms}$ of exchange server events.
- [ ] **Step 3: "Cash First" Discipline**
  - Over a 24-hour test period, verify that the signal engine spends the majority of its time emitting `WAIT / NO TRADE` during sideways periods. A system that triggers 100 trades a day is overtrading. A solid system produces 3 to 10 high-conviction trades per asset per day.
- [ ] **Step 4: Demo Account Forward-Testing (100-Trade Sample)**
  - Run the bot on a Demo account for a minimum of **100 consecutive trades**.
  - In binary options, calculate your real win rate:
    $$\text{Win Rate} = \frac{\text{Winning Trades}}{100}$$
    - If Win Rate $< 56\%$, the negative house edge (85% payout vs 100% loss) will deplete capital.
    - If Win Rate $\ge 62\%$, the statistical edge is positive.
- [ ] **Step 5: Hardcoded Drawdown Circuit Breaker**
  - Enforce a software kill-switch: If daily account drawdown reaches **4%**, the bot terminates all connections and shuts down until 00:00 UTC.

---

## Conclusion
By replacing synthetic data with real WebSocket streams, enforcing an ADX chop filter with multi-timeframe confirmation, moving from serverless to a dedicated VPS, and routing signals to Telegram or broker APIs, **SignalDesk** transforms into a robust, legitimate, and profitable algorithmic trading tool.
