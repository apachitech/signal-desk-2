import os
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import ASSET_CONFIG, TIMEFRAME_CONFIG
from app.data_fetcher import get_candles
from app.indicators import calculate_indicators, extract_chart_series
from app.signal_engine import analyze_signal
from app.backtester import run_full_backtest, run_all_assets_backtest

app = FastAPI(title="SignalDesk API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root & Static setup
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


class BacktestRequest(BaseModel):
    asset: str = "EURUSD"
    timeframe: str = "5m"
    threshold: float = 2.0
    ema_fast: int = 9
    ema_slow: int = 21
    ema_trend: int = 200
    rsi_period: int = 14
    stake: float = 100.0
    payout_pct: float = 0.85
    limit: int = 1000


@app.get("/api/config")
async def get_app_config():
    """Return available assets, timeframes and metadata."""
    assets = [
        {
            "id": k,
            "name": v["name"],
            "category": v["category"],
            "digits": v["digits"]
        }
        for k, v in ASSET_CONFIG.items()
    ]
    timeframes = [
        {
            "id": k,
            "label": v["label"],
            "expiry_label": v["expiry_label"],
            "minutes": v["expiry_minutes"]
        }
        for k, v in TIMEFRAME_CONFIG.items()
    ]
    return {
        "assets": assets,
        "timeframes": timeframes,
        "default_asset": "EURUSD",
        "default_timeframe": "5m"
    }


@app.get("/api/signal")
async def get_live_signal(
    asset: str = Query("EURUSD"),
    timeframe: str = Query("5m"),
    threshold: float = Query(2.0),
    force_refresh: bool = Query(False)
):
    """
    Fetch market candles, compute indicators, and return live confluence signal.
    Also returns candle & indicator series for Lightweight Charts rendering.
    """
    if asset not in ASSET_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid asset: {asset}")
    if timeframe not in TIMEFRAME_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

    try:
        # Fetch ~200-250 candles for fast real-time signal generation
        candles = await get_candles(asset, timeframe, limit=250, force_refresh=force_refresh)
        
        settings = {"threshold": threshold}
        df = calculate_indicators(candles, settings=settings)
        signal_data = analyze_signal(df, asset, timeframe, settings=settings)
        chart_series = extract_chart_series(df)

        # Prepare candle data for Lightweight Charts (last 150-200 candles)
        chart_candles = candles[-150:] if len(candles) > 150 else candles

        return {
            "success": True,
            "asset": asset,
            "timeframe": timeframe,
            "signal": signal_data,
            "candles": chart_candles,
            "indicators": chart_series,
            "timestamp": int(candles[-1]["time"]) if candles else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signal calculation error: {str(e)}")


@app.post("/api/backtest")
async def run_backtest_endpoint(req: BacktestRequest):
    """Run historical backtest over 1,000+ candles with customizable settings."""
    if req.asset not in ASSET_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid asset: {req.asset}")
    if req.timeframe not in TIMEFRAME_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe: {req.timeframe}")

    settings = {
        "threshold": req.threshold,
        "ema_fast": req.ema_fast,
        "ema_slow": req.ema_slow,
        "ema_trend": req.ema_trend,
        "rsi_period": req.rsi_period
    }

    try:
        results = await run_full_backtest(
            asset=req.asset,
            timeframe=req.timeframe,
            settings=settings,
            limit=req.limit
        )
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@app.post("/api/backtest-all")
async def run_backtest_all_assets_endpoint(req: BacktestRequest):
    """Run backtest across all assets to display win rate by asset breakdown."""
    settings = {
        "threshold": req.threshold,
        "ema_fast": req.ema_fast,
        "ema_slow": req.ema_slow,
        "ema_trend": req.ema_trend,
        "rsi_period": req.rsi_period
    }
    try:
        results = await run_all_assets_backtest(timeframe=req.timeframe, settings=settings)
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-asset backtest failed: {str(e)}")


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
elif (BASE_DIR / "public").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "public")), name="static")


@app.get("/api")
@app.get("/api/")
@app.get("/api/index.py")
@app.get("/api/index")
async def api_root():
    return {
        "status": "online",
        "service": "SignalDesk API",
        "version": "1.0.0",
        "endpoints": {
            "config": "/api/config",
            "signal": "/api/signal",
            "backtest": "/api/backtest",
            "backtest_all": "/api/backtest-all"
        }
    }


@app.get("/style.css")
async def serve_style():
    f = STATIC_DIR / "style.css"
    if not f.exists():
        f = BASE_DIR / "public" / "style.css"
    if f.exists():
        return FileResponse(str(f), media_type="text/css")
    raise HTTPException(status_code=404, detail="style.css not found")


@app.get("/app.js")
async def serve_app_js():
    f = STATIC_DIR / "app.js"
    if not f.exists():
        f = BASE_DIR / "public" / "app.js"
    if f.exists():
        return FileResponse(str(f), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        index_file = BASE_DIR / "public" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "SignalDesk Backend API Online. Please create frontend in static/."}


