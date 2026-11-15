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
    "EURGBP": {
        "name": "EUR / GBP",
        "category": "forex",
        "yf_ticker": "EURGBP=X",
        "binance_symbol": None,
        "digits": 5
    },
    "EURCAD": {
        "name": "EUR / CAD",
        "category": "forex",
        "yf_ticker": "EURCAD=X",
        "binance_symbol": None,
        "digits": 5
    },
    "EURAUD": {
        "name": "EUR / AUD",
        "category": "forex",
        "yf_ticker": "EURAUD=X",
        "binance_symbol": None,
        "digits": 5
    },
    "GBPAUD": {
        "name": "GBP / AUD",
        "category": "forex",
        "yf_ticker": "GBPAUD=X",
        "binance_symbol": None,
        "digits": 5
    },
    "AUDJPY": {
        "name": "AUD / JPY",
        "category": "forex",
        "yf_ticker": "AUDJPY=X",
        "binance_symbol": None,
        "digits": 3
    },
    "CADJPY": {
        "name": "CAD / JPY",
        "category": "forex",
        "yf_ticker": "CADJPY=X",
        "binance_symbol": None,
        "digits": 3
    },
    "CHFJPY": {
        "name": "CHF / JPY",
        "category": "forex",
        "yf_ticker": "CHFJPY=X",
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
    "AVAXUSDT": {
        "name": "Avalanche / USDT",
        "category": "crypto",
        "yf_ticker": "AVAX-USD",
        "binance_symbol": "AVAXUSDT",
        "digits": 3
    },
    "LINKUSDT": {
        "name": "Chainlink / USDT",
        "category": "crypto",
        "yf_ticker": "LINK-USD",
        "binance_symbol": "LINKUSDT",
        "digits": 3
    },
    "SUIUSDT": {
        "name": "Sui / USDT",
        "category": "crypto",
        "yf_ticker": "SUI-USD",
        "binance_symbol": "SUIUSDT",
        "digits": 4
    },
    "DOTUSDT": {
        "name": "Polkadot / USDT",
        "category": "crypto",
        "yf_ticker": "DOT-USD",
        "binance_symbol": "DOTUSDT",
        "digits": 4
    },
    "NEARUSDT": {
        "name": "NEAR Protocol / USDT",
        "category": "crypto",
        "yf_ticker": "NEAR-USD",
        "binance_symbol": "NEARUSDT",
        "digits": 3
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
    "NATGAS": {
        "name": "Natural Gas",
        "category": "commodity",
        "yf_ticker": "NG=F",
        "binance_symbol": None,
        "digits": 3
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
    "GER40": {
        "name": "German DAX 40",
        "category": "index",
        "yf_ticker": "DAX",
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
    },
    "EURGBP_OTC": {
        "name": "EUR / GBP (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 5
    },
    "AUDJPY_OTC": {
        "name": "AUD / JPY (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 3
    },
    "GBPJPY_OTC": {
        "name": "GBP / JPY (OTC 24/7)",
        "category": "otc",
        "yf_ticker": None,
        "binance_symbol": None,
        "digits": 3
    },
    "SOLUSD_OTC": {
        "name": "Solana / USD (OTC 24/7)",
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

# API Keys & Bot Config
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "15"))

# Telegram Live Alert Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Quantitative Engine Settings
MIN_ADX_THRESHOLD = float(os.getenv("MIN_ADX_THRESHOLD", "22.0"))
