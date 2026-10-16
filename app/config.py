import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if available
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Supported Assets Catalog (21 Liquid Market Assets)
ASSET_CONFIG = {
    # --- FOREX MAJORS & CROSSES ---
    "EURUSD": {
        "name": "EUR / USD",
        "category": "forex",
        "yf_ticker": "EURUSD=X",
        "binance_symbol": None,
        "digits": 5
    },
    "GBPUSD": {
        "name": "GBP / USD",
        "category": "forex",
        "yf_ticker": "GBPUSD=X",
        "binance_symbol": None,
        "digits": 5
    },
    "USDJPY": {
        "name": "USD / JPY",
        "category": "forex",
        "yf_ticker": "USDJPY=X",
        "binance_symbol": None,
        "digits": 3
    },
    "AUDUSD": {
        "name": "AUD / USD",
        "category": "forex",
        "yf_ticker": "AUDUSD=X",
        "binance_symbol": None,
        "digits": 5
    },
    "USDCAD": {
        "name": "USD / CAD",
        "category": "forex",
        "yf_ticker": "USDCAD=X",
        "binance_symbol": None,
        "digits": 5
    },
    "USDCHF": {
        "name": "USD / CHF",
        "category": "forex",
        "yf_ticker": "USDCHF=X",
        "binance_symbol": None,
        "digits": 5
    },
    "NZDUSD": {
        "name": "NZD / USD",
        "category": "forex",
        "yf_ticker": "NZDUSD=X",
        "binance_symbol": None,
        "digits": 5
    },
    "EURJPY": {
        "name": "EUR / JPY",
        "category": "forex",
        "yf_ticker": "EURJPY=X",
        "binance_symbol": None,
        "digits": 3
    },
    "GBPJPY": {
        "name": "GBP / JPY",
        "category": "forex",
        "yf_ticker": "GBPJPY=X",
        "binance_symbol": None,
        "digits": 3
    },

    # --- CRYPTO ASSETS ---
    "BTCUSDT": {
        "name": "Bitcoin / USDT",
        "category": "crypto",
        "yf_ticker": "BTC-USD",
        "binance_symbol": "BTCUSDT",
        "digits": 2
    },
    "ETHUSDT": {
        "name": "Ethereum / USDT",
        "category": "crypto",
        "yf_ticker": "ETH-USD",
        "binance_symbol": "ETHUSDT",
        "digits": 2
    },
    "SOLUSDT": {
        "name": "Solana / USDT",
        "category": "crypto",
        "yf_ticker": "SOL-USD",
        "binance_symbol": "SOLUSDT",
        "digits": 2
    },
    "BNBUSDT": {
        "name": "BNB / USDT",
        "category": "crypto",
        "yf_ticker": "BNB-USD",
        "binance_symbol": "BNBUSDT",
        "digits": 2
    },
    "XRPUSDT": {
        "name": "XRP / USDT",
        "category": "crypto",
        "yf_ticker": "XRP-USD",
        "binance_symbol": "XRPUSDT",
        "digits": 4
    },
    "DOGEUSDT": {
        "name": "Dogecoin / USDT",
        "category": "crypto",
        "yf_ticker": "DOGE-USD",
        "binance_symbol": "DOGEUSDT",
        "digits": 5
    },
    "ADAUSDT": {
        "name": "Cardano / USDT",
        "category": "crypto",
        "yf_ticker": "ADA-USD",
        "binance_symbol": "ADAUSDT",
        "digits": 4
    },

    # --- COMMODITIES & METALS ---
    "XAUUSD": {
        "name": "Gold / USD",
        "category": "commodity",
        "yf_ticker": "GC=F",
        "binance_symbol": "PAXGUSDT",
        "digits": 2
    },
    "XAGUSD": {
        "name": "Silver / USD",
        "category": "commodity",
        "yf_ticker": "SI=F",
        "binance_symbol": None,
        "digits": 3
    },
    "USOIL": {
        "name": "Crude Oil (WTI)",
        "category": "commodity",
        "yf_ticker": "CL=F",
        "binance_symbol": None,
        "digits": 2
    },

    # --- GLOBAL INDICES ---
    "SPX": {
        "name": "S&P 500 Index",
        "category": "index",
        "yf_ticker": "ES=F",
        "binance_symbol": None,
        "digits": 2
    },
    "NDX": {
        "name": "Nasdaq 100 Index",
        "category": "index",
        "yf_ticker": "NQ=F",
        "binance_symbol": None,
        "digits": 2
    },

    # --- POCKET OPTION OTC (24/7 WEEKEND PAIRS) ---
    "EURUSD_OTC": {
        "name": "EUR / USD (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 5
    },
    "GBPUSD_OTC": {
        "name": "GBP / USD (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 5
    },
    "USDJPY_OTC": {
        "name": "USD / JPY (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 3
    },
    "AUDUSD_OTC": {
        "name": "AUD / USD (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 5
    },
    "USDCAD_OTC": {
        "name": "USD / CAD (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 5
    },
    "USDCHF_OTC": {
        "name": "USD / CHF (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 5
    },
    "NZDUSD_OTC": {
        "name": "NZD / USD (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 5
    },
    "XAUUSD_OTC": {
        "name": "Gold / USD (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 2
    },
    "BTCUSD_OTC": {
        "name": "Bitcoin / USD (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 2
    },
    "ETHUSD_OTC": {
        "name": "Ethereum / USD (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 2
    }
}

TIMEFRAME_CONFIG = {
    "1m": {
        "label": "1 Minute",
        "yf_interval": "1m",
        "binance_interval": "1m",
        "yf_period_short": "1d",
        "yf_period_long": "7d",
        "expiry_minutes": 1,
        "expiry_label": "1 Minute (Next Candle Close)"
    },
    "5m": {
        "label": "5 Minutes",
        "yf_interval": "5m",
        "binance_interval": "5m",
        "yf_period_short": "5d",
        "yf_period_long": "30d",
        "expiry_minutes": 5,
        "expiry_label": "5 Minutes (Next Candle Close)"
    },
    "15m": {
        "label": "15 Minutes",
        "yf_interval": "15m",
        "binance_interval": "15m",
        "yf_period_short": "10d",
        "yf_period_long": "60d",
        "expiry_minutes": 15,
        "expiry_label": "15 Minutes (Next Candle Close)"
    }
}

# API Keys
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "15"))
