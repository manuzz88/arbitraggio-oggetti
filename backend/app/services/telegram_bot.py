"""
Telegram Bot Handler - Gestisce comandi e notifiche
"""
import asyncio
import httpx
from typing import Optional, List, Dict, Any
from loguru import logger
from datetime import datetime
import json

from app.config import settings
from app.database import AsyncSessionLocal
from sqlalchemy import select, func, desc
from app.models.item import Item, ItemStatus


class TelegramBot:
    """Bot Telegram per notifiche arbitraggio"""
    
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else None
        self.client: Optional[httpx.AsyncClient] = None
        self.last_update_id = 0
    
    async def start(self):
        """Avvia il client HTTP"""
        self.client = httpx.AsyncClient(timeout=30.0)
        if self.token:
            logger.info(f"TelegramBot started (chat_id: {self.chat_id})")
        else:
            logger.warning("TelegramBot: No token configured")
    
    async def stop(self):
        """Chiudi il client"""
        if self.client:
            await self.client.aclose()
        logger.info("TelegramBot stopped")
    
    async def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Invia messaggio al chat configurato"""
        if not self.base_url or not self.chat_id:
            return False
        
        try:
            r = await self.client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": False
                }
            )
            return r.json().get("ok", False)
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    async def _send_with_webapp_button(self, chat_id: int) -> bool:
        """Invia messaggio con pulsante per aprire la Mini App"""
        try:
            message = """🎯 *Arbitraggio Bot*

Trova opportunità di arbitraggio su oggetti usati!

📱 *Apri la Mini App* per:
• Vedere le migliori opportunità
• Cercare prezzi di mercato
• Statistiche in tempo reale

Oppure usa i comandi:
/top - 🏆 Top opportunità
/price - 💰 Valuta prezzo
/status - 📊 Stato sistema"""

            # Per ora invia solo il messaggio testuale
            # La Mini App richiede un URL HTTPS pubblico
            r = await self.client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "reply_markup": {
                        "inline_keyboard": [
                            [{"text": "🌐 Apri Dashboard Web", "url": "http://localhost:5173"}],
                            [{"text": "🏆 Top Opportunità", "callback_data": "top"}],
                            [{"text": "💰 Cerca Prezzo", "callback_data": "search"}]
                        ]
                    }
                }
            )
            return r.json().get("ok", False)
        except Exception as e:
            logger.error(f"Send webapp button error: {e}")
            return False
    
    async def send_opportunity(self, item: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
        """Invia notifica per nuova opportunità"""
        score = analysis.get("score", 0)
        
        # Emoji in base allo score
        if score >= 85:
            emoji = "🔥🔥🔥"
            urgency = "AFFARE IMPERDIBILE!"
        elif score >= 75:
            emoji = "🎯🎯"
            urgency = "Ottima opportunità"
        else:
            emoji = "💡"
            urgency = "Opportunità"
        
        price = item.get("original_price", 0)
        value_min = analysis.get("estimated_value_min", 0)
        value_max = analysis.get("estimated_value_max", 0)
        margin = analysis.get("margin_percentage", 0)
        
        message = f"""{emoji} *{urgency}* - Score {score}/100

📦 *{item.get('original_title', 'N/A')[:100]}*

💰 Prezzo: €{price:.0f}
📊 Valore mercato: €{value_min:.0f} - €{value_max:.0f}
📈 Margine: +{margin:.0f}%

🏷️ {analysis.get('category', 'N/A')} | {analysis.get('brand', 'N/A')}
📍 {item.get('original_location', 'N/A')}

💡 _{analysis.get('reasoning', '')[:200]}_

🔗 [Vedi annuncio]({item.get('source_url', '#')})"""

        return await self.send_message(message)
    
    async def send_daily_summary(self, stats: Dict[str, Any]) -> bool:
        """Invia riepilogo giornaliero"""
        message = f"""📊 *RIEPILOGO GIORNALIERO*
_{datetime.now().strftime('%d/%m/%Y')}_

🔍 Annunci scansionati: {stats.get('scanned', 0)}
✅ Nuove opportunità: {stats.get('opportunities', 0)}
🎯 Score medio: {stats.get('avg_score', 0):.0f}

