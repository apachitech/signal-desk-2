import asyncio
import json
import logging
import os
import random
import ssl
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import websockets

logger = logging.getLogger("pocket_trader")

# Mapping from standard asset symbols to Pocket Option internal asset symbols
PO_ASSET_MAP = {
    # High-Payout 24/7 OTC Pairs
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
    # Standard Forex / Commodities / Crypto
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

ACCOUNTS_FILE = Path(__file__).resolve().parent.parent / "config" / "accounts.json"


class PocketAccount:
    """
    Represents an individual Pocket Option trading account.
    Maintains isolated WebSocket connections, circuit breakers, and state.
    """
    def __init__(
        self,
        account_id: str,
        name: str,
        uid: int,
        session_id: str,
        is_demo: bool = True,
        stake_amount: float = 1.0,
        max_daily_loss: float = 5.0,
        max_daily_profit: float = 10.0,
        max_consecutive_losses: int = 3,
        max_concurrent_trades: int = 2,
        trade_cooldown_seconds: float = 30.0,
        enabled: bool = True
    ):
        self.id: str = str(account_id)
        self.name: str = name
        self.uid: int = int(uid or 0)
        self.session_id: str = str(session_id or "").strip().strip("\"'")
        self.is_demo: bool = bool(is_demo)
        self.stake_amount: float = max(1.0, float(stake_amount or 1.0))

        # Risk Circuit Breakers
        self.max_daily_loss: float = float(max_daily_loss or 5.0)
        self.max_daily_profit: float = float(max_daily_profit or 10.0)
        self.max_consecutive_losses: int = int(max_consecutive_losses or 3)

        # Concurrency & Pacing Protection
        self.max_concurrent_trades: int = int(max_concurrent_trades or 2)
        self.trade_cooldown_seconds: float = float(trade_cooldown_seconds or 30.0)
        self.enabled: bool = bool(enabled)

        # Runtime State
        self.ws_client = None
        self.connected: bool = False
        self.auth_error: str = ""
        self.last_trade_status: str = "Ready"
        self.last_trade_time: float = 0.0
        self.active_deals: Dict[str, Dict[str, Any]] = {}

        # Daily Session P&L Trackers
        self.daily_pnl: float = 0.0
        self.consecutive_losses: int = 0
        self.total_trades_today: int = 0
        self.wins_today: int = 0
        self.losses_today: int = 0
        self.circuit_broken: bool = False
        self.circuit_reason: str = ""

    @property
    def ws_url(self) -> str:
        """Route to appropriate Pocket Option cluster."""
        if self.is_demo:
            return "wss://demo-api-eu.po.market/socket.io/?EIO=4&transport=websocket"
        return "wss://api-eu.po.market/socket.io/?EIO=4&transport=websocket"

    def clean_expired_deals(self):
        """Purge deals that have passed expiry time."""
        now = time.time()
        expired = [k for k, v in self.active_deals.items() if now >= v.get("expires_at", 0)]
        for k in expired:
            del self.active_deals[k]

    def check_safety_guards(self, asset: str = "", action: str = "") -> Tuple[bool, str]:
        """Verify account-specific circuit breakers before execution."""
        if self.circuit_broken:
            return False, f"Circuit Breaker active for {self.name}: {self.circuit_reason}"

        if self.daily_pnl <= -self.max_daily_loss:
            self.circuit_broken = True
            self.circuit_reason = f"Max daily loss reached (-${abs(self.daily_pnl):.2f})."
            return False, self.circuit_reason

        if self.daily_pnl >= self.max_daily_profit:
            self.circuit_broken = True
            self.circuit_reason = f"Daily profit target achieved (+${self.daily_pnl:.2f})."
            return False, self.circuit_reason

        if self.consecutive_losses >= self.max_consecutive_losses:
            self.circuit_broken = True
            self.circuit_reason = f"{self.max_consecutive_losses} consecutive losses. Cooldown active."
            return False, self.circuit_reason

        # Guard 1: Concurrency Cap
        self.clean_expired_deals()
        if len(self.active_deals) >= self.max_concurrent_trades:
            return False, f"Concurrency Limit: {len(self.active_deals)}/{self.max_concurrent_trades} active deals running."

        # Guard 2: Pacing Cooldown
        now = time.time()
        time_since_last = now - self.last_trade_time
        if self.last_trade_time > 0 and time_since_last < self.trade_cooldown_seconds:
            remaining = int(self.trade_cooldown_seconds - time_since_last)
            return False, f"Pacing Cooldown: Wait {remaining}s before opening next deal."

        # Guard 3: Opposing Direction Conflict
        if asset and action:
            clean_base = asset.replace("_OTC", "").replace("=X", "")
            for deal_key, deal in self.active_deals.items():
                active_base = deal["asset"].replace("_OTC", "").replace("=X", "")
                if clean_base == active_base and deal["action"].upper() != action.upper():
                    return False, f"Opposing conflict: Active {deal['action']} already open on {deal['asset']}."

        return True, "All safety checks passed."

    async def connect(self) -> bool:
        """Establish authenticated WebSocket connection with Pocket Option for this account."""
        if not self.session_id or not self.uid:
            self.auth_error = "Session ID or UID missing"
            self.connected = False
            return False

        self.auth_error = ""
        headers = {
            'Origin': 'https://pocketoption.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36'
        }
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            if self.ws_client:
                try:
                    await self.ws_client.close()
                except Exception:
                    pass
                self.ws_client = None

            self.ws_client = await websockets.connect(
                self.ws_url,
                ssl=ssl_ctx,
                additional_headers=headers,
                open_timeout=10,
                ping_interval=20,
                ping_timeout=20
            )
            await self.ws_client.recv()
            await self.ws_client.send("40")
            await self.ws_client.recv()

            auth_data = {
                "session": self.session_id,
                "isDemo": 1 if self.is_demo else 0,
                "uid": self.uid,
                "platform": 2,
                "isFastHistory": True,
                "isOptimized": True
            }
            await self.ws_client.send("42" + json.dumps(["auth", auth_data]))

            auth_ok = False
            for _ in range(12):
                try:
                    resp = await asyncio.wait_for(self.ws_client.recv(), timeout=4.0)
                    if isinstance(resp, str):
                        if "successauth" in resp or "successupdateBalance" in resp:
                            auth_ok = True
                            self.auth_error = ""
                            break
                        elif "NotAuthorized" in resp:
                            self.auth_error = "Session ID expired or invalid (NotAuthorized)."
                            self.connected = False
                            return False
                except asyncio.TimeoutError:
                    break

            self.connected = auth_ok
            if not self.auth_error and not auth_ok:
                self.connected = True
            return self.connected
        except Exception as e:
            self.auth_error = f"Connection error: {e}"
            self.connected = False
            return False

    async def open_trade(
        self,
        asset: str,
        action: str,
        expiry_seconds: int = 300,
        stake: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a trade specifically on this account."""
        if not self.enabled:
            return {"account_id": self.id, "account_name": self.name, "success": False, "reason": "Account is disabled."}

        is_safe, reason = self.check_safety_guards(asset=asset, action=action)
        if not is_safe:
            return {"account_id": self.id, "account_name": self.name, "success": False, "reason": reason}

        po_asset = PO_ASSET_MAP.get(asset, asset)
        po_action = "call" if action.upper() == "BUY" else "put"
        trade_amount = float(stake or self.stake_amount)

        if not self.connected or not self.ws_client:
            connected = await self.connect()
            if not connected:
                fail_msg = self.auth_error or "Failed to connect to Pocket Option server."
                self.last_trade_status = f"Aborted: {fail_msg}"
                return {"account_id": self.id, "account_name": self.name, "success": False, "reason": fail_msg}

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
            now = time.time()
            self.last_trade_time = now
            self.total_trades_today += 1
            deal_key = f"{po_asset}:{action}:{request_id}"
            self.active_deals[deal_key] = {
                "asset": asset,
                "po_asset": po_asset,
                "action": action,
                "amount": trade_amount,
                "opened_at": now,
                "expires_at": now + expiry_seconds
            }
            mode_str = "DEMO" if self.is_demo else "REAL"
            logger.info(f"[{self.name}] AUTO-ORDER EXECUTED: {action} on {po_asset} for ${trade_amount:.2f} ({mode_str})")
            return {
                "account_id": self.id,
                "account_name": self.name,
                "success": True,
                "asset": po_asset,
                "action": action,
                "amount": trade_amount,
                "expiry_seconds": expiry_seconds,
                "is_demo": self.is_demo,
                "request_id": request_id,
                "timestamp": int(now)
            }
        except Exception as e:
            self.connected = False
            return {"account_id": self.id, "account_name": self.name, "success": False, "reason": f"Execution error: {e}"}

    def to_dict(self, mask_session: bool = True) -> Dict[str, Any]:
        """Serialize account for API and dashboard presentation."""
        self.clean_expired_deals()
        session_display = ""
        if self.session_id:
            session_display = (self.session_id[:12] + "...") if mask_session else self.session_id

        return {
            "id": self.id,
            "name": self.name,
            "uid": self.uid,
            "session_id": session_display,
            "is_demo": self.is_demo,
            "stake_amount": self.stake_amount,
            "max_daily_loss": self.max_daily_loss,
            "max_daily_profit": self.max_daily_profit,
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_concurrent_trades": self.max_concurrent_trades,
            "trade_cooldown_seconds": self.trade_cooldown_seconds,
            "enabled": self.enabled,
            "connected": self.connected,
            "auth_error": self.auth_error,
            "last_trade_status": self.last_trade_status,
            "active_deals_count": len(self.active_deals),
            "session_stats": {
                "daily_pnl": self.daily_pnl,
                "total_trades": self.total_trades_today,
                "wins": self.wins_today,
                "losses": self.losses_today,
                "consecutive_losses": self.consecutive_losses,
                "circuit_broken": self.circuit_broken,
                "circuit_reason": self.circuit_reason
            }
        }


class MultiAccountTrader:
    """
    Master Dispatcher for executing binary options signals across multiple Pocket Option accounts.
    Executes trades simultaneously with isolated safety circuit breakers.
    """
    def __init__(self):
        self.enabled: bool = os.getenv("PO_AUTO_TRADE_ENABLED", "true").lower() in ("true", "1")
        self.sniper_precision_mode: bool = os.getenv("PO_SNIPER_PRECISION", "true").lower() in ("true", "1")
        self.min_confidence: int = int(os.getenv("PO_MIN_CONFIDENCE", "80"))
        self.accounts: Dict[str, PocketAccount] = {}
        self.load_accounts()

    def load_accounts(self):
        """Loads accounts from accounts.json, environment variable PO_ACCOUNTS, or .env defaults."""
        self.accounts.clear()

        # 1. Check PO_ACCOUNTS environment variable (JSON string for cloud/Render)
        env_accounts_str = os.getenv("PO_ACCOUNTS", "").strip()
        loaded = False
        if env_accounts_str:
            try:
                raw_list = json.loads(env_accounts_str)
                for item in raw_list:
                    acc = self._dict_to_account(item)
                    if acc:
                        self.accounts[acc.id] = acc
                if self.accounts:
                    loaded = True
            except Exception as e:
                logger.error(f"Error parsing PO_ACCOUNTS env var: {e}")

        # 2. Check config/accounts.json file
        if not loaded and ACCOUNTS_FILE.exists():
            try:
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    raw_list = json.load(f)
                    for item in raw_list:
                        acc = self._dict_to_account(item)
                        if acc:
                            self.accounts[acc.id] = acc
                if self.accounts:
                    loaded = True
            except Exception as e:
                logger.error(f"Error reading accounts.json: {e}")

        # 3. Fallback: Load from single-account .env variables
        if not loaded:
            default_session = os.getenv("PO_SESSION_ID", "").strip().strip("\"'")
            default_uid = int(os.getenv("PO_UID", "0") or 0)
            default_is_demo = os.getenv("PO_IS_DEMO", "false").lower() in ("true", "1")
            default_stake = float(os.getenv("PO_STAKE_AMOUNT", "1.0"))

            primary_acc = PocketAccount(
                account_id="acc_primary",
                name="Primary Account",
                uid=default_uid,
                session_id=default_session,
                is_demo=default_is_demo,
                stake_amount=default_stake,
                max_daily_loss=float(os.getenv("PO_MAX_DAILY_LOSS", "5.0")),
                max_daily_profit=float(os.getenv("PO_MAX_DAILY_PROFIT", "10.0")),
                max_consecutive_losses=int(os.getenv("PO_MAX_CONSECUTIVE_LOSSES", "3")),
                max_concurrent_trades=int(os.getenv("PO_MAX_CONCURRENT_TRADES", "2")),
                trade_cooldown_seconds=float(os.getenv("PO_TRADE_COOLDOWN_SECONDS", "30.0")),
                enabled=True
            )
            self.accounts[primary_acc.id] = primary_acc
            self.save_accounts()

    def _dict_to_account(self, d: Dict[str, Any]) -> Optional[PocketAccount]:
        """Convert a dictionary to a PocketAccount instance."""
        try:
            acc_id = d.get("id") or f"acc_{random.randint(1000, 9999)}"
            return PocketAccount(
                account_id=acc_id,
                name=d.get("name", "Account"),
                uid=int(d.get("uid", 0) or 0),
                session_id=d.get("session_id", ""),
                is_demo=bool(d.get("is_demo", True)),
                stake_amount=float(d.get("stake_amount", 1.0)),
                max_daily_loss=float(d.get("max_daily_loss", 5.0)),
                max_daily_profit=float(d.get("max_daily_profit", 10.0)),
                max_consecutive_losses=int(d.get("max_consecutive_losses", 3)),
                max_concurrent_trades=int(d.get("max_concurrent_trades", 2)),
                trade_cooldown_seconds=float(d.get("trade_cooldown_seconds", 30.0)),
                enabled=bool(d.get("enabled", True))
            )
        except Exception as e:
            logger.error(f"Failed to create PocketAccount from dict: {e}")
            return None

    def save_accounts(self):
        """Persists accounts to config/accounts.json."""
        try:
            ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            export_list = []
            for acc in self.accounts.values():
                export_list.append({
                    "id": acc.id,
                    "name": acc.name,
                    "uid": acc.uid,
                    "session_id": acc.session_id,
                    "is_demo": acc.is_demo,
                    "stake_amount": acc.stake_amount,
                    "max_daily_loss": acc.max_daily_loss,
                    "max_daily_profit": acc.max_daily_profit,
                    "max_consecutive_losses": acc.max_consecutive_losses,
                    "max_concurrent_trades": acc.max_concurrent_trades,
                    "trade_cooldown_seconds": acc.trade_cooldown_seconds,
                    "enabled": acc.enabled
                })
            with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                json.dump(export_list, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving accounts to {ACCOUNTS_FILE}: {e}")

    async def connect_all(self) -> Dict[str, bool]:
        """Connects all enabled accounts in parallel."""
        tasks = []
        acc_ids = []
        for acc in self.accounts.values():
            if acc.enabled:
                tasks.append(acc.connect())
                acc_ids.append(acc.id)
        if not tasks:
            return {}
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {acc_ids[i]: (results[i] is True) for i in range(len(acc_ids))}

    async def open_trade_all(
        self,
        asset: str,
        action: str,
        expiry_seconds: int = 300
    ) -> List[Dict[str, Any]]:
        """
        Executes a binary options signal simultaneously across all active enabled accounts.
        Runs in parallel via asyncio.gather so all accounts enter at the exact same sub-second tick.
        """
        if not self.enabled:
            return [{"success": False, "reason": "Master auto-trading toggle is OFF."}]

        tasks = []
        enabled_accounts = [acc for acc in self.accounts.values() if acc.enabled]
        if not enabled_accounts:
            return [{"success": False, "reason": "No active trading accounts are enabled."}]

        for acc in enabled_accounts:
            tasks.append(acc.open_trade(asset=asset, action=action, expiry_seconds=expiry_seconds))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        final_results = []
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                final_results.append({
                    "account_id": enabled_accounts[idx].id,
                    "account_name": enabled_accounts[idx].name,
                    "success": False,
                    "reason": f"Execution exception: {res}"
                })
            else:
                final_results.append(res)
        return final_results

    # ================= Backwards Compatibility Properties =================
    @property
    def primary_account(self) -> PocketAccount:
        """Returns the primary account, creating one if empty."""
        if not self.accounts:
            self.load_accounts()
        if "acc_primary" in self.accounts:
            return self.accounts["acc_primary"]
        if self.accounts:
            return next(iter(self.accounts.values()))
        # Fallback dummy
        acc = PocketAccount("acc_primary", "Primary Account", 0, "")
        self.accounts["acc_primary"] = acc
        return acc

    @property
    def is_demo(self) -> bool:
        return self.primary_account.is_demo

    @property
    def stake_amount(self) -> float:
        return self.primary_account.stake_amount

    @stake_amount.setter
    def stake_amount(self, val: float):
        self.primary_account.stake_amount = val
        self.save_accounts()

    @property
    def connected(self) -> bool:
        return any(acc.connected for acc in self.accounts.values() if acc.enabled)

    @connected.setter
    def connected(self, val: bool):
        pass

    @property
    def ws_url(self) -> str:
        return self.primary_account.ws_url

    @property
    def session_id(self) -> str:
        return self.primary_account.session_id

    @property
    def uid(self) -> int:
        return self.primary_account.uid

    @property
    def max_daily_loss(self) -> float:
        return self.primary_account.max_daily_loss

    @property
    def max_daily_profit(self) -> float:
        return self.primary_account.max_daily_profit

    @property
    def max_consecutive_losses(self) -> int:
        return self.primary_account.max_consecutive_losses

    @property
    def max_concurrent_trades(self) -> int:
        return self.primary_account.max_concurrent_trades

    @property
    def trade_cooldown_seconds(self) -> float:
        return self.primary_account.trade_cooldown_seconds

    @property
    def active_deals(self) -> Dict[str, Any]:
        combined = {}
        for acc in self.accounts.values():
            combined.update(acc.active_deals)
        return combined

    @property
    def daily_pnl(self) -> float:
        return sum(acc.daily_pnl for acc in self.accounts.values())

    @property
    def total_trades_today(self) -> int:
        return sum(acc.total_trades_today for acc in self.accounts.values())

    @property
    def wins_today(self) -> int:
        return sum(acc.wins_today for acc in self.accounts.values())

    @property
    def losses_today(self) -> int:
        return sum(acc.losses_today for acc in self.accounts.values())

    @property
    def consecutive_losses(self) -> int:
        return self.primary_account.consecutive_losses

    @property
    def circuit_broken(self) -> bool:
        return self.primary_account.circuit_broken

    @property
    def circuit_reason(self) -> str:
        return self.primary_account.circuit_reason

    @property
    def auth_error(self) -> str:
        return self.primary_account.auth_error

    @property
    def last_trade_status(self) -> str:
        return self.primary_account.last_trade_status

    def clean_expired_deals(self):
        for acc in self.accounts.values():
            acc.clean_expired_deals()

    async def connect(self) -> bool:
        """Connect primary account (backwards-compatible)."""
        return await self.primary_account.connect()

    async def set_demo_mode(self, is_demo: bool):
        """Toggle demo mode on primary account (backwards-compatible)."""
        self.primary_account.is_demo = is_demo
        self.primary_account.connected = False
        if self.primary_account.ws_client:
            try:
                await self.primary_account.ws_client.close()
            except Exception:
                pass
            self.primary_account.ws_client = None
        self.save_accounts()

    async def open_trade(
        self,
        asset: str,
        action: str,
        expiry_seconds: int = 300,
        stake: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes trade across all enabled accounts, returning primary summary.
        """
        results = await self.open_trade_all(asset=asset, action=action, expiry_seconds=expiry_seconds)
        if not results:
            return {"success": False, "reason": "No execution results returned."}
        # Check if at least one account succeeded
        successful = [r for r in results if r.get("success")]
        if successful:
            primary_res = successful[0]
            primary_res["total_accounts_executed"] = len(successful)
            primary_res["all_results"] = results
            return primary_res
        return results[0]

    # ================= CRUD Operations =================
    def add_account(self, data: Dict[str, Any]) -> PocketAccount:
        """Register a new trading account."""
        acc_id = f"acc_{int(time.time())}_{random.randint(100, 999)}"
        acc = PocketAccount(
            account_id=acc_id,
            name=data.get("name", f"Account {len(self.accounts) + 1}"),
            uid=int(data.get("uid", 0) or 0),
            session_id=data.get("session_id", ""),
            is_demo=bool(data.get("is_demo", True)),
            stake_amount=float(data.get("stake_amount", 1.0)),
            max_daily_loss=float(data.get("max_daily_loss", 5.0)),
            max_daily_profit=float(data.get("max_daily_profit", 10.0)),
            max_consecutive_losses=int(data.get("max_consecutive_losses", 3)),
            max_concurrent_trades=int(data.get("max_concurrent_trades", 2)),
            trade_cooldown_seconds=float(data.get("trade_cooldown_seconds", 30.0)),
            enabled=bool(data.get("enabled", True))
        )
        self.accounts[acc_id] = acc
        self.save_accounts()
        return acc

    def update_account(self, acc_id: str, updates: Dict[str, Any]) -> Optional[PocketAccount]:
        """Update existing account parameters."""
        acc = self.accounts.get(acc_id)
        if not acc:
            return None

        if "name" in updates:
            acc.name = str(updates["name"])
        if "uid" in updates and updates["uid"]:
            acc.uid = int(updates["uid"])
        if "session_id" in updates and updates["session_id"]:
            acc.session_id = str(updates["session_id"]).strip().strip("\"'")
        if "is_demo" in updates:
            new_demo = bool(updates["is_demo"])
            if acc.is_demo != new_demo:
                acc.is_demo = new_demo
                acc.connected = False
        if "stake_amount" in updates:
            acc.stake_amount = max(1.0, float(updates["stake_amount"]))
        if "max_daily_loss" in updates:
            acc.max_daily_loss = float(updates["max_daily_loss"])
        if "max_daily_profit" in updates:
            acc.max_daily_profit = float(updates["max_daily_profit"])
        if "max_consecutive_losses" in updates:
            acc.max_consecutive_losses = int(updates["max_consecutive_losses"])
        if "enabled" in updates:
            acc.enabled = bool(updates["enabled"])

        self.save_accounts()
        return acc

    def delete_account(self, acc_id: str) -> bool:
        """Remove an account by ID."""
        if acc_id in self.accounts:
            del self.accounts[acc_id]
            self.save_accounts()
            return True
        return False

    def get_accounts_list(self) -> List[Dict[str, Any]]:
        """Return list of all accounts for API."""
        return [acc.to_dict(mask_session=True) for acc in self.accounts.values()]


# Global singleton instance
pocket_trader = MultiAccountTrader()
