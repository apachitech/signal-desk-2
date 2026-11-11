import logging
from typing import Optional
import httpx
from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("TelegramBot")


class TelegramNotifier:
    """
    Dispatches verified trading signals to Telegram in real-time.
    Supports single user or channel broadcast.
    """
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = (bot_token or TELEGRAM_BOT_TOKEN).strip()
        self.chat_id = (chat_id or TELEGRAM_CHAT_ID).strip()
        self.enabled = bool(self.bot_token and self.chat_id)
        if self.enabled:
            self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        else:
            self.api_url = None

    async def send_signal(
        self,
        asset: str,
        timeframe: str,
        action: str,
        entry_price: float,
        optimal_zone: str,
        adx: float,
        reason: str,
        expiry_label: str
    ) -> bool:
        """Sends an HTML formatted trade alert to Telegram."""
        if not self.enabled or action not in ["BUY", "SELL"]:
            return False

        emoji = "🟢 <b>STRONG CALL / BUY</b>" if action == "BUY" else "🔴 <b>STRONG PUT / SELL</b>"
        arrow = "⬆️" if action == "BUY" else "⬇️"

        message = (
            f"⚡ <b>SIGNALDESK QUANTITATIVE ALERT</b> ⚡\n\n"
            f"<b>Asset:</b> <code>{asset}</code>\n"
            f"<b>Timeframe:</b> {timeframe}\n"
            f"<b>Direction:</b> {emoji} {arrow}\n\n"
            f"🎯 <b>Optimal Entry:</b> <code>{optimal_zone}</code>\n"
            f"⏱️ <b>Duration:</b> {expiry_label}\n"
            f"📊 <b>Trend Strength (ADX):</b> <code>{adx:.1f}</code>\n\n"
            f"💡 <b>Confluence Reason:</b>\n<i>{reason}</i>\n\n"
            f"🛡️ <i>Risk Management: Max 1-2% fixed stake per position.</i>"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.post(self.api_url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"Telegram alert sent for {asset} {action}")
                    return True
                else:
                    logger.warning(f"Telegram API responded with {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to dispatch Telegram signal: {e}")

        return False


# Singleton instance
telegram_bot = TelegramNotifier()

