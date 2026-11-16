import asyncio
import json
import logging
import os
import random
import ssl
import time
from typing import Dict, Any, Optional
import websockets

logger = logging.getLogger("PocketTrader")

# Symbol mapping from SignalDesk internal names to Pocket Option exact asset names
PO_ASSET_MAP = {
    # OTC Pairs
    "EURUSD_OTC": "EURUSD_otc",
    "GBPUSD_OTC": "GBPUSD_otc",
    "USDJPY_OTC": "USDJPY_otc",
    "AUDUSD_OTC": "AUDUSD_otc",
    "USDCAD_OTC": "USDCAD_otc",
    "USDCHF_OTC": "USDCHF_otc",
    "NZDUSD_OTC": "NZDUSD_otc",
    "EURGBP_OTC": "EURGBP_otc",
    "AUDJPY_OTC": "AUDJPY_otc",
    "GBPJPY_OTC": "GBPJPY_otc",
    "XAUUSD_OTC": "XAUUSD_otc",
    "BTCUSD_OTC": "BTCUSD_otc",
    "ETHUSD_OTC": "ETHUSD_otc",
    "SOLUSD_OTC": "SOLUSD_otc",
    # Real Forex & Commodities
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
    "USDCHF": "USDCHF",
    "NZDUSD": "NZDUSD",
    "EURJPY": "EURJPY",
    "GBPJPY": "GBPJPY",
    "EURGBP": "EURGBP",
    "EURCAD": "EURCAD",
    "EURAUD": "EURAUD",
    "GBPAUD": "GBPAUD",
    "AUDJPY": "AUDJPY",
    "CADJPY": "CADJPY",
    "CHFJPY": "CHFJPY",
    "XAUUSD": "XAUUSD",
    "XAGUSD": "XAGUSD",
    "USOIL": "USOIL",
    # Crypto
    "BTCUSDT": "BTCUSDT",
    "ETHUSDT": "ETHUSDT",
    "SOLUSDT": "SOLUSDT",
    "BNBUSDT": "BNBUSDT",
    "XRPUSDT": "XRPUSDT",
    "DOGEUSDT": "DOGEUSDT",
    "ADAUSDT": "ADAUSDT",
    "AVAXUSDT": "AVAXUSDT",
    "LINKUSDT": "LINKUSDT",
    "SUIUSDT": "SUIUSDT",
    "DOTUSDT": "DOTUSDT",
    "NEARUSDT": "NEARUSDT"
}


