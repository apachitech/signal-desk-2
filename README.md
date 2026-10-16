# ⚡ SignalDesk — Institutional Confluence Trading Engine

SignalDesk is a fast, probabilistic trading assistant that analyzes real-time market data across **Forex, Crypto, and Gold** to generate actionable **BUY / SELL / WAIT** confluence signals with suggested expiry times, confidence scoring, historical backtesting (assuming 85% fixed-expiry payout), and capital risk management tools.

---

## 🌟 Key Features

### 1. Confluence Signal Engine
Signals are only triggered when multiple independent technical indicators agree:
- **Trend Confluence (Weight: 1.2)**: Fast EMA 9 vs Slow EMA 21 alignment combined with macro trend filter (Price vs EMA 200).
- **Momentum Confluence (Weight: 1.3)**: MACD line vs Signal line with expanding histogram direction, plus RSI(14) expansion without being overbought (>70) or oversold (<30).
- **Volatility & Bands (Weight: 0.8)**: Bollinger Bands (20, 2) touches/rejections with RSI confirmation.
- **Support & Resistance Protection (Weight: -1.2 penalty)**: Detects recent 20-period swing highs and swing lows to avoid buying directly into a ceiling or selling into a floor.
- **Flat Market & Conflict Guard**: Automatically returns **WAIT** during flat compression (low ATR / BB width squeeze) or when indicators oppose each other (e.g. Trend is bullish but Momentum is collapsing).

### 2. Supported Assets & Timeframes (31 Total Assets)
- **Pocket Option 24/7 OTC Pairs (10 pairs for Weekend & Night trading)**:
  - `EURUSD_OTC`, `GBPUSD_OTC`, `USDJPY_OTC`, `AUDUSD_OTC`, `USDCAD_OTC`, `USDCHF_OTC`, `NZDUSD_OTC`, `XAUUSD_OTC` (Gold OTC), `BTCUSD_OTC` (Bitcoin OTC), `ETHUSD_OTC` (Ethereum OTC)
- **Forex Majors & Crosses (9 pairs)**: `EURUSD`, `GBPUSD`, `USDJPY`, `AUDUSD`, `USDCAD`, `USDCHF`, `NZDUSD`, `EURJPY`, `GBPJPY`
- **Crypto Assets (7 pairs via Binance Live)**: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, `XRPUSDT`, `DOGEUSDT`, `ADAUSDT`
- **Precious Metals & Commodities (3 assets)**: `XAUUSD` (Gold), `XAGUSD` (Silver), `USOIL` (Crude Oil WTI)
- **Global Stock Indices (2 assets)**: `SPX` (S&P 500 Index), `NDX` (Nasdaq 100 Index)
- **Timeframes**: `1m`, `5m`, `15m` with matching suggested expiry rule.

### 3. Integrated TradingView Lightweight Charts
- Interactive candlestick chart with EMA 9, EMA 21, EMA 200, and Bollinger Bands overlays.
- Dynamic arrow markers indicating BUY and SELL confluence entries.

### 4. Confluence Backtester
- Runs the exact signal logic over 1,000+ historical candles.
- Computes Total Signals, Win Rate %, Loss Rate %, Expected Net Profit ($), Profit Factor, and Max Consecutive Losses assuming standard 85% fixed-expiry binary payout.
- **Profitability Warning**: Flags any strategy below 56.0% win rate (since 54.1% is the mathematical breakeven at 85% payout).
- **Interactive Parameter Tweaks**: Adjust signal threshold (1.4 - 3.2), EMA lengths, and RSI period in real time.
- **Compare All 7 Assets**: One-click scan across all pairs to identify highest edge assets.

### 5. Risk Management & Trade Journal
- **Fixed-Stake Calculator**: Computes exact position size based on 1-2% account balance risk.
- **Daily Loss Circuit Breaker**: Tracks consecutive losses and daily drawdown percentage, displaying a bold warning banner to step away if limits are breached.
- **Trade Journal**: LocalStorage-persisted trading log with one-click signal recording, realized P&L calculation, and CSV export.

### 6. Auto-Refresh & Audio Chimes
- Wall-clock synchronized countdown to next candle close.
- Web Audio API synthesizer chime (major arpeggio for BUY, descending minor chime for SELL).

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Modern web browser (Chrome, Edge, Firefox, Safari)

### Installation

1. Open a terminal in the project directory:
   ```bash
   cd c:\Users\XPRISTO\Desktop\signal-desk-2
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Configure API keys in `.env`:
   ```bash
   # Copy sample environment configuration
   cp .env.example .env
   ```
   *Note: Binance public crypto API and yfinance work out of the box with zero keys required.*

4. Launch the application:
   ```bash
   python run.py
   ```
   *Or via uvicorn directly:*
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. Open your browser and navigate to:
   ```
   http://127.0.0.1:8000
   ```

---

## 📁 Project Structure

```
signal-desk-2/
├── app/
│   ├── __init__.py
│   ├── config.py           # Asset definitions, timeframes, and .env loading
│   ├── data_fetcher.py     # Binance API, yfinance, TwelveData, and caching
│   ├── indicators.py       # Pure pandas vector indicators (EMA, RSI, MACD, BB, ATR)
│   ├── signal_engine.py    # Confluence scoring, conflict detection, confidence rating
│   ├── backtester.py       # Historical 1000-candle simulation with 85% payout math
│   └── main.py             # FastAPI REST endpoints and static file server
├── static/
│   ├── index.html          # High-performance trading terminal UI
│   ├── style.css           # Bloomberg/TradingView dark theme & micro-animations
│   └── app.js              # Lightweight Charts, audio alerts, backtester & risk logic
├── .env.example            # Environment template
├── requirements.txt        # Python package dependencies
├── run.py                  # Entrypoint runner script
└── README.md               # Documentation
```

---

## ⚖️ Legal & Risk Disclaimer
Signals are probabilistic, not guaranteed. Trading involves substantial risk of loss. Past performance does not guarantee future results.
