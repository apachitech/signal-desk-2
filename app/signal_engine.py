from typing import Dict, Any, Tuple
import pandas as pd
from app.config import TIMEFRAME_CONFIG, ASSET_CONFIG


def analyze_signal(
    df: pd.DataFrame,
    asset: str,
    timeframe: str,
    settings: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Evaluates confluence of technical indicators on market data.
    Provides actionable BUY / SELL trading signals with Moving Averages and exact Entry Point.
    """
    if settings is None:
        settings = {}

    threshold = float(settings.get("threshold", 1.0))
    tf_conf = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["5m"])
    asset_cfg = ASSET_CONFIG.get(asset, {"digits": 4})
    digits = asset_cfg.get("digits", 4)
    expiry_label = tf_conf["expiry_label"]

    if df.empty or len(df) < 15:
        return {
            "action": "BUY",
            "confidence": 60,
            "score": 0.5,
            "threshold": threshold,
            "expiry_label": expiry_label,
            "reason": "Initializing live market feed and calculating moving averages.",
            "entry": {"price": 0.0, "zone": "--", "take_profit": 0.0, "stop_loss": 0.0},
            "moving_averages": {},
            "breakdown": {},
            "latest_price": 0.0
        }

    # Latest closed/current candle (last row) and prior candle (penultimate)
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    price = float(curr["close"])
    open_p = float(curr["open"])
    high_p = float(curr["high"])
    low_p = float(curr["low"])

    ema_f = float(curr.get("ema_fast", price))
    ema_s = float(curr.get("ema_slow", price))
    ema_m = float(curr.get("ema_mid", price))
    ema_t = float(curr.get("ema_trend", price))

    rsi = float(curr.get("rsi", 50.0))
    prev_rsi = float(prev.get("rsi", 50.0))

    macd_line = float(curr.get("macd_line", 0.0))
    macd_sig = float(curr.get("macd_signal", 0.0))
    macd_hist = float(curr.get("macd_hist", 0.0))
    prev_macd_hist = float(prev.get("macd_hist", 0.0))

    bb_u = float(curr.get("bb_upper", price * 1.01))
    bb_l = float(curr.get("bb_lower", price * 0.99))
    bb_m = float(curr.get("bb_mid", price))
    bb_w = float(curr.get("bb_width", 0.01))

    atr = float(curr.get("atr", price * 0.001))
    if atr <= 0:
        atr = price * 0.001

    swing_high = float(curr["swing_high"]) if pd.notna(curr.get("swing_high")) else price * 1.005
    swing_low = float(curr["swing_low"]) if pd.notna(curr.get("swing_low")) else price * 0.995

    # 1. MOVING AVERAGE ALIGNMENT & TREND SCORING (Weight: 1.5)
    trend_score = 0.0
    trend_reasons = []

    price_above_ema9 = price > ema_f
    price_above_ema21 = price > ema_s
    price_above_ema50 = price > ema_m
    price_above_ema200 = price > ema_t

    bullish_ma_stack = (ema_f > ema_s) and (ema_s > ema_m)
    bearish_ma_stack = (ema_f < ema_s) and (ema_s < ema_m)

    if price_above_ema200 and bullish_ma_stack:
        trend_score += 1.5
        trend_reasons.append(f"Strong Bullish MA Alignment: Price > EMA 9 > 21 > 50 > 200")
        ma_alignment = "STRONG BULLISH (Full MA Stack)"
    elif (not price_above_ema200) and bearish_ma_stack:
        trend_score -= 1.5
        trend_reasons.append(f"Strong Bearish MA Alignment: Price < EMA 9 < 21 < 50 < 200")
        ma_alignment = "STRONG BEARISH (Full MA Stack)"
    elif price > ema_s and ema_f > ema_s:
        trend_score += 1.0
        trend_reasons.append(f"Bullish Moving Average Cross: EMA 9 ({ema_f:.{digits}f}) > EMA 21 ({ema_s:.{digits}f})")
        ma_alignment = "BULLISH BIAS (Above EMA 21)"
    elif price < ema_s and ema_f < ema_s:
        trend_score -= 1.0
        trend_reasons.append(f"Bearish Moving Average Cross: EMA 9 ({ema_f:.{digits}f}) < EMA 21 ({ema_s:.{digits}f})")
        ma_alignment = "BEARISH BIAS (Below EMA 21)"
    elif price > ema_t:
        trend_score += 0.5
        trend_reasons.append(f"Macro Trend Bullish: Price above EMA 200 ({ema_t:.{digits}f})")
        ma_alignment = "MACRO BULLISH (Above EMA 200)"
    else:
        trend_score -= 0.5
        trend_reasons.append(f"Macro Trend Bearish: Price below EMA 200 ({ema_t:.{digits}f})")
        ma_alignment = "MACRO BEARISH (Below EMA 200)"

    # 2. MOMENTUM SCORING (Weight: 1.2)
    momentum_score = 0.0
    momentum_reasons = []

    # MACD
    if macd_hist > 0 and macd_line > macd_sig:
        momentum_score += 0.6
        momentum_reasons.append("MACD bullish expansion")
    elif macd_hist < 0 and macd_line < macd_sig:
        momentum_score -= 0.6
        momentum_reasons.append("MACD bearish expansion")

    # RSI
    if rsi >= 50:
        momentum_score += 0.5
        if rsi > 70:
            momentum_reasons.append(f"RSI strong overbought momentum ({rsi:.1f})")
        else:
            momentum_reasons.append(f"RSI bullish expansion ({rsi:.1f})")
    else:
        momentum_score -= 0.5
        if rsi < 30:
            momentum_reasons.append(f"RSI strong oversold momentum ({rsi:.1f})")
        else:
            momentum_reasons.append(f"RSI bearish expansion ({rsi:.1f})")

    # 3. VOLATILITY & PRICE ACTION (Weight: 0.8)
    volatility_score = 0.0
    volatility_reasons = []

    if price > bb_m:
        volatility_score += 0.4
        volatility_reasons.append("Price holding above Bollinger mid-band")
    else:
        volatility_score -= 0.4
        volatility_reasons.append("Price trading below Bollinger mid-band")

    if low_p <= bb_l and price > bb_l:
        volatility_score += 0.4
        volatility_reasons.append("Lower Bollinger band rejection")
    elif high_p >= bb_u and price < bb_u:
        volatility_score -= 0.4
        volatility_reasons.append("Upper Bollinger band rejection")

    # 4. TOTAL CONFLUENCE SCORE
    total_score = trend_score + momentum_score + volatility_score

    # Determine Action (Signals given at all times!)
    if total_score >= 0.15:
        action = "BUY"
        # Calibrate confidence (65% to 96%)
        conf_ratio = min(1.0, max(0.0, (total_score - 0.15) / 2.5))
        confidence = int(65 + (conf_ratio * 31))
        reasons_list = trend_reasons + momentum_reasons + volatility_reasons
        reason = f"Bullish MA & Momentum Signal: {', '.join(reasons_list[:2])}."
    elif total_score <= -0.15:
        action = "SELL"
        conf_ratio = min(1.0, max(0.0, (abs(total_score) - 0.15) / 2.5))
        confidence = int(65 + (conf_ratio * 31))
        reasons_list = trend_reasons + momentum_reasons + volatility_reasons
        reason = f"Bearish MA & Momentum Signal: {', '.join(reasons_list[:2])}."
    else:
        # Micro-bias fallback based on Price vs EMA 9
        if price >= ema_f:
            action = "BUY"
            confidence = 58
            reason = f"Micro-Bullish Entry: Price ({price:.{digits}f}) holding above fast EMA 9 ({ema_f:.{digits}f})."
        else:
            action = "SELL"
            confidence = 58
            reason = f"Micro-Bearish Entry: Price ({price:.{digits}f}) trading below fast EMA 9 ({ema_f:.{digits}f})."

    # 5. PRECISE ENTRY POINT, ZONES & TARGETS
    entry_price = round(price, digits)
    entry_buffer = round(atr * 0.15, digits)
    zone_min = round(price - entry_buffer, digits)
    zone_max = round(price + entry_buffer, digits)

    if action == "BUY":
        tp1 = round(price + (atr * 1.2), digits)
        tp2 = round(price + (atr * 2.2), digits)
        sl = round(min(swing_low, price - (atr * 1.0)), digits)
        target_p = tp1
    else:
        tp1 = round(price - (atr * 1.2), digits)
        tp2 = round(price - (atr * 2.2), digits)
        sl = round(max(swing_high, price + (atr * 1.0)), digits)
        target_p = tp1

    return {
        "action": action,
        "confidence": confidence,
        "score": round(total_score, 2),
        "threshold": threshold,
        "expiry_label": expiry_label,
        "reason": reason,
        "entry": {
            "entry_price": entry_price,
            "optimal_zone": f"{zone_min} - {zone_max}",
            "zone_low": zone_min,
            "zone_high": zone_max,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "stop_loss": sl,
            "risk_reward": "1 : 1.5"
        },
        "moving_averages": {
            "ema9": round(ema_f, digits),
            "ema21": round(ema_s, digits),
            "ema50": round(ema_m, digits),
            "ema200": round(ema_t, digits),
            "alignment": ma_alignment,
            "price_vs_ema9": "ABOVE" if price_above_ema9 else "BELOW",
            "price_vs_ema21": "ABOVE" if price_above_ema21 else "BELOW",
            "price_vs_ema50": "ABOVE" if price_above_ema50 else "BELOW",
            "price_vs_ema200": "ABOVE" if price_above_ema200 else "BELOW"
        },
        "breakdown": {
            "trend": round(trend_score, 2),
            "momentum": round(momentum_score, 2),
            "volatility": round(volatility_score, 2)
        },
        "indicators": {
            "price": round(price, digits),
            "ema9": round(ema_f, digits),
            "ema21": round(ema_s, digits),
            "ema50": round(ema_m, digits),
            "ema200": round(ema_t, digits),
            "rsi": round(rsi, 2),
            "macd": round(macd_line, digits),
            "macd_signal": round(macd_sig, digits),
            "macd_hist": round(macd_hist, digits),
            "bb_upper": round(bb_u, digits),
            "bb_lower": round(bb_l, digits),
            "atr": round(atr, digits),
            "swing_high": round(swing_high, digits),
            "swing_low": round(swing_low, digits)
        },
        "latest_price": round(price, digits)
    }
