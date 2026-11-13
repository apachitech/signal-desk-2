# Why You Cannot (and Should Not) Deploy a Quantitative Trading Bot on Vercel

> **Executive Summary:** Vercel is one of the world's greatest platforms for frontend web apps (Next.js, React, static websites). However, for a real-time quantitative trading engine like SignalDesk, **Vercel's serverless architecture makes it fundamentally impossible to run reliably.** Deploying a trading bot to Vercel will cause missed signals, broken WebSocket connections, and financial losses.

---

## 1. The Core Architectural Conflict: Serverless vs. Stateful Trading Engine

| Requirement of a Real Trading Bot | Vercel Serverless Architecture | What Happens on Vercel |
| :--- | :--- | :--- |
| **Persistent In-Memory Candle Buffers** | Functions freeze and die after 10–15 seconds of inactivity. | Memory is erased between clicks. Indicators lose their 200-candle history. |
| **Continuous WebSocket Market Stream** (`wss://`) | Serverless functions cannot hold open persistent background TCP sockets. | WebSocket disconnects immediately upon function sleep. Zero tick updates. |
| **24/7 Background Signal Evaluation Engine** | Execution only triggers when an external HTTP request arrives. | The bot cannot evaluate trends in the background or send alerts when you aren't browsing. |
| **Real-Time Instant Telegram Alerts** | Serverless functions sleep to 0 instances when idle. | Cold-start latency (1–5 seconds) means price moves before the alert is generated. |

---

## 2. The 4 Technical Blockers Explained

### A. Ephemeral Memory (Zero State Retention)
* **How SignalDesk Works:** To compute an **EMA 21**, **RSI 14**, and **Wilder's ADX 14**, the engine maintains a sliding window buffer of 50 to 300 recent candles in RAM (`_WS_CANDLE_BUFFER` in `app/live_feed.py`).
* **Why Vercel Fails:** Vercel spins up micro-containers on demand and **destroys them** seconds after the HTTP response is returned. Every time a new request arrives, a completely fresh container boots up with **empty memory**. The bot would have to re-fetch hundreds of historical candles on every single indicator calculation, leading to rate-limits and lag.

### B. Inability to Run Background Loops (`while True` / `asyncio.create_task`)
* **How SignalDesk Works:** When FastAPI starts up (`on_startup`), it spawns a background asyncio task that streams real-time prices from exchange feeds 24/7.
* **Why Vercel Fails:** Vercel executes serverless functions within strict execution timeouts (10 seconds on Hobby, up to 60–300s on Pro). As soon as the main request finishes, **all background tasks and worker threads are abruptly terminated** by Vercel's hypervisor.

### C. Persistent Inbound/Outbound WebSockets Are Disallowed
* Real-time tick feeds require a continuous, uninterrupted socket connection (`wss://stream.binance.com:9443` or Kraken WS).
* Vercel functions cannot maintain open outbound WebSocket connections while idle. The handshake drops, throwing `WebSocketConnectionClosed` or timeout exceptions.

### D. Cold Start Latency Destroys Trading Execution
* In binary options (Pocket Option, Quotex) and high-frequency crypto trading, an entry delay of **2 to 3 seconds** changes a winning trade into a loss.
* When a Vercel serverless function goes to sleep, the next trigger incurs a **1,000ms to 4,000ms "Cold Start"** while AWS Lambda / Vercel initializes Python runtime, imports libraries (`pandas`, `numpy`, `fastapi`), and re-establishes network connections.

---

## 3. What Vercel CAN Be Used For (If You Really Want Vercel)

If you love Vercel's fast CDN and global edge network, the correct architecture is a **Split Architecture**:

```
[ User Browser / Phone ]
          │
          ▼
   Vercel Edge CDN (Frontend Only: HTML / CSS / JS)
          │
          │ (REST / WebSocket API Calls)
          ▼
   Dedicated Persistent Server (Backend Python Engine)
   ├── Local PC / Laptop ($0)
   ├── Oracle Cloud Always Free VM ($0)
   ├── Render.com Web Service ($0 - $7/mo)
   └── DigitalOcean / Hetzner VPS ($4/mo)
          │
          ▼
   Live Exchanges (Binance / Kraken) & Telegram Alerts
```

In this setup:
- **Vercel** hosts only static assets (`index.html`, `style.css`, `app.js`).
- **A persistent Python server** runs the actual calculations, WebSocket ingestion, and Telegram dispatcher.

---

## 4. The Correct Free Alternatives to Vercel for Trading Bots

If you want free or low-cost hosting that **does** support persistent Python background processes and WebSockets:

| Platform | Free Tier Available? | Persistent WebSocket? | Background Engine? | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Vercel** | Yes | ❌ NO | ❌ NO | **Do Not Use** |
| **Local PC / Laptop** | **100% Free** | ✅ YES | ✅ YES | **Best & Fastest for Starting** |
| **Render.com** | 750 free hrs/mo | ✅ YES | ✅ YES | **Recommended Cloud Option** |
| **Oracle Cloud** | Always Free Forever | ✅ YES | ✅ YES | **Best 24/7 Free Linux VPS** |
| **Koyeb** | Free Nano Eco Tier | ✅ YES | ✅ YES | **Great Free Container Host** |
| **Railway** | $5 monthly credit | ✅ YES | ✅ YES | **Very Easy Setup** |

---

## 5. Conclusion

Do not try to force a real-time trading engine into a serverless environment like Vercel. 

To trade profitably and safely:
1. Run SignalDesk locally on your machine during trading sessions (`python run.py`), **OR**
2. Deploy it to a continuous container/VPS platform (Render, Oracle Cloud Always Free, or an inexpensive $4 Linux server).

*(Detailed step-by-step instructions for running without paying for a VPS can be found in [**`IF-NO-MONEY-4-VPS.md`**](file:///c:/Users/XPRISTO/Desktop/signal-desk-2/IF-NO-MONEY-4-VPS.md)).*

