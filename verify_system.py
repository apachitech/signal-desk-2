import httpx

def main():
    client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=25.0)
    print("1. Fetching config...")
    r_cfg = client.get("/api/config")
    print(f"Config: {r_cfg.status_code}, assets: {len(r_cfg.json()['assets'])}")

    print("2. Fetching live EURUSD signal...")
    r_sig = client.get("/api/signal?asset=EURUSD&timeframe=5m")
    sig = r_sig.json()["signal"]
    print(f"EURUSD Signal: {sig['action']}, Confidence: {sig['confidence']}%, Reason: {sig['reason']}")

    print("3. Fetching live BTCUSDT signal...")
    r_btc = client.get("/api/signal?asset=BTCUSDT&timeframe=5m")
    sig_btc = r_btc.json()["signal"]
    print(f"BTCUSDT Signal: {sig_btc['action']}, Confidence: {sig_btc['confidence']}%, Price: {sig_btc['latest_price']}")

    print("4. Running single asset backtest for EURUSD...")
    r_bt = client.post("/api/backtest", json={"asset": "EURUSD", "timeframe": "5m", "threshold": 2.0, "limit": 250})
    bt_data = r_bt.json()["data"]
    print(f"EURUSD Backtest: {bt_data['total_signals']} signals, Win Rate: {bt_data['win_rate']}%, PnL: ${bt_data['expected_profit']}")

    print("\n[SUCCESS] SignalDesk application is fully operational!")

if __name__ == "__main__":
    main()