💰 *Top 3 affari:*
"""
        for i, item in enumerate(stats.get('top_items', [])[:3], 1):
            message += f"\n{i}. {item.get('title', 'N/A')[:40]}... (Score: {item.get('score', 0)})"
        
        return await self.send_message(message)
    
    async def handle_command(self, command: str, chat_id: int, message_text: str = "") -> str:
        """Gestisce i comandi ricevuti"""
        
        if command == "/start":
            # Invia messaggio con pulsante per aprire la Mini App
            await self._send_with_webapp_button(chat_id)
            return None  # Messaggio già inviato
        
        if command == "/app":
            await self._send_with_webapp_button(chat_id)
            return None

        elif command == "/status":
            stats = await self._get_system_stats()
            return f"""📊 *Stato Sistema*

✅ Bot: Online
✅ Scraping: Attivo
✅ AI: GPT-4 Vision
✅ Fonti: Subito.it, PriceCharting, Amazon

📦 *Database:*
   • Totale items: {stats['total']}
   • In attesa: {stats['pending']}
   • Approvati: {stats['approved']}

🎯 *Oggi:*
   • Scansionati: {stats['today']}
   • Opportunità: {stats['opportunities_today']}

⏰ Scansione: ogni 30 min"""

        elif command == "/top":
            return await self._get_top_opportunities()

        elif command == "/stats":
            return await self._get_detailed_stats()

        elif command.startswith("/search"):
            query = message_text.replace("/search", "").strip()
            if not query:
                return "🔎 *Cerca prodotto*\n\nUso: `/search nintendo switch`"
            return await self._search_items(query)

        elif command.startswith("/price"):
            query = message_text.replace("/price", "").strip()
            if not query:
                return "💰 *Valuta prezzo*\n\nUso: `/price iPhone 14 Pro 128GB`"
            return await self._evaluate_price(query)

        elif command == "/categories":
            return """📂 *Categorie Monitorate*

🎮 *Gaming/Retro:*
   Nintendo, PlayStation, Xbox, Retrogaming
   _Fonte: PriceCharting_

📱 *Elettronica:*
   Smartphone, Tablet, PC, Console
   _Fonte: Amazon, eBay_

👗 *Moda/Lusso:*
   Borse, Orologi, Sneakers
   _Fonte: eBay, StockX_

🏠 *Casa/Vintage:*
   Mobili, Oggetti vintage, Antiquariato
   _Fonte: eBay venduti_

🧸 *Collezionismo:*
   LEGO, Funko Pop, Trading Cards
   _Fonte: PriceCharting, eBay_"""

        elif command == "/scan":
            return await self._trigger_scan()

        elif command == "/help":
            return """❓ *Guida Completa*

*🔍 Come funziona:*
1. Scansiono Subito.it ogni 30 min
2. L'AI analizza titolo, foto, descrizione
3. Cerco prezzi reali su Amazon, eBay, PriceCharting
4. Calcolo margine di profitto
5. Ti notifico le migliori opportunità

*📊 Score (0-100):*
• 85+ 🔥 AFFARE IMPERDIBILE
• 70-84 🎯 Ottima opportunità  
• 50-69 💡 Da valutare
• <50 ❌ Non conveniente

*💡 Comandi utili:*
• `/search ps5` - Cerca tra gli items
• `/price iPhone 14` - Valuta un prodotto
• `/top` - Migliori opportunità ora

