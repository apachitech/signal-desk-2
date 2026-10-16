import pandas as pd
import numpy as np
from typing import Dict, Any, List


def calculate_indicators(candles: List[Dict[str, Any]], settings: Dict[str, Any] = None) -> pd.DataFrame:
    """
    Calculate all technical indicators and moving averages required for confluence analysis.
    Uses pure pandas/numpy vector calculations for sub-millisecond execution.
    """
    if settings is None:
        settings = {}

    ema_fast = int(settings.get("ema_fast", 9))
    ema_slow = int(settings.get("ema_slow", 21))
    ema_mid = int(settings.get("ema_mid", 50))
    ema_trend = int(settings.get("ema_trend", 200))
    rsi_period = int(settings.get("rsi_period", 14))
    macd_fast = int(settings.get("macd_fast", 12))
    macd_slow = int(settings.get("macd_slow", 26))
    macd_signal = int(settings.get("macd_signal", 9))
    bb_period = int(settings.get("bb_period", 20))
    bb_std = float(settings.get("bb_std", 2.0))
    swing_lookback = int(settings.get("swing_lookback", 20))

    df = pd.DataFrame(candles)
    if df.empty or len(df) < 15:
        return df

    close = df["close"]
    high = df["high"]
    low = df["low"]

    # 1. Market Moving Averages (Fast, Slow, Mid-Term, Macro)
    df["ema_fast"] = close.ewm(span=ema_fast, adjust=False).mean()
    df["ema_slow"] = close.ewm(span=ema_slow, adjust=False).mean()
    df["ema_mid"] = close.ewm(span=min(ema_mid, len(df)), adjust=False).mean()
    trend_span = min(ema_trend, len(df))
    df["ema_trend"] = close.ewm(span=trend_span, adjust=False).mean()

    # 2. RSI (Wilder's smoothed EMA)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=rsi_period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=rsi_period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(50.0)

    # 3. MACD
    ema_f = close.ewm(span=macd_fast, adjust=False).mean()
    ema_s = close.ewm(span=macd_slow, adjust=False).mean()
    df["macd_line"] = ema_f - ema_s
    df["macd_signal"] = df["macd_line"].ewm(span=macd_signal, adjust=False).mean()
    df["macd_hist"] = df["macd_line"] - df["macd_signal"]

    # 4. Bollinger Bands
    sma_bb = close.rolling(bb_period).mean()
    std_bb = close.rolling(bb_period).std().fillna(0)
    df["bb_mid"] = sma_bb
    df["bb_upper"] = sma_bb + (bb_std * std_bb)
    df["bb_lower"] = sma_bb - (bb_std * std_bb)
    df["bb_width"] = ((df["bb_upper"] - df["bb_lower"]) / sma_bb.replace(0, np.nan)).fillna(0)

    # 5. ATR (Average True Range)
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean().fillna(tr)

    # 6. Swing High / Low (Support & Resistance)
    df["swing_high"] = high.shift(1).rolling(swing_lookback).max()
    df["swing_low"] = low.shift(1).rolling(swing_lookback).min()

    return df


def extract_chart_series(df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
    """
    Format moving average and indicator series for Lightweight Charts line overlays.
    """
    ema_fast_data = []
    ema_slow_data = []
    ema_mid_data = []
    ema_trend_data = []
    bb_upper_data = []
    bb_lower_data = []
    bb_mid_data = []

    subset = df.iloc[-200:] if len(df) > 200 else df

    for _, row in subset.iterrows():
        t = int(row["time"])
        if pd.notna(row.get("ema_fast")):
            ema_fast_data.append({"time": t, "value": round(float(row["ema_fast"]), 5)})
        if pd.notna(row.get("ema_slow")):
            ema_slow_data.append({"time": t, "value": round(float(row["ema_slow"]), 5)})
        if pd.notna(row.get("ema_mid")):
            ema_mid_data.append({"time": t, "value": round(float(row["ema_mid"]), 5)})
        if pd.notna(row.get("ema_trend")):
            ema_trend_data.append({"time": t, "value": round(float(row["ema_trend"]), 5)})
        if pd.notna(row.get("bb_upper")):
            bb_upper_data.append({"time": t, "value": round(float(row["bb_upper"]), 5)})
        if pd.notna(row.get("bb_lower")):
            bb_lower_data.append({"time": t, "value": round(float(row["bb_lower"]), 5)})
        if pd.notna(row.get("bb_mid")):
            bb_mid_data.append({"time": t, "value": round(float(row["bb_mid"]), 5)})

    return {
        "ema_fast": ema_fast_data,
        "ema_slow": ema_slow_data,
        "ema_mid": ema_mid_data,
        "ema_trend": ema_trend_data,
        "bb_upper": bb_upper_data,
        "bb_lower": bb_lower_data,
        "bb_mid": bb_mid_data
    }
