from typing import Dict, Any, List, Optional
import pandas as pd
from app.indicators import calculate_indicators
from app.signal_engine import analyze_signal
from app.data_fetcher import get_candles
from app.config import ASSET_CONFIG, TIMEFRAME_CONFIG


def run_backtest_on_dataframe(
    df: pd.DataFrame,
    asset: str,
    timeframe: str,
    settings: Dict[str, Any] = None,
    expiry_bars: int = 1,
    stake: float = 100.0,
    payout_pct: float = 0.85
) -> Dict[str, Any]:
    """
    Simulates signal engine over historical candle series.
    Evaluates each candle against signal confluence rules and tracks outcome
    at candle close after `expiry_bars` (default 1 bar = matching timeframe expiry).
    """
    if settings is None:
        settings = {}

    threshold = float(settings.get("threshold", 2.0))
    tf_conf = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["5m"])
    digits = ASSET_CONFIG.get(asset, {}).get("digits", 4)

    total_candles = len(df)
    if total_candles < 60:
        return {
            "asset": asset,
            "timeframe": timeframe,
            "candles_analyzed": total_candles,
            "total_signals": 0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "expected_profit": 0.0,
            "roi_pct": 0.0,
            "profit_factor": 0.0,
            "max_consecutive_losses": 0,
            "trades": [],
            "warning": "Not enough candles to backtest."
        }

    trades = []
    wins = 0
    losses = 0
    ties = 0
    consecutive_losses = 0
    max_consecutive_losses = 0
    equity = 0.0
    equity_curve = [{"trade": 0, "equity": 0.0}]

    # Minimum warm-up period for EMA 200 & indicators
    warmup = min(50, total_candles // 4)

    # Step through candle by candle
    for i in range(warmup, total_candles - expiry_bars):
        # Window up to candle i (no future peek)
        sub_df = df.iloc[: i + 1]
        sig = analyze_signal(sub_df, asset, timeframe, settings)

        action = sig["action"]
        if action not in ["BUY", "SELL"]:
            continue

        entry_time = int(sub_df.iloc[-1]["time"])
        entry_price = float(sub_df.iloc[-1]["close"])

        # Outcome at expiry_bars later
        exit_candle = df.iloc[i + expiry_bars]
        exit_time = int(exit_candle["time"])
        exit_price = float(exit_candle["close"])

        pnl = 0.0
        result = "TIE"

        if action == "BUY":
            if exit_price > entry_price:
                result = "WIN"
                pnl = stake * payout_pct
                wins += 1
                consecutive_losses = 0
            elif exit_price < entry_price:
                result = "LOSS"
                pnl = -stake
                losses += 1
                consecutive_losses += 1
                if consecutive_losses > max_consecutive_losses:
                    max_consecutive_losses = consecutive_losses
            else:
                result = "TIE"
                pnl = 0.0
                ties += 1
        elif action == "SELL":
            if exit_price < entry_price:
                result = "WIN"
                pnl = stake * payout_pct
                wins += 1
                consecutive_losses = 0
            elif exit_price > entry_price:
                result = "LOSS"
                pnl = -stake
                losses += 1
                consecutive_losses += 1
                if consecutive_losses > max_consecutive_losses:
                    max_consecutive_losses = consecutive_losses
            else:
                result = "TIE"
                pnl = 0.0
                ties += 1

        equity += pnl
        equity_curve.append({"trade": len(trades) + 1, "equity": round(equity, 2)})

        trades.append({
            "id": len(trades) + 1,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "action": action,
            "confidence": sig["confidence"],
            "score": sig["score"],
            "entry_price": round(entry_price, digits),
            "exit_price": round(exit_price, digits),
            "result": result,
            "pnl": round(pnl, 2),
            "reason": sig["reason"]
        })

    total_decided = wins + losses
    win_rate = (wins / total_decided * 100.0) if total_decided > 0 else 0.0
    loss_rate = (losses / total_decided * 100.0) if total_decided > 0 else 0.0
    total_staked = (wins + losses) * stake
    roi_pct = (equity / total_staked * 100.0) if total_staked > 0 else 0.0

    gross_profit = wins * stake * payout_pct
    gross_loss = losses * stake
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

    # Breakeven for 85% payout is 1 / (1 + 0.85) = 54.05%
    is_profitable = win_rate >= 56.0
    warning = None
    if total_decided >= 5 and win_rate < 56.0:
        warning = f"Warning: Win rate ({win_rate:.1f}%) is below 56.0%. At an 85% payout, you need at least a 54.1% win rate to break even. Adjust thresholds or indicators."

    return {
        "asset": asset,
        "timeframe": timeframe,
        "candles_analyzed": total_candles,
        "total_signals": len(trades),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": round(win_rate, 1),
        "loss_rate": round(loss_rate, 1),
        "expected_profit": round(equity, 2),
        "roi_pct": round(roi_pct, 1),
        "profit_factor": round(profit_factor, 2),
        "max_consecutive_losses": max_consecutive_losses,
        "is_profitable": is_profitable,
        "warning": warning,
        "equity_curve": equity_curve[-50:],  # last 50 data points for quick chart
        "recent_trades": trades[-30:],       # last 30 trades for table
        "settings_used": {
            "threshold": threshold,
            "expiry_bars": expiry_bars,
            "payout_pct": payout_pct,
            "stake": stake
        }
    }


async def run_full_backtest(
    asset: str,
    timeframe: str,
    settings: Dict[str, Any] = None,
    limit: int = 1000
) -> Dict[str, Any]:
    """Fetch history, compute indicators, and run simulation."""
    candles = await get_candles(asset, timeframe, limit=limit)
    df = calculate_indicators(candles, settings=settings)
    return run_backtest_on_dataframe(df, asset, timeframe, settings=settings)


import asyncio

async def run_all_assets_backtest(
    timeframe: str,
    settings: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Runs backtest across all 7 assets concurrently to compare win rate by asset."""
    results = {}
    summary_list = []

    async def _test_asset(a):
        try:
            res = await run_full_backtest(a, timeframe, settings=settings, limit=400)
            return (a, res, None)
        except Exception as e:
            return (a, None, str(e))

    tasks = [_test_asset(a) for a in ASSET_CONFIG.keys()]
    completed = await asyncio.gather(*tasks)

    for a, res, err in completed:
        if res:
            results[a] = res
            summary_list.append({
                "asset": a,
                "name": ASSET_CONFIG[a]["name"],
                "signals": res["total_signals"],
                "win_rate": res["win_rate"],
                "expected_profit": res["expected_profit"],
                "is_profitable": res["is_profitable"]
            })
        else:
            results[a] = {"error": err}

    return {
        "timeframe": timeframe,
        "by_asset": summary_list,
        "details": results
    }
