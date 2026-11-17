import asyncio
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
from app.signal_engine import analyze_signal, validate_sniper_precision
from app.backtester import run_full_backtest, run_all_assets_backtest
from app.live_feed import start_live_feeds
from app.telegram_bot import telegram_bot
from app.pocket_trader import pocket_trader

app = FastAPI(title="SignalDesk Quantitative Bot API", version="2.0.0")

# Track sent alerts: asset_timeframe -> last_candle_time
_SENT_ALERTS: Dict[str, int] = {}
_SCANNER_TASK: Optional[asyncio.Task] = None


async def background_market_scanner():
    """
    Continuous background autonomous scanner.
    Iterates over key high-liquidity assets every 15 seconds.
    When a genuine BUY or SELL signal forms, dispatches it to Telegram immediately
    without needing any user to be clicking on the website.
    """
    scan_assets = [
        "EURUSD_OTC",  # ~92% High Payout OTC
        "GBPUSD_OTC",  # ~90-92% High Payout OTC
        "USDJPY_OTC",  # ~86-88% High Payout OTC
        "XAUUSD_OTC",  # ~88% Gold OTC
        "BTCUSDT"      # Top Volume Crypto 24/7
    ]
    scan_timeframes = ["1m", "5m"]
    await asyncio.sleep(5)  # Let feeds warm up
    print("[*] Autonomous Background Market Scanner started! Scanning for trade confluence...")

    while True:
        try:
            for asset in scan_assets:
                for tf in scan_timeframes:
                    try:
                        candles = await get_candles(asset, tf, limit=150, force_refresh=False)
                        if not candles or len(candles) < 30:
                            continue

                        df = calculate_indicators(candles, settings={"threshold": 2.0})
                        sig = analyze_signal(df, asset, tf, settings={"threshold": 2.0})
                        action = sig.get("action")
                        last_candle_time = int(candles[-1]["time"])
                        alert_key = f"{asset}:{tf}"

                        if action in ["BUY", "SELL"]:
                            # 1. Automatic Telegram Signal Dispatch
                            if telegram_bot.enabled and _SENT_ALERTS.get(alert_key) != last_candle_time:
                                _SENT_ALERTS[alert_key] = last_candle_time
                                entry_info = sig.get("entry", {})
                                await telegram_bot.send_signal(
                                    asset=asset,
                                    timeframe=tf,
                                    action=action,
                                    entry_price=entry_info.get("entry_price", sig.get("latest_price", 0.0)),
                                    optimal_zone=entry_info.get("optimal_zone", "--"),
                                    adx=float(sig.get("indicators", {}).get("adx", 20.0)),
                                    reason=sig.get("reason", ""),
                                    expiry_label=sig.get("expiry_label", f"{tf} Expiry")
                                )

                            # 2. Automated Pocket Option Execution (Across all enabled accounts in parallel)
                            if pocket_trader.enabled and _SENT_ALERTS.get(alert_key + ":po_trade") != last_candle_time:
                                # ================= SNIPER PRECISION GATE =================
                                # Priority #1: Accuracy, Precision & High-Probability Expectancy
                                if pocket_trader.sniper_precision_mode:
                                    mtf_tf = "5m" if tf == "1m" else "15m"
                                    try:
                                        mtf_candles = await get_candles(asset, mtf_tf, limit=60, force_refresh=False)
                                        mtf_df = calculate_indicators(mtf_candles, settings={"threshold": 2.0}) if mtf_candles else None
                                    except Exception:
                                        mtf_df = None

                                    is_sniper_safe, sniper_reason = validate_sniper_precision(
                                        df=df,
                                        sig=sig,
                                        mtf_df=mtf_df,
                                        min_confidence=pocket_trader.min_confidence
                                    )
                                    if not is_sniper_safe:
                                        print(f"[🎯 Sniper Guard] Auto-trade bypassed on {asset} ({tf}): {sniper_reason}")
                                        continue

                                expiry_sec = 60 if tf == "1m" else 300
                                trade_results = await pocket_trader.open_trade_all(
                                    asset=asset,
                                    action=action,
                                    expiry_seconds=expiry_sec
                                )
                                successful = [r for r in trade_results if r.get("success")]
                                if successful:
                                    _SENT_ALERTS[alert_key + ":po_trade"] = last_candle_time
                                    summary_lines = []
                                    for r in successful:
                                        summary_lines.append(f"• {r.get('account_name', 'Account')}: ${r.get('amount', 1.0):.2f}")
                                    conf_val = sig.get('confidence', 80)
                                    print(f"[🎯] SNIPER AUTO-TRADE EXECUTED on {len(successful)} account(s): {action} on {asset} ({conf_val}% Confluence)")
                                    if telegram_bot.enabled:
                                        await telegram_bot.send_signal(
                                            asset=asset,
                                            timeframe=tf,
                                            action=action,
                                            entry_price=sig.get("latest_price", 0.0),
                                            optimal_zone="--",
                                            adx=float(sig.get("indicators", {}).get("adx", 20.0)),
                                            reason=f"🎯 SNIPER AUTO-EXECUTED on {len(successful)} Account(s) ({conf_val}% Confidence):\n" + "\n".join(summary_lines),
                                            expiry_label=f"{tf} Duration"
                                        )
                                else:
                                    fail_reasons = [f"{r.get('account_name', 'Acc')}: {r.get('reason', 'Blocked')}" for r in trade_results]
                                    combined_reasons = "; ".join(fail_reasons)
                                    print(f"[!] AUTO-TRADE BLOCKED on {asset}: {combined_reasons}")
                                    if telegram_bot.enabled and not any("Pacing Cooldown" in r.get("reason", "") for r in trade_results):
                                        await telegram_bot.send_signal(
                                            asset=asset,
                                            timeframe=tf,
                                            action="WAIT",
                                            entry_price=sig.get("latest_price", 0.0),
                                            optimal_zone="--",
                                            adx=float(sig.get("indicators", {}).get("adx", 20.0)),
                                            reason=f"⚠️ AUTO-TRADE SKIPPED:\n" + "\n".join(fail_reasons),
                                            expiry_label="Risk Guard Active"
                                        )
                    except Exception as scan_err:
                        pass
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            pass
        await asyncio.sleep(15)


