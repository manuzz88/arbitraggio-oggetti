from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger

router = APIRouter()


class ScrapeRequest(BaseModel):
    queries: List[str]
    max_pages: int = 3
    platform: str = "subito"


class ScrapeResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None


@router.post("/start", response_model=ScrapeResponse)
async def start_scraping(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Avvia uno scraping manuale.
    Lo scraping viene eseguito in background.
    """
    logger.info(f"Manual scraping requested for queries: {request.queries}")
    
    if request.platform != "subito":
        raise HTTPException(status_code=400, detail=f"Platform {request.platform} not supported yet")
    
    # Esegui in background senza Celery (per semplicità in dev)
    background_tasks.add_task(
        run_scraping_background,
        request.queries,
        request.max_pages
    )
    
    return ScrapeResponse(
        status="started",
        message=f"Scraping started for {len(request.queries)} queries"
    )


async def run_scraping_background(queries: List[str], max_pages: int):
    """Esegue lo scraping in background"""
    from app.config import settings
    
    # Usa ScraperAPI se configurato, altrimenti mock
    if settings.SCRAPER_API_KEY:
        from app.services.scraper.subito_api import SubitoScraperAPI as Scraper
        logger.info("Using SubitoScraperAPI (via ScraperAPI)")
    else:
        from app.services.scraper.mock import MockScraper as Scraper
        logger.info("Using MockScraper (no SCRAPER_API_KEY)")
    
    from app.services.ai.vision import VisionAnalyzer
    from app.database import AsyncSessionLocal
    from app.models.item import Item, ItemStatus, SourcePlatform
    from app.config import settings
    from sqlalchemy import select
    
    scraper = Scraper()
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
                    
                    # Determina platform in base al source_id
                    for item_data in items:
                        source_id = item_data['source_id']
                        if source_id.startswith("subito_"):
                            platform = SourcePlatform.SUBITO
                        elif source_id.startswith("mock_"):
                            platform = SourcePlatform.OTHER
                        else:
                            platform = SourcePlatform.OTHER
                        
                        # Verifica se esiste già
                        result = await db.execute(
                            select(Item).where(
                                Item.source_id == source_id,
                                Item.source_platform == platform
                            )
                        )
                        if result.scalar():
                            continue
                        
                        # Crea nuovo item
                        item = Item(
                            source_platform=platform,
                            source_url=item_data["source_url"],
                            source_id=item_data["source_id"],
                            original_title=item_data["original_title"],
                            original_price=item_data["original_price"],
                            original_currency=item_data.get("original_currency", "EUR"),
                            original_images=item_data.get("original_images", []),
                            original_location=item_data.get("original_location"),
                            status=ItemStatus.PENDING,
                        )
                        
                        # Analisi AI se abbiamo immagini e API key
                        if item_data.get("original_images") and settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_key":
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
                                if price_est:
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
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
    finally:
        await scraper.stop()
        await vision.close()


@router.get("/status")
async def get_scraper_status():
    """Ritorna lo stato dello scraper"""
    return {
        "status": "idle",
        "supported_platforms": ["subito"],
        "coming_soon": ["facebook", "wallapop", "vinted"]
    }
