import asyncio
from typing import List
from loguru import logger

from app.tasks import celery_app
from app.services.scraper.subito import SubitoScraper
from app.services.ai.vision import VisionAnalyzer
from app.database import AsyncSessionLocal
from app.models.item import Item, ItemStatus, SourcePlatform
from app.config import settings


@celery_app.task(bind=True, max_retries=3)
def scrape_subito(self, queries: List[str], max_pages: int = 3):
    """
    Task per scraping automatico su Subito.it
    
    Args:
        queries: Lista di termini di ricerca
        max_pages: Numero massimo di pagine per query
    """
    logger.info(f"Starting Subito scraping for queries: {queries}")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_scrape_subito_async(queries, max_pages))


async def _scrape_subito_async(queries: List[str], max_pages: int):
    """Versione async dello scraping"""
    scraper = SubitoScraper()
    vision = VisionAnalyzer()
    total_items = 0
    
    try:
        await scraper.start()
        
        async with AsyncSessionLocal() as db:
            for query in queries:
                logger.info(f"Scraping query: {query}")
                
                try:
                    items = await scraper.search(query, max_pages=max_pages)
                    logger.info(f"Found {len(items)} items for '{query}'")
                    
                    for item_data in items:
                        # Verifica se esiste già
                        existing = await db.execute(
                            f"SELECT id FROM items WHERE source_id = '{item_data['source_id']}' AND source_platform = 'subito'"
                        )
                        if existing.scalar():
                            continue
                        
                        # Crea nuovo item
                        item = Item(
                            source_platform=SourcePlatform.SUBITO,
                            source_url=item_data["source_url"],
                            source_id=item_data["source_id"],
                            original_title=item_data["original_title"],
                            original_price=item_data["original_price"],
                            original_currency=item_data.get("original_currency", "EUR"),
                            original_images=item_data.get("original_images", []),
                            original_location=item_data.get("original_location"),
                            status=ItemStatus.PENDING,
                        )
                        
                        # Analisi AI se abbiamo immagini
                        if item_data.get("original_images") and settings.OPENAI_API_KEY:
                            try:
                                analysis = await vision.analyze_images(
                                    item_data["original_images"],
                                    item_data["original_title"],
                                    item_data["original_price"]
                                )
                                
                                item.ai_validation = analysis
                                item.ai_score = analysis.get("score_affidabilita")
                                item.ai_category = analysis.get("categoria")
                                item.ai_brand = analysis.get("brand")
                                item.ai_model = analysis.get("modello")
                                item.ai_condition = analysis.get("stato")
                                
                                price_est = analysis.get("prezzo_stimato", {})
                                item.estimated_value_min = price_est.get("min")
                                item.estimated_value_max = price_est.get("max")
                                item.potential_margin = analysis.get("margine_potenziale")
                                
                                # Auto-reject se score troppo basso
                                if item.ai_score and item.ai_score < settings.AI_MIN_SCORE_AUTO_REJECT:
                                    item.status = ItemStatus.REJECTED
                                    item.rejection_reason = "Score AI troppo basso"
                                    
                            except Exception as e:
                                logger.error(f"AI analysis failed: {e}")
                        
                        db.add(item)
                        total_items += 1
                    
                    await db.commit()
                    
                except Exception as e:
                    logger.error(f"Error scraping query '{query}': {e}")
                    continue
        
        logger.info(f"Scraping completed. Total new items: {total_items}")
        return {"status": "success", "new_items": total_items}
        
    except Exception as e:
        logger.error(f"Scraping task failed: {e}")
        raise
    finally:
        await scraper.stop()
        await vision.close()


@celery_app.task(bind=True)
def scrape_single_item(self, url: str, platform: str = "subito"):
    """Scrape dettagli di un singolo item"""
    logger.info(f"Scraping single item: {url}")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_scrape_single_async(url, platform))


async def _scrape_single_async(url: str, platform: str):
    """Versione async per singolo item"""
    if platform == "subito":
        scraper = SubitoScraper()
    else:
        raise ValueError(f"Platform {platform} not supported")
    
    try:
        await scraper.start()
        details = await scraper.get_item_details(url)
        return details
    finally:
        await scraper.stop()