*📱 Dashboard Web:*
http://localhost:5173"""

        elif command == "/settings":
            return """⚙️ *Impostazioni Notifiche*

*Attualmente attive per:*
✅ Score ≥ 70
✅ Margine ≥ 25%
✅ Prezzo < €500

*Categorie:*
✅ Gaming
✅ Elettronica
✅ Collezionismo
⬜ Moda (disattivato)

_Modifica dalla dashboard web_"""

        else:
            return "❓ Comando non riconosciuto.\n\nUsa /help per la lista comandi."
    
    async def _get_system_stats(self) -> Dict[str, int]:
        """Ottieni statistiche sistema"""
        try:
            async with AsyncSessionLocal() as db:
                total = await db.scalar(select(func.count(Item.id)))
                pending = await db.scalar(
                    select(func.count(Item.id)).where(Item.status == ItemStatus.PENDING)
                )
                approved = await db.scalar(
                    select(func.count(Item.id)).where(Item.status == ItemStatus.APPROVED)
                )
                
                today = datetime.now().replace(hour=0, minute=0, second=0)
                today_count = await db.scalar(
                    select(func.count(Item.id)).where(Item.found_at >= today)
                )
                opportunities = await db.scalar(
                    select(func.count(Item.id)).where(
                        Item.found_at >= today,
                        Item.ai_score >= 70
                    )
                )
                
                return {
                    "total": total or 0,
                    "pending": pending or 0,
                    "approved": approved or 0,
                    "today": today_count or 0,
                    "opportunities_today": opportunities or 0
                }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {"total": 0, "pending": 0, "approved": 0, "today": 0, "opportunities_today": 0}
    
    async def _get_top_opportunities(self) -> str:
        """Ottieni top 5 opportunità"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Item)
                    .where(Item.ai_score >= 60)
                    .order_by(desc(Item.ai_score))
                    .limit(5)
                )
                items = result.scalars().all()
                
                if not items:
                    return "🏆 *Top Opportunità*\n\n_Nessuna opportunità trovata. Avvia una scansione con /scan_"
                
                msg = "🏆 *Top 5 Opportunità*\n"
                
                for i, item in enumerate(items, 1):
                    emoji = "🔥" if item.ai_score >= 85 else "🎯" if item.ai_score >= 70 else "💡"
                    margin = item.potential_margin or 0
                    
                    msg += f"""
{i}. {emoji} *Score {item.ai_score}* | +{margin:.0f}%
   {item.original_title[:50]}...
   💰 €{item.original_price:.0f} → €{item.estimated_value_min or 0:.0f}-{item.estimated_value_max or 0:.0f}
   [Vedi]({item.source_url})
"""
                return msg
                
        except Exception as e:
            logger.error(f"Top opportunities error: {e}")
            return "❌ Errore nel caricamento opportunità"
    
    async def _get_detailed_stats(self) -> str:
        """Statistiche dettagliate"""
        try:
            async with AsyncSessionLocal() as db:
                # Score medio
                avg_score = await db.scalar(
                    select(func.avg(Item.ai_score)).where(Item.ai_score.isnot(None))
                )
                
                # Margine medio
                avg_margin = await db.scalar(
                    select(func.avg(Item.potential_margin)).where(Item.potential_margin.isnot(None))
                )
                
                # Per categoria
                categories = await db.execute(
                    select(Item.ai_category, func.count(Item.id))
                    .where(Item.ai_category.isnot(None))
                    .group_by(Item.ai_category)
                    .order_by(desc(func.count(Item.id)))
                    .limit(5)
                )
                
                msg = f"""📈 *Statistiche Dettagliate*

*Performance:*
   📊 Score medio: {avg_score or 0:.0f}/100
   💰 Margine medio: +{avg_margin or 0:.0f}%

