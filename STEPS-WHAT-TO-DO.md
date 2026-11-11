# 📋 Step-by-Step Operations Guide: Running Your Real Quantitative Trading Bot

This document gives you the exact, step-by-step checklist to configure, test, and run your transformed **SignalDesk Quantitative Bot**—from setting up real-time phone alerts to deploying on a 24/7 server.

---

## Quick Overview of What You Have Now
- **Live Binance WebSocket Feed:** Ingests sub-100ms real market ticks for crypto and gold proxies.
- **ADX Chop Filter:** Automatically suppresses signals (`WAIT / NO TRADE`) when the market is in sideways consolidation ($\text{ADX} < 22$).
- **Multi-Indicator Confluence:** Emits verified `BUY` or `SELL` entries only when EMA alignment, RSI momentum, and directional indices align.
- **Telegram Notification Bot:** Dispatches formatted trade alert cards straight to your smartphone.

---

## Step 1: Set Up Telegram Alerts on Your Phone (5 Minutes)

You can receive instant sound alerts on your phone whenever a verified signal fires on candle close.

### 1.1 Create Your Telegram Bot
1. Open the **Telegram** app on your phone or computer.
2. Search for `@BotFather` (verified account with blue checkmark) and press **Start**.
3. Send the command:
   ```text
   /newbot
   ```
4. Follow the prompts:
   - Give your bot a name (e.g. `MySignalDeskBot`).
   - Give your bot a username ending in `bot` (e.g. `mysignaldesk_trading_bot`).
5. BotFather will provide an **HTTP API Token** that looks like this:
   ```text
   789123456:ABCdefGhIJKlmNoPQRstuVWXyz123456789
   ```
   **Copy this token.**

### 1.2 Get Your Personal Chat ID
1. In Telegram, search for `@userinfobot` and click **Start**.
2. It will reply immediately with your account information, including your **Id** (a 9 or 10-digit number like `123456789`).
3. **Copy your Id.**
4. Send a message like `/start` or `hello` to your new bot (so Telegram allows the bot to message you).

### 1.3 Add Them to Your `.env` File
In your `signal-desk-2` folder, open `.env` in Notepad or your editor and enter your credentials:
```env
# Telegram Live Alert Bot
TELEGRAM_BOT_TOKEN=789123456:ABCdefGhIJKlmNoPQRstuVWXyz123456789
TELEGRAM_CHAT_ID=123456789

# Quantitative Engine Settings
MIN_ADX_THRESHOLD=22.0
```
Save the file.

---

## Step 2: Test the Bot Locally on Your Computer

### 2.1 Install / Verify Python Dependencies
Open PowerShell or your terminal inside `c:\Users\XPRISTO\Desktop\signal-desk-2`:
```powershell
pip install -r requirements.txt
```

### 2.2 Start the Server
Run the startup script:
```powershell
python run.py
```
You should see:
```text
INFO:     Started server process
INFO:     Connecting to Binance Stream: 7 assets...
INFO:     Binance WebSocket stream established successfully.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 2.3 Verify in Your Browser
1. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).
2. Look at the **ADX (Chop/Trend)** cell in the Technical Values grid:
   - When $\text{ADX} < 22$, the signal badge will display **`WAIT`** with the message:
     *"Chop Filter Active: Market in sideways consolidation with no directional edge. Capital preserved."*
   - When $\text{ADX} \ge 22$ and EMAs align, the badge triggers **`BUY`** or **`SELL`**.

### 2.4 Test the Telegram Notification
Open a second terminal window and test your Telegram connection:
```powershell
curl -X POST http://127.0.0.1:8000/api/telegram/test
```
Check your phone! You will receive a sample HTML signal card with entry zone, ADX score, and expiry details.

---

## Step 3: Deploy to a 24/7 VPS (So It Runs While You Sleep)

Because serverless platforms like Vercel put background processes to sleep after 10–15 seconds, a continuous trading bot should run on a low-cost Virtual Private Server ($4 to $6/month).

### Recommended VPS Providers:
- **DigitalOcean** (Basic Droplet: $4–$6/mo)
- **Hetzner Cloud** (CX22: ~$4.50/mo — excellent European latency)
- **AWS Lightsail** ($3.50–$5/mo)

### 3.1 Setup on Ubuntu Linux (One-Time Setup):
SSH into your VPS server:
```bash
# 1. Update system and install Python & Docker
sudo apt update && sudo apt install -y python3-pip git docker.io docker-compose

# 2. Clone your repository
git clone https://github.com/apachitech/signal-desk-2.git
cd signal-desk-2

# 3. Create your production .env file
nano .env
# (Paste your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID, then press Ctrl+O, Enter, Ctrl+X)
```

### 3.2 Run with Docker (Recommended):
```bash
# Build and run in the background (detached mode)
docker-compose up -d --build
```
Your bot is now running 24/7 with auto-restart! It will keep WebSockets connected, monitor market confluence continuously, and push alerts to your phone.

To check live logs at any time:
```bash
docker-compose logs -f
```

---

## Step 4: Connecting Automated Execution (Optional)

If you want the bot to automatically open trades on your broker account instead of sending alerts:

### Choice A: Forex & Metals (Gold) $\rightarrow$ MetaTrader 5 (MT5)
1. Install **MetaTrader 5** on a Windows PC or Windows VPS.
2. In your Python environment, install:
   ```bash
   pip install MetaTrader5
   ```
3. Use the code blueprint in `TRANSFORMATION-REAL-BOT.md` (Section 5.2) to send market orders directly to your broker when a signal triggers.

### Choice B: Crypto (Bitcoin / Ethereum / Solana) $\rightarrow$ Binance / Bybit
1. Generate an API Key with "Trade" permissions from your Binance or Bybit account.
2. Install CCXT:
   ```bash
   pip install ccxt
   ```
3. The engine will place market or limit orders automatically.

### Choice C: Pocket Option / Binary Options
1. Pocket Option does not provide an official public trade execution API.
2. Traders automate Pocket Option through:
   - **Chrome Extension automation** or **Playwright script** (clicks the Call/Put button in the web terminal upon receiving the signal).
   - Alternatively, use **Deriv.com** which provides an official, documented binary options API (`deriv-api`).

---

## Step 5: Safe Demo Testing Checklist (Before Real Capital)

Follow this golden rule of quantitative trading: **Never risk real capital until a system has proven itself in forward-testing.**

| Test Stage | Requirement | Goal |
| :--- | :--- | :--- |
| **Stage 1: Connection Test** | Run WebSocket feed for 2 hours | 0 disconnects; ticks arrive in $< 100\text{ ms}$. |
| **Stage 2: Chop Filter Verification** | Observe during a slow Asian/sideways session | Confirm the bot correctly stays on **`WAIT`** rather than overtrading. |
| **Stage 3: 50-Trade Demo Forward Test** | Take the first 50 verified signals on a **Demo Account** | Calculate actual win rate: $\text{Wins} / 50$. |
| **Stage 4: Edge Validation** | In binary options (85% payout) | Win rate must be $\ge 56\%$ to be profitable. |
| **Stage 5: Risk Rules** | Fixed Stake | Never risk more than **1% to 2%** of account balance per position. |

---

## Summary Command Reference

| Action | Command |
| :--- | :--- |
| Start bot locally | `python run.py` |
| Test Telegram notification | `curl -X POST http://127.0.0.1:8000/api/telegram/test` |
| Check Bot & Feed Status | Open [http://127.0.0.1:8000/api/bot/status](http://127.0.0.1:8000/api/bot/status) |
| Check Docker container logs | `docker-compose logs -f` |
| Stop Docker bot | `docker-compose down` |