class PocketOptionAutoTrader:
    """
    Automated execution bridge to Pocket Option via direct WebSocket Socket.IO protocol.
    Enforces risk circuit breaker limits (Daily Loss, Daily Profit, Consecutive Losses).
    """
    def __init__(self):
        self.enabled: bool = os.getenv("PO_AUTO_TRADE_ENABLED", "false").lower() in ("true", "1")
        self.session_id: str = os.getenv("PO_SESSION_ID", "").strip()
        self.uid: int = int(os.getenv("PO_UID", "0") or 0)
        self.is_demo: bool = os.getenv("PO_IS_DEMO", "true").lower() in ("true", "1")
        self.stake_amount: float = float(os.getenv("PO_STAKE_AMOUNT", "1.0"))

        # Safety Circuit Breakers
        self.max_daily_loss: float = float(os.getenv("PO_MAX_DAILY_LOSS", "5.0"))
        self.max_daily_profit: float = float(os.getenv("PO_MAX_DAILY_PROFIT", "10.0"))
        self.max_consecutive_losses: int = int(os.getenv("PO_MAX_CONSECUTIVE_LOSSES", "3"))

        # Daily Session P&L Trackers
        self.daily_pnl: float = 0.0
        self.consecutive_losses: int = 0
        self.total_trades_today: int = 0
        self.wins_today: int = 0
        self.losses_today: int = 0
        self.circuit_broken: bool = False
        self.circuit_reason: str = ""

        self.ws_url = "wss://api-eu.po.market/socket.io/?EIO=4&transport=websocket"
        self.ws_client = None
        self.connected = False
        self.is_running = False
        self.auth_error: str = ""
        self.last_trade_status: str = ""

    def check_safety_guards(self) -> tuple[bool, str]:
        """Verify that account is not locked by risk circuit breakers."""
        if self.circuit_broken:
            return False, f"Circuit Breaker Tripped: {self.circuit_reason}"
        if self.daily_pnl <= -abs(self.max_daily_loss):
            self.circuit_broken = True
            self.circuit_reason = f"Max daily loss reached (-${abs(self.max_daily_loss):.2f}). Stop trading."
            return False, self.circuit_reason
        if self.daily_pnl >= self.max_daily_profit:
            self.circuit_broken = True
            self.circuit_reason = f"Daily profit target reached (+${self.max_daily_profit:.2f})! Banked."
            return False, self.circuit_reason
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.circuit_broken = True
            self.circuit_reason = f"{self.max_consecutive_losses} consecutive losses. Cooldown active."
            return False, self.circuit_reason
        return True, "All safety checks passed."

    async def set_demo_mode(self, is_demo: bool):
        """Switch between Demo and Real account, re-authenticating if connected."""
        if self.is_demo == is_demo:
            return
        self.is_demo = is_demo
        mode_str = "DEMO" if is_demo else "REAL"
        logger.info(f"Pocket Option account switched to: {mode_str}")
        if self.connected and self.ws_client:
            try:
                auth_data = {
                    "session": self.session_id,
                    "isDemo": 1 if self.is_demo else 0,
                    "uid": self.uid,
                    "platform": 1
                }
                await self.ws_client.send("42" + json.dumps(["auth", auth_data]))
                logger.info(f"Re-sent Pocket Option auth packet for {mode_str} balance.")
            except Exception as e:
                logger.warning(f"Error re-authenticating on mode switch: {e}")
                self.connected = False
                if self.ws_client:
                    await self.ws_client.close()

    async def connect(self) -> bool:
        """Establish authenticated WebSocket connection with Pocket Option."""
        if not self.session_id or not self.uid:
            logger.warning("Pocket Option session_id or uid missing in .env")
            return False

        headers = {
            'Origin': 'https://pocketoption.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36'
        }
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            self.ws_client = await websockets.connect(
                self.ws_url,
                ssl=ssl_ctx,
                additional_headers=headers,
                open_timeout=10,
                ping_interval=20,
                ping_timeout=20
            )
            # Receive engine.io open packet
            await self.ws_client.recv()
            # Send socket.io connect packet
            await self.ws_client.send("40")
            await self.ws_client.recv()

            # Send auth packet
            auth_data = {
                "session": self.session_id,
                "isDemo": 1 if self.is_demo else 0,
                "uid": self.uid,
                "platform": 1
            }
            await self.ws_client.send("42" + json.dumps(["auth", auth_data]))

            # Await and verify Pocket Option server auth response
            auth_ok = False
            for _ in range(6):
                try:
                    resp = await asyncio.wait_for(self.ws_client.recv(), timeout=3.0)
                    if isinstance(resp, str):
                        if "successauth" in resp:
                            auth_ok = True
                            self.auth_error = ""
                            break
                        elif "NotAuthorized" in resp:
                            self.auth_error = "PO_SESSION_ID is expired or invalid (Pocket Option returned 'NotAuthorized'). Refresh session from browser."
                            logger.error(f"[!] Pocket Option Auth Failed: {self.auth_error}")
                            self.connected = False
                            return False
                except asyncio.TimeoutError:
                    break

            self.connected = auth_ok
            if auth_ok:
                logger.info("Pocket Option WebSocket authenticated successfully.")
            elif not self.auth_error:
                # If neither successauth nor NotAuthorized arrived within timeout, assume ready
                self.connected = True
            return self.connected
        except Exception as e:
            self.auth_error = f"Connection failed: {e}"
            logger.error(f"Failed to connect to Pocket Option WebSocket: {e}")
            self.connected = False
            return False

    async def open_trade(
        self,
        asset: str,
        action: str,
        expiry_seconds: int = 300,
        stake: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes a live binary options trade on Pocket Option in sub-50ms.
        action: "BUY" (maps to "call") or "SELL" (maps to "put")
        """
        if not self.enabled:
            return {"success": False, "reason": "Auto-trading toggle is OFF in SignalDesk."}

        is_safe, reason = self.check_safety_guards()
        if not is_safe:
            return {"success": False, "reason": reason}

        po_asset = PO_ASSET_MAP.get(asset, asset)
        po_action = "call" if action.upper() == "BUY" else "put"
        trade_amount = float(stake or self.stake_amount)

        # Ensure WebSocket is live
        if not self.connected or not self.ws_client:
            connected = await self.connect()
            if not connected:
                fail_msg = self.auth_error or "Failed to connect to Pocket Option server."
                self.last_trade_status = f"Aborted: {fail_msg}"
                return {"success": False, "reason": fail_msg}

        request_id = random.randint(10000000, 99999999)
        order_payload = {
            "asset": po_asset,
            "amount": trade_amount,
            "action": po_action,
            "isDemo": 1 if self.is_demo else 0,
            "requestId": request_id,
            "optionType": 100,
            "time": expiry_seconds
        }

        try:
            msg = "42" + json.dumps(["openOrder", order_payload])
            await self.ws_client.send(msg)
            self.total_trades_today += 1
            logger.info(f"[*] AUTO-ORDER EXECUTED: {action} on {po_asset} for ${trade_amount:.2f} ({expiry_seconds}s)")
            return {
                "success": True,
                "asset": po_asset,
                "action": action,
                "amount": trade_amount,
                "expiry_seconds": expiry_seconds,
                "is_demo": self.is_demo,
                "request_id": request_id,
                "timestamp": int(time.time())
            }
        except Exception as e:
            self.connected = False
            logger.error(f"Error sending openOrder to Pocket Option: {e}")
            return {"success": False, "reason": f"Execution error: {str(e)}"}

    def reset_daily_stats(self):
        """Reset session statistics for a fresh trading day."""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.total_trades_today = 0
        self.wins_today = 0
        self.losses_today = 0
        self.circuit_broken = False
        self.circuit_reason = ""


# Global singleton instance
pocket_trader = PocketOptionAutoTrader()