*Top Categorie:*"""
                
                for cat, count in categories:
                    msg += f"\n   • {cat}: {count} items"
                
                return msg
                
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return "❌ Errore nel caricamento statistiche"
    
    async def _search_items(self, query: str) -> str:
        """Cerca items nel database"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Item)
                    .where(Item.original_title.ilike(f"%{query}%"))
                    .order_by(desc(Item.ai_score))
                    .limit(5)
                )
                items = result.scalars().all()
                
                if not items:
                    return f"🔎 *Ricerca: {query}*\n\n_Nessun risultato trovato_"
                
                msg = f"🔎 *Ricerca: {query}*\n\nTrovati {len(items)} risultati:\n"
                
                for item in items:
                    score = item.ai_score or 0
                    emoji = "🔥" if score >= 85 else "🎯" if score >= 70 else "💡" if score >= 50 else "📦"
                    msg += f"""
{emoji} *{item.original_title[:40]}...*
   💰 €{item.original_price:.0f} | Score: {score}
   [Vedi]({item.source_url})
"""
                return msg
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return "❌ Errore nella ricerca"
    
    async def _evaluate_price(self, query: str) -> str:
        """Valuta prezzo di un prodotto"""
        try:
            from app.services.price_researcher import PriceResearcher
            
            researcher = PriceResearcher()
            await researcher.start()
            
            research = await researcher.research(query)
            
            await researcher.stop()
            
            msg = f"💰 *Valutazione: {query}*\n"
            
            if research.avg_ebay_sold:
                msg += f"\n📦 *eBay Venduti:*"
                msg += f"\n   Media: €{research.avg_ebay_sold:.0f}"
                msg += f"\n   Range: €{research.min_ebay_sold:.0f} - €{research.max_ebay_sold:.0f}"
            
            if research.amazon_prices:
                avg = sum(p.price for p in research.amazon_prices) / len(research.amazon_prices)
                msg += f"\n\n🛒 *Amazon:*"
                msg += f"\n   Media: €{avg:.0f}"
            
            if research.pricecharting and research.pricecharting.products:
                p = research.pricecharting.products[0]
                msg += f"\n\n🎮 *PriceCharting:*"
                if p.loose_price_eur:
                    msg += f"\n   Loose: €{p.loose_price_eur:.0f}"
                if p.cib_price_eur:
                    msg += f"\n   CIB: €{p.cib_price_eur:.0f}"
                if p.new_price_eur:
                    msg += f"\n   New: €{p.new_price_eur:.0f}"
            
            if not any([research.avg_ebay_sold, research.amazon_prices, 
                       research.pricecharting and research.pricecharting.products]):
                msg += "\n\n_Nessun dato di prezzo trovato_"
            
            return msg
            
        except Exception as e:
            logger.error(f"Price eval error: {e}")
            return "❌ Errore nella valutazione prezzo"
    
    async def _trigger_scan(self) -> str:
        """Avvia scansione manuale"""
        # Per ora ritorna messaggio, in futuro triggera lo scheduler
        return """🔍 *Scansione Manuale*

⏳ Scansione avviata...

_Riceverai una notifica quando saranno trovate nuove opportunità._

💡 Puoi anche usare la dashboard web per avviare scansioni con filtri specifici."""
    
    async def poll_updates(self):
        """Polling per ricevere messaggi (per bot standalone)"""
        if not self.base_url:
            return
        
        try:
            r = await self.client.get(
                f"{self.base_url}/getUpdates",
                params={"offset": self.last_update_id + 1, "timeout": 10}
            )
            data = r.json()
            
            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    self.last_update_id = update["update_id"]
                    
                    message = update.get("message", {})
                    text = message.get("text", "")
                    chat_id = message.get("chat", {}).get("id")
                    
                    if text.startswith("/") and chat_id:
                        command = text.split()[0]
                        logger.info(f"Received command: {command} from {chat_id}")
                        try:
                            response = await self.handle_command(command, chat_id, text)
                            if response:  # Solo se c'è una risposta testuale
                                await self.client.post(
                                    f"{self.base_url}/sendMessage",
                                    json={
                                        "chat_id": chat_id, 
                                        "text": response, 
                                        "parse_mode": "Markdown",
                                        "disable_web_page_preview": True
                                    }
                                )
                        except Exception as cmd_err:
                            logger.error(f"Command error: {cmd_err}")
                            await self.client.post(
                                f"{self.base_url}/sendMessage",
                                json={"chat_id": chat_id, "text": f"❌ Errore: {str(cmd_err)[:100]}"}
                            )
                    
                    # Gestisci callback dai pulsanti inline
                    callback = update.get("callback_query", {})
                    if callback:
                        callback_id = callback.get("id")
                        callback_data = callback.get("data")
                        callback_chat = callback.get("message", {}).get("chat", {}).get("id")
                        
                        if callback_data and callback_chat:
                            logger.info(f"Callback: {callback_data}")
                            response = await self.handle_command(f"/{callback_data}", callback_chat, "")
                            
                            # Rispondi al callback
                            await self.client.post(
                                f"{self.base_url}/answerCallbackQuery",
                                json={"callback_query_id": callback_id}
                            )
                            
                            if response:
                                await self.client.post(
                                    f"{self.base_url}/sendMessage",
                                    json={
                                        "chat_id": callback_chat,
                                        "text": response,
                                        "parse_mode": "Markdown",
                                        "disable_web_page_preview": True
                                    }
                                )
        except httpx.TimeoutException:
            pass  # Normal timeout, ignore
        except Exception as e:
            logger.error(f"Telegram poll error: {type(e).__name__}: {e}")
    
    async def run_polling(self):
        """Esegui polling continuo"""
        logger.info("Starting Telegram bot polling...")
        while True:
            await self.poll_updates()
            await asyncio.sleep(1)


# Singleton
telegram_bot = TelegramBot()
