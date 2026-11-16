# Pocket Option Automated Trading: Operating Guide

> **Important Safety Notice:** Your Auto-Trader is configured in **Demo Mode by default** (`PO_IS_DEMO=true`). It trades with practice money ($0 real risk). Do **not** switch to real money until you have verified at least 20 to 30 automated trades on Demo.

---

## Table of Contents
1. [How Your Auto-Trading System Works](#1-how-your-auto-trading-system-works)
2. [What You Must Do Right Now (Quick Start)](#2-what-you-must-do-right-now-quick-start)
3. [Auto-Trader Dashboard Controls](#3-auto-trader-dashboard-controls)
4. [Strict Risk Management & Circuit Breakers](#4-strict-risk-management--circuit-breakers)
5. [Telegram Notifications](#5-telegram-notifications)
6. [Updating Your Session Token When It Expires](#6-updating-your-session-token-when-it-expires)
7. [Switching from Demo to Real Account](#7-switching-from-demo-to-real-account)
8. [Summary Checklist for Every Trading Session](#8-summary-checklist-for-every-trading-session)

---

## 1. How Your Auto-Trading System Works

Your SignalDesk platform has a complete **3-layer automated execution architecture**:

```
[ Layer 1: Market Intelligence ]
Real-Time Market Feeds (Binance WebSockets, Twelve Data, Fallbacks)
              │
              ▼
[ Layer 2: Quantitative Decision Engine ]
app/main.py (Autonomous 15-second Scanner)
Evaluates: Wilder's ADX 14 (>22 Non-Chop) + EMA 9/21 Dynamic Pullback + RSI 14
              │
              ├─────────────────────────────────────────┐
              ▼                                         ▼
[ Layer 3A: Telegram Dispatcher ]         [ Layer 3B: Pocket Option Auto-Trader ]
Sends instant alert to your phone         app/pocket_trader.py
                                          Executes openOrder via WebSocket in <50ms
                                          (EURUSD_otc, BTCUSDT, etc.)
```

---

## 2. What You Must Do Right Now (Quick Start)

### Step 1: Start Your SignalDesk Server
Open PowerShell in your project folder:
```powershell
cd c:\Users\XPRISTO\Desktop\signal-desk-2
python run.py
```

### Step 2: Open the Trading Dashboard
In your browser, go to:
👉 **[http://localhost:8000](http://localhost:8000)** (or your Render live URL).

### Step 3: Turn Auto-Trader ON
Look at the top header bar next to the countdown clock:
- You will see the new pill: `[ Auto-Trader: OFF (DEMO) ]`.
- **Click the button once.**
- It will turn **`ON`** and the status dot will glow **green**.

**That is all!** The autonomous background scanner is running. As soon as a verified high-confluence setup forms on any of the scanned pairs (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `EURUSD`, `GBPUSD`), the bot will:
1. Send an order to your Pocket Option Demo balance in sub-50ms.
2. Send an alert directly to your Telegram phone app.

---

## 3. Auto-Trader Dashboard Controls

| Element | Location | What It Does |
| :--- | :--- | :--- |
| **Status Dot** | Header Bar | Gray = Disconnected / Idle. Green = Authenticated & Active. |
| **ON / OFF Button** | Header Bar | Instant one-click killswitch. Shuts off order execution immediately. |
| **DEMO / REAL Badge** | Header Bar | Shows whether your orders are placed on practice money or real funds. |

---

## 4. Strict Risk Management & Circuit Breakers

The auto-trader contains hard-coded mathematical circuit breakers in [`app/pocket_trader.py`](app/pocket_trader.py):

* **Flat Staking ($1.00):** Every trade risks exactly **$1.00**. It never uses Martingale (it never doubles down after a loss).
* **Daily Stop-Loss (-$5.00):** If the bot loses a cumulative $5.00 in a single day, it trips the circuit breaker and stops trading until tomorrow.
* **Daily Profit Target (+$10.00):** If the bot reaches +$10.00 in profit, it locks in gains and ceases trading for the day to prevent over-trading.
* **Consecutive Loss Breaker (3 Losses):** If 3 trades lose in a row, the bot activates cooldown mode.

---

## 5. Telegram Notifications

Whenever an automated trade is placed on Pocket Option, your Telegram bot will notify you:

```
🚀 SIGNALDESK TRADING ALERT
═══════════════════════════════
Asset:         EURUSD_OTC (Pocket Option)
Timeframe:     5m
Action:        🟢 BUY (CALL)
Entry Price:   1.12540
Expiry:        5 Minutes Duration
Trend (ADX):   28.40 (Strong Trend)
═══════════════════════════════
Reason:
🤖 AUTO-EXECUTED on Pocket Option (Demo Account, $1.00).
```

---

## 6. Updating Your Session Token When It Expires

Pocket Option session cookies expire periodically (typically after 7 to 14 days of inactivity, or if you click "Log Out" in your browser).

If you see an error in the logs saying `session expired` or `connection closed`:

1. Open **[pocketoption.com](https://pocketoption.com)** in your browser and log in.
2. Press **`F12`** (Developer Tools) $\rightarrow$ **Network** $\rightarrow$ click **WS**.
3. Refresh the page (`F5`).
4. Click on `api-eu.po.market` $\rightarrow$ click **Messages**.
5. Look for `42["auth", {"session": "XXXXX", ...}]`.
6. Copy the new 32-character session ID.
7. Open your [`.env`](.env) file:
   ```env
   PO_SESSION_ID=your_new_session_id_here
   ```
8. Save the file and restart `python run.py`.

---

## 7. Switching from Demo to Real Account

> ⚠️ **Prerequisite Rule:** Do NOT switch to real money until you have completed **at least 20 demo trades** and verified a win rate above 60%.

You can switch between **Demo** and **Real** in two ways:

### Method A: One-Click Instant Switch (In Dashboard)
1. In the top navigation bar, locate the Auto-Trader pill: `[ Auto-Trader: OFF (DEMO) ]`.
2. **Click directly on the `DEMO` badge.**
3. A confirmation modal will appear reminding you of your safety limits ($1.00 stake, -$5 stop-loss, +$10 target).
4. Click **OK** to confirm.
5. The badge will instantly turn into a glowing red **`REAL`** badge. The WebSocket connection automatically re-authenticates to your real cash balance.
6. *To switch back to Demo at any time:* Simply click the **`REAL`** badge again.

### Method B: Persistent Configuration (In `.env`)
1. Open your [`.env`](.env) file.
2. Change:
   ```env
   PO_IS_DEMO=false
   ```
3. Restart `python run.py`.
4. The dashboard will now launch by default in **`REAL`** mode.
5. The bot will now place $1.00 trades on your real Pocket Option balance with the same strict daily stop-loss (-$5) and profit take-profit (+$10).

---

## 8. Summary Checklist for Every Trading Session

- [ ] Turn on your computer and open PowerShell.
- [ ] Run `python run.py`.
- [ ] Open `http://localhost:8000`.
- [ ] Confirm the **Auto-Trader** button is set to **`ON`**.
- [ ] Keep your Telegram open on your phone.
- [ ] When you are done trading for the day, toggle Auto-Trader **`OFF`** or press `Ctrl + C` in PowerShell.