@app.on_event("startup")
async def on_startup():
    """Start persistent real-time WebSocket tick ingestion and autonomous scanner."""
    global _SCANNER_TASK
    try:
        await start_live_feeds()
    except Exception as e:
        print(f"Warning: could not start background WebSocket feeds: {e}")

    try:
        await pocket_trader.connect_all()
    except Exception as e:
        print(f"Warning: could not connect Pocket Option trading accounts: {e}")

    try:
        _SCANNER_TASK = asyncio.create_task(background_market_scanner())
    except Exception as e:
        print(f"Warning: could not start background scanner: {e}")

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


@app.get("/api/health")
async def health_check():
    """Lightweight ping endpoint for UptimeRobot / ping monitors to keep Render awake 24/7."""
    return {
        "status": "online",
        "autotrade_enabled": pocket_trader.enabled,
        "is_demo": pocket_trader.is_demo
    }


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
        last_candle_time = int(candles[-1]["time"]) if candles else 0

        # Automatic Telegram Signal Dispatch (Only once per candle for verified BUY / SELL)
        action = signal_data.get("action")
        alert_key = f"{asset}:{timeframe}"
        if action in ["BUY", "SELL"] and telegram_bot.enabled:
            if _SENT_ALERTS.get(alert_key) != last_candle_time:
                _SENT_ALERTS[alert_key] = last_candle_time
                entry_info = signal_data.get("entry", {})
                await telegram_bot.send_signal(
                    asset=asset,
                    timeframe=timeframe,
                    action=action,
                    entry_price=entry_info.get("entry_price", signal_data.get("latest_price", 0.0)),
                    optimal_zone=entry_info.get("optimal_zone", "--"),
                    adx=float(signal_data.get("indicators", {}).get("adx", 20.0)),
                    reason=signal_data.get("reason", ""),
                    expiry_label=signal_data.get("expiry_label", f"{timeframe} Expiry")
                )

        return {
            "success": True,
            "asset": asset,
            "timeframe": timeframe,
            "signal": signal_data,
            "candles": chart_candles,
            "indicators": chart_series,
            "timestamp": last_candle_time
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


@app.get("/api/bot/status")
async def get_bot_status():
    """Returns live quantitative bot status, feeds, and alert integrations."""
    from app.live_feed import _WS_CANDLE_BUFFER
    return {
        "status": "online",
        "engine": "Quantitative Confluence + ADX Chop Filter",
        "chop_filter_threshold": 22.0,
        "websocket_feed": {
            "active_streams": list(_WS_CANDLE_BUFFER.keys()),
            "total_buffers": len(_WS_CANDLE_BUFFER)
        },
        "telegram_integration": {
            "configured": telegram_bot.enabled,
            "chat_id_set": bool(telegram_bot.chat_id)
        }
    }


@app.get("/api/autotrade/status")
async def get_autotrade_status():
    """Returns real-time status of the Pocket Option automated trading engine."""
    pocket_trader.clean_expired_deals()
    return {
        "enabled": pocket_trader.enabled,
        "is_demo": pocket_trader.is_demo,
        "stake_amount": pocket_trader.stake_amount,
        "max_daily_loss": pocket_trader.max_daily_loss,
        "max_daily_profit": pocket_trader.max_daily_profit,
        "max_consecutive_losses": pocket_trader.max_consecutive_losses,
        "max_concurrent_trades": pocket_trader.max_concurrent_trades,
        "trade_cooldown_seconds": pocket_trader.trade_cooldown_seconds,
        "active_deals_count": len(pocket_trader.active_deals),
        "sniper_precision": {
            "active": pocket_trader.sniper_precision_mode,
            "min_confidence": pocket_trader.min_confidence,
            "mtf_alignment": True,
            "anti_exhaustion": True,
            "candle_momentum": True
        },
        "session_stats": {
            "daily_pnl": pocket_trader.daily_pnl,
            "total_trades": pocket_trader.total_trades_today,
            "wins": pocket_trader.wins_today,
            "losses": pocket_trader.losses_today,
            "consecutive_losses": pocket_trader.consecutive_losses,
            "circuit_broken": pocket_trader.circuit_broken,
            "circuit_reason": pocket_trader.circuit_reason
        },
        "connection": {
            "has_credentials": bool(pocket_trader.session_id and pocket_trader.uid),
            "uid": pocket_trader.uid,
            "session_prefix": (pocket_trader.session_id[:6] + "...") if pocket_trader.session_id else "None",
            "connected": pocket_trader.connected,
            "auth_error": pocket_trader.auth_error,
            "last_trade_status": pocket_trader.last_trade_status
        }
    }


@app.get("/api/autotrade/test-connect")
async def test_autotrade_connection():
    """Live verification of Pocket Option WebSocket authentication."""
    pocket_trader.connected = False
    ok = await pocket_trader.connect()
    return {
        "connected": ok,
        "is_demo": pocket_trader.is_demo,
        "gateway": pocket_trader.ws_url,
        "session_prefix": (pocket_trader.session_id[:6] + "...") if pocket_trader.session_id else "None",
        "auth_error": pocket_trader.auth_error,
        "last_trade_status": pocket_trader.last_trade_status
    }


class AutoTradeConfigRequest(BaseModel):
    enabled: bool
    is_demo: bool = True
    stake_amount: float = 1.0
    sniper_precision_mode: Optional[bool] = None
    min_confidence: Optional[int] = None


@app.post("/api/autotrade/config")
async def update_autotrade_config(cfg: AutoTradeConfigRequest):
    """Update auto-trading toggle, mode, and stake live from the frontend dashboard."""
    pocket_trader.enabled = cfg.enabled
    if pocket_trader.is_demo != cfg.is_demo:
        await pocket_trader.set_demo_mode(cfg.is_demo)
    pocket_trader.stake_amount = max(1.0, cfg.stake_amount)
    if cfg.sniper_precision_mode is not None:
        pocket_trader.sniper_precision_mode = cfg.sniper_precision_mode
    if cfg.min_confidence is not None:
        pocket_trader.min_confidence = max(70, min(95, cfg.min_confidence))
    return {
        "success": True,
        "enabled": pocket_trader.enabled,
        "is_demo": pocket_trader.is_demo,
        "stake_amount": pocket_trader.stake_amount,
        "sniper_precision_mode": pocket_trader.sniper_precision_mode,
        "min_confidence": pocket_trader.min_confidence,
        "message": f"Auto-trading {'ENABLED' if pocket_trader.enabled else 'DISABLED'} (Mode: {'DEMO' if pocket_trader.is_demo else 'REAL'}, Stake: ${pocket_trader.stake_amount:.2f}, Sniper: {pocket_trader.min_confidence}%+)"
    }


# ================= Multi-Account Copy-Trading API Endpoints =================

@app.get("/api/autotrade/accounts")
async def get_autotrade_accounts():
    """Returns all configured trading accounts, their connection statuses and session stats."""
    pocket_trader.clean_expired_deals()
    return {
        "master_enabled": pocket_trader.enabled,
        "total_accounts": len(pocket_trader.accounts),
        "active_accounts": len([a for a in pocket_trader.accounts.values() if a.enabled]),
        "accounts": pocket_trader.get_accounts_list()
    }


class AccountCreateRequest(BaseModel):
    name: str
    uid: int
    session_id: str
    is_demo: bool = True
    stake_amount: float = 1.0
    max_daily_loss: float = 5.0
    max_daily_profit: float = 10.0
    max_consecutive_losses: int = 3
    max_concurrent_trades: int = 2
    trade_cooldown_seconds: float = 30.0
    enabled: bool = True


@app.post("/api/autotrade/accounts")
async def create_autotrade_account(data: AccountCreateRequest):
    """Add a new trading account to the multi-account manager."""
    acc = pocket_trader.add_account(data.dict())
    asyncio.create_task(acc.connect())
    return {
        "success": True,
        "account": acc.to_dict(mask_session=True),
        "message": f"Account '{acc.name}' registered successfully."
    }


class AccountUpdateRequest(BaseModel):
    name: Optional[str] = None
    uid: Optional[int] = None
    session_id: Optional[str] = None
    is_demo: Optional[bool] = None
    stake_amount: Optional[float] = None
    max_daily_loss: Optional[float] = None
    max_daily_profit: Optional[float] = None
    max_consecutive_losses: Optional[int] = None
    max_concurrent_trades: Optional[int] = None
    trade_cooldown_seconds: Optional[float] = None
    enabled: Optional[bool] = None


@app.put("/api/autotrade/accounts/{acc_id}")
async def update_autotrade_account(acc_id: str, data: AccountUpdateRequest):
    """Update settings for an existing account."""
    acc = pocket_trader.update_account(acc_id, {k: v for k, v in data.dict().items() if v is not None})
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return {
        "success": True,
        "account": acc.to_dict(mask_session=True),
        "message": f"Account '{acc.name}' updated."
    }


@app.delete("/api/autotrade/accounts/{acc_id}")
async def delete_autotrade_account(acc_id: str):
    """Remove a trading account."""
    if acc_id == "acc_primary" and len(pocket_trader.accounts) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the sole primary account.")
    deleted = pocket_trader.delete_account(acc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"success": True, "message": "Account removed."}


@app.post("/api/autotrade/accounts/{acc_id}/test-connect")
async def test_account_connection(acc_id: str):
    """Test connection for a specific account."""
    acc = pocket_trader.accounts.get(acc_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    acc.connected = False
    ok = await acc.connect()
    return {
        "success": ok,
        "account_id": acc.id,
        "account_name": acc.name,
        "connected": ok,
        "is_demo": acc.is_demo,
        "gateway": acc.ws_url,
        "auth_error": acc.auth_error
    }


@app.post("/api/autotrade/accounts/{acc_id}/toggle")
async def toggle_account(acc_id: str):
    """Toggle enabled/disabled state for a specific account."""
    acc = pocket_trader.accounts.get(acc_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    acc.enabled = not acc.enabled
    pocket_trader.save_accounts()
    if acc.enabled and not acc.connected:
        asyncio.create_task(acc.connect())
    return {
        "success": True,
        "account_id": acc.id,
        "enabled": acc.enabled,
        "message": f"Account '{acc.name}' is now {'ENABLED' if acc.enabled else 'DISABLED'}."
    }


@app.api_route("/api/telegram/test", methods=["GET", "POST"])
async def test_telegram_alert():
    """Dispatches a test verification alert to Telegram (supports GET and POST)."""
    if not telegram_bot.enabled:
        return {
            "success": False,
            "message": "Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file."
        }
    sent = await telegram_bot.send_signal(
        asset="BTCUSDT",
        timeframe="5m",
        action="BUY",
        entry_price=84500.0,
        optimal_zone="84480.0 - 84520.0",
        adx=31.5,
        reason="Test Alert: Quantitative Engine Confluence (ADX 31.5 + EMA 9/21 Dynamic Pullback).",
        expiry_label="5 Minutes Expiry"
    )
    return {
        "success": sent,
        "message": "Test alert sent successfully to Telegram." if sent else "Failed to send alert to Telegram."
    }


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
elif (BASE_DIR / "public").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "public")), name="static")


@app.get("/api")
@app.get("/api/")
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


@app.api_route("/", methods=["GET", "HEAD"])
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        index_file = BASE_DIR / "public" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "SignalDesk Backend API Online. Please create frontend in static/."}


