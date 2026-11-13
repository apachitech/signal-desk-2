# Market Data API Keys: How & Where to Get Them for Free

> **Quick Note:** These API keys are **completely optional**. SignalDesk already connects to Binance Public REST/WebSocket feeds and Yahoo Finance out of the box with **zero keys**. However, adding a free **Twelve Data** key gives you enhanced, institutional-grade Forex data (EUR/USD, GBP/USD, USD/JPY) and Gold prices.

---

## 1. Twelve Data API Key (`TWELVE_DATA_API_KEY`)

**Best For:** Real-time Forex pairs (EUR/USD, GBP/USD, USD/JPY, AUD/USD), Gold (XAU/USD), and Crypto.

### Step-by-Step Registration (100% Free, No Credit Card):
1. Navigate to the official website: [https://twelvedata.com/](https://twelvedata.com/)
2. Click **"Get Started"** or **"Sign Up"** in the top-right corner.
3. Fill in your name, email, and password.
4. Verify your email if prompted.
5. Once logged in, go to your **API Keys** management dashboard:
   👉 [https://twelvedata.com/account/api-keys](https://twelvedata.com/account/api-keys)
6. Copy the alphanumeric key (e.g., `a1b2c3d4e5f678901234567890abcdef`).
7. Open your [`.env`](.env) file in the root of the project and paste it:
   ```env
   TWELVE_DATA_API_KEY=your_twelve_data_key_here
   ```

### Free Tier Specifications:
- **Rate Limit:** 8 API credits per minute.
- **Daily Limit:** 800 credits per day.
- **SignalDesk Optimization:** SignalDesk has built-in smart caching (`CACHE_TTL_SECONDS`), so it only calls Twelve Data when new candle closes form. You will almost never hit this limit during normal trading sessions.

---

## 2. Alpha Vantage API Key (`ALPHA_VANTAGE_API_KEY`)

**Best For:** Secondary backup for global Forex, Commodities, Indices, and Equities.

### Step-by-Step Registration (Instant, No Password Needed):
1. Go directly to the official free key generator:
   👉 [https://www.alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)
2. Fill out the 3 fields:
   - **What best describes you?**: Select *Investor* or *Software Developer*.
   - **Organization**: Type *Personal* or your name.
   - **Email**: Enter your email address.
3. Click the blue button: **"GET FREE API KEY"**.
4. The key will display immediately right on your screen (no waiting for confirmation emails).
5. Copy the key and paste it into your [`.env`](.env) file:
   ```env
   ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
   ```

### Free Tier Specifications:
- **Daily Limit:** 25 requests per day.
- **Role in SignalDesk:** Acts as a tertiary failover provider if Twelve Data and primary feeds are unreachable.

---

## 3. Summary of How SignalDesk Selects Market Data

SignalDesk uses a prioritized fallback waterfall architecture:

```
1. Binance WebSocket Feed (Sub-100ms real ticks for Crypto)
      │ (If Forex or Crypto WS fails)
      ▼
2. Twelve Data API (High accuracy Forex & Gold candles)
      │ (If Twelve Data empty / exhausted)
      ▼
3. Binance Public REST API (Crypto without any API keys)
      │ (If unreachable)
      ▼
4. Yahoo Finance (yfinance - Free global quotes)
      │ (If rate-limited)
      ▼
5. Alpha Vantage API (Emergency fallback)
```

With just **Twelve Data** added, you have high-precision market data across both Forex and Crypto with zero monthly expenses.

