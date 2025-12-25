"""
Scheduler - Scraping automatico e analisi AI programmata
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger

from app.config import settings


class ArbitraggioScheduler:
    """Gestisce scraping automatico e analisi AI schedulata"""
    
    def __init__(self):
        self.running = False
        self.last_scrape: Optional[datetime] = None
        self.last_analysis: Optional[datetime] = None
        self.scrape_interval_minutes = 30  # Ogni 30 minuti
        self.analysis_interval_minutes = 15  # Ogni 15 minuti
        self.default_queries = [
            "iphone 13",
            "iphone 14", 
            "nintendo switch",
            "playstation 5",
            "macbook",
            "airpods pro",
        ]
        self.min_score_for_alert = 75  # Alert Telegram per score >= 75
    
    async def start(self):
        """Avvia lo scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        logger.info("Arbitraggio Scheduler started")
        
        # Avvia i task in background
        asyncio.create_task(self._scraping_loop())
        asyncio.create_task(self._analysis_loop())
    
    async def stop(self):
        """Ferma lo scheduler"""
        self.running = False
        logger.info("Arbitraggio Scheduler stopped")
    
    async def _scraping_loop(self):
        """Loop di scraping automatico"""
        while self.running:
            try:
                await self._run_scraping()
                self.last_scrape = datetime.utcnow()
            except Exception as e:
                logger.error(f"Scraping loop error: {e}")
            
            # Attendi intervallo
            await asyncio.sleep(self.scrape_interval_minutes * 60)
    
    async def _analysis_loop(self):
        """Loop di analisi AI automatica"""
        # Attendi un po' prima di iniziare (per dare tempo allo scraping)
        await asyncio.sleep(60)
        
        while self.running:
            try:
                await self._run_analysis()
                self.last_analysis = datetime.utcnow()
            except Exception as e:
                logger.error(f"Analysis loop error: {e}")
            
            # Attendi intervallo
            await asyncio.sleep(self.analysis_interval_minutes * 60)
    
    async def _run_scraping(self):
        """Esegue uno scraping completo"""
        from app.services.scraper.subito_api import SubitoScraperAPI
        from app.services.scraper.mock import MockScraper
        from app.database import AsyncSessionLocal
        from app.models.item import Item, ItemStatus, SourcePlatform
        
        logger.info(f"Starting scheduled scraping for {len(self.default_queries)} queries")
        
        # Seleziona scraper
        if settings.SCRAPER_API_KEY:
            scraper = SubitoScraperAPI()
        else:
            scraper = MockScraper()
        
        await scraper.start()
        total_new = 0
        
        try:
            async with AsyncSessionLocal() as db:
                for query in self.default_queries:
                    try:
                        items = await scraper.search(query, max_pages=1)
                        logger.info(f"Found {len(items)} items for '{query}'")
                        
                        for item_data in items:
                            # Controlla duplicati
                            from sqlalchemy import select
                            existing = await db.execute(
                                select(Item).where(Item.source_id == item_data["source_id"])
                            )
                            if existing.scalar_one_or_none():
                                continue
                            
                            # Determina platform
                            source_id = item_data.get("source_id", "")
                            if source_id.startswith("subito_"):
                                platform = SourcePlatform.SUBITO
                            else:
                                platform = SourcePlatform.OTHER
                            
                            # Crea item
                            new_item = Item(
                                source_platform=platform,
                                source_url=item_data.get("source_url", ""),
                                source_id=source_id,
                                original_title=item_data.get("original_title", ""),
                                original_description=item_data.get("original_description"),
                                original_price=item_data.get("original_price", 0),
                                original_currency=item_data.get("original_currency", "EUR"),
                                original_images=item_data.get("original_images", []),
                                original_location=item_data.get("original_location"),
                                seller_info=item_data.get("seller_info", {}),
                                status=ItemStatus.PENDING,
                            )
                            db.add(new_item)
                            total_new += 1
                        
                        await db.commit()
                        
                        # Pausa tra query
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error scraping '{query}': {e}")
                        continue
                
        finally:
            await scraper.stop()
        
        logger.info(f"Scheduled scraping completed. New items: {total_new}")
        return total_new
    
    async def _run_analysis(self):
        """Esegue analisi AI sugli items pending"""
        from app.services.ai_analyzer import AIAnalyzer
        from app.services.telegram_notifier import get_notifier
        from app.database import AsyncSessionLocal
        from app.models.item import Item, ItemStatus
        from sqlalchemy import select
        
        logger.info("Starting scheduled AI analysis")
        
        analyzer = AIAnalyzer()
        notifier = get_notifier()
        
        async with AsyncSessionLocal() as db:
            # Prendi items pending non analizzati
            query = select(Item).where(
                Item.status == ItemStatus.PENDING,
                Item.ai_score.is_(None),
                Item.original_price >= 30,
                Item.original_price <= 600
            ).order_by(Item.found_at.desc()).limit(20)
            
            result = await db.execute(query)
            items = result.scalars().all()
            
            if not items:
                logger.info("No items to analyze")
                return
            
            logger.info(f"Analyzing {len(items)} items")
            opportunities = []
            
            for item in items:
                try:
                    analysis = await analyzer.analyze_item(
                        title=item.original_title,
                        description=item.original_description or "",
                        price=float(item.original_price),
                        images=item.original_images or [],
                        location=item.original_location or "",
                        condition=item.seller_info.get("condition", "") if item.seller_info else ""
                    )
                    
                    # Salva risultati
                    item.ai_score = analysis.get("score")
                    item.ai_category = analysis.get("category")
                    item.ai_brand = analysis.get("brand")
                    item.ai_model = analysis.get("model")
                    item.estimated_value_min = analysis.get("estimated_value_min")
                    item.estimated_value_max = analysis.get("estimated_value_max")
                    item.potential_margin = analysis.get("margin_percentage")
                    item.ai_validation = analysis
                    item.analyzed_at = datetime.utcnow()
                    
                    # Se score alto, invia alert Telegram
                    score = analysis.get("score", 0)
                    if score >= self.min_score_for_alert:
                        opportunities.append({
                            "item": item,
                            "analysis": analysis
                        })
                        
                        # Invia notifica Telegram
                        await notifier.send_opportunity_alert(
                            title=item.original_title,
                            price=float(item.original_price),
                            estimated_value=analysis.get("estimated_value_min", 0),
                            margin_percentage=analysis.get("margin_percentage", 0),
                            score=score,
                            recommendation=analysis.get("recommendation", "WATCH"),
                            reasoning=analysis.get("reasoning", ""),
                            url=item.source_url,
                            category=analysis.get("category", ""),
                            brand=analysis.get("brand", ""),
                            location=item.original_location or ""
                        )
                    
                except Exception as e:
                    logger.error(f"Error analyzing item {item.id}: {e}")
                    continue
            
            await db.commit()
            
        logger.info(f"Analysis completed. High-score opportunities: {len(opportunities)}")
        return len(opportunities)
    
    def get_status(self) -> Dict[str, Any]:
        """Restituisce lo stato dello scheduler"""
        return {
            "running": self.running,
            "last_scrape": self.last_scrape.isoformat() if self.last_scrape else None,
            "last_analysis": self.last_analysis.isoformat() if self.last_analysis else None,
            "scrape_interval_minutes": self.scrape_interval_minutes,
            "analysis_interval_minutes": self.analysis_interval_minutes,
            "queries": self.default_queries,
            "min_score_for_alert": self.min_score_for_alert,
        }
    
    def update_settings(
        self,
        queries: Optional[List[str]] = None,
        scrape_interval: Optional[int] = None,
        analysis_interval: Optional[int] = None,
        min_score_alert: Optional[int] = None
    ):
        """Aggiorna le impostazioni dello scheduler"""
        if queries:
            self.default_queries = queries
        if scrape_interval:
            self.scrape_interval_minutes = scrape_interval
        if analysis_interval:
            self.analysis_interval_minutes = analysis_interval
        if min_score_alert:
            self.min_score_for_alert = min_score_alert
        
        logger.info(f"Scheduler settings updated: {self.get_status()}")


# Singleton instance
_scheduler: Optional[ArbitraggioScheduler] = None

def get_scheduler() -> ArbitraggioScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ArbitraggioScheduler()
    return _scheduler
