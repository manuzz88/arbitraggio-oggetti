"""
Telegram Notifier - Invia alert per opportunità di arbitraggio
"""
import httpx
from typing import Optional, Dict, Any
from loguru import logger

from app.config import settings


class TelegramNotifier:
    """Invia notifiche Telegram per opportunità di arbitraggio"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            logger.warning("Telegram notifications disabled - missing BOT_TOKEN or CHAT_ID")
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Invia un messaggio Telegram"""
        if not self.enabled:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": True,
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info("Telegram message sent successfully")
                    return True
                else:
                    logger.error(f"Telegram API error: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def send_opportunity_alert(
        self,
        title: str,
        price: float,
        estimated_value: float,
        margin_percentage: float,
        score: int,
        recommendation: str,
        reasoning: str,
        url: str,
        category: str = "",
        brand: str = "",
        location: str = ""
    ) -> bool:
        """Invia alert per una nuova opportunità di arbitraggio"""
        
        # Emoji in base al recommendation
        emoji = {
            "BUY": "🟢",
            "WATCH": "🟡", 
            "SKIP": "🔴"
        }.get(recommendation, "⚪")
        
        # Calcola profitto
        profit = estimated_value - price
        
        message = f"""
{emoji} <b>NUOVA OPPORTUNITÀ</b> {emoji}

<b>📦 {title}</b>

💰 <b>Prezzo:</b> €{price:.0f}
📈 <b>Valore stimato:</b> €{estimated_value:.0f}
💵 <b>Profitto potenziale:</b> +€{profit:.0f} (+{margin_percentage:.0f}%)

🎯 <b>Score:</b> {score}/100
✅ <b>Raccomandazione:</b> {recommendation}

📝 {reasoning}
"""
        
        if category:
            message += f"\n📂 <b>Categoria:</b> {category}"
        if brand:
            message += f"\n🏷️ <b>Brand:</b> {brand}"
        if location:
            message += f"\n📍 <b>Località:</b> {location}"
        
        message += f"\n\n🔗 <a href='{url}'>Vedi annuncio</a>"
        
        return await self.send_message(message)
    
    async def send_daily_summary(
        self,
        total_analyzed: int,
        opportunities_found: int,
        best_opportunities: list
    ) -> bool:
        """Invia riepilogo giornaliero"""
        
        message = f"""
📊 <b>RIEPILOGO GIORNALIERO</b>

🔍 Items analizzati: {total_analyzed}
⚡ Opportunità trovate: {opportunities_found}

"""
        
        if best_opportunities:
            message += "<b>🏆 Top 3 Opportunità:</b>\n\n"
            for i, opp in enumerate(best_opportunities[:3], 1):
                message += f"{i}. {opp['title'][:30]}... - €{opp['price']} → €{opp['value']} (+{opp['margin']}%)\n"
        
        return await self.send_message(message)
    
    async def send_test_message(self) -> bool:
        """Invia messaggio di test"""
        return await self.send_message(
            "🤖 <b>Arbitraggio Bot</b>\n\n"
            "✅ Notifiche Telegram configurate correttamente!\n"
            "Riceverai alert per le migliori opportunità di arbitraggio."
        )


# Singleton instance
_notifier: Optional[TelegramNotifier] = None

def get_notifier() -> TelegramNotifier:
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier
