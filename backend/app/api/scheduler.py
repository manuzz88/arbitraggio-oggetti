"""
API endpoints per lo scheduler di scraping automatico
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.scheduler import get_scheduler
from app.services.telegram_notifier import get_notifier

router = APIRouter()


class SchedulerSettings(BaseModel):
    queries: Optional[List[str]] = None
    scrape_interval_minutes: Optional[int] = None
    analysis_interval_minutes: Optional[int] = None
    min_score_for_alert: Optional[int] = None


@router.get("/status")
async def get_scheduler_status():
    """Ottiene lo stato dello scheduler"""
    scheduler = get_scheduler()
    return scheduler.get_status()


@router.post("/start")
async def start_scheduler():
    """Avvia lo scheduler automatico"""
    scheduler = get_scheduler()
    await scheduler.start()
    return {"status": "started", "message": "Scheduler avviato"}


@router.post("/stop")
async def stop_scheduler():
    """Ferma lo scheduler automatico"""
    scheduler = get_scheduler()
    await scheduler.stop()
    return {"status": "stopped", "message": "Scheduler fermato"}


@router.put("/settings")
async def update_scheduler_settings(settings: SchedulerSettings):
    """Aggiorna le impostazioni dello scheduler"""
    scheduler = get_scheduler()
    scheduler.update_settings(
        queries=settings.queries,
        scrape_interval=settings.scrape_interval_minutes,
        analysis_interval=settings.analysis_interval_minutes,
        min_score_alert=settings.min_score_for_alert
    )
    return scheduler.get_status()


@router.post("/test-telegram")
async def test_telegram_notification():
    """Invia un messaggio di test su Telegram"""
    notifier = get_notifier()
    
    if not notifier.enabled:
        raise HTTPException(
            status_code=400, 
            detail="Telegram non configurato. Imposta TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID nel .env"
        )
    
    success = await notifier.send_test_message()
    
    if success:
        return {"status": "success", "message": "Messaggio di test inviato"}
    else:
        raise HTTPException(status_code=500, detail="Errore nell'invio del messaggio")


# Categorie predefinite per filtri
CATEGORY_PRESETS = {
    "smartphone": {
        "name": "Smartphone",
        "queries": ["iphone 13", "iphone 14", "iphone 15", "samsung galaxy s23", "pixel 8"],
        "min_price": 150,
        "max_price": 800,
    },
    "gaming": {
        "name": "Gaming & Console",
        "queries": ["nintendo switch", "playstation 5", "xbox series", "steam deck"],
        "min_price": 100,
        "max_price": 500,
    },
    "apple": {
        "name": "Apple Products",
        "queries": ["macbook", "ipad pro", "airpods pro", "apple watch"],
        "min_price": 100,
        "max_price": 1500,
    },
    "vintage": {
        "name": "Vintage & Retrogaming",
        "queries": ["gameboy", "sega megadrive", "nintendo 64", "playstation 1", "commodore"],
        "min_price": 20,
        "max_price": 300,
    },
    "lego": {
        "name": "LEGO",
        "queries": ["lego star wars", "lego technic", "lego creator", "lego city"],
        "min_price": 30,
        "max_price": 400,
    },
    "audio": {
        "name": "Audio & Hi-Fi",
        "queries": ["cuffie sony", "bose", "marshall speaker", "bang olufsen"],
        "min_price": 50,
        "max_price": 500,
    },
    "fotografia": {
        "name": "Fotografia",
        "queries": ["canon eos", "nikon", "sony alpha", "fujifilm", "gopro"],
        "min_price": 100,
        "max_price": 1000,
    },
    "sneakers": {
        "name": "Sneakers Limited",
        "queries": ["jordan 1", "nike dunk", "yeezy", "new balance 550"],
        "min_price": 80,
        "max_price": 400,
    },
}


@router.get("/categories")
async def get_category_presets():
    """Ottiene le categorie predefinite per lo scraping"""
    return CATEGORY_PRESETS


@router.post("/scrape-category/{category_id}")
async def scrape_category(category_id: str):
    """Avvia scraping per una categoria specifica"""
    if category_id not in CATEGORY_PRESETS:
        raise HTTPException(status_code=404, detail=f"Categoria '{category_id}' non trovata")
    
    category = CATEGORY_PRESETS[category_id]
    scheduler = get_scheduler()
    
    # Aggiorna temporaneamente le query
    old_queries = scheduler.default_queries.copy()
    scheduler.default_queries = category["queries"]
    
    # Esegui scraping
    try:
        new_items = await scheduler._run_scraping()
        return {
            "status": "success",
            "category": category["name"],
            "queries": category["queries"],
            "new_items": new_items
        }
    finally:
        # Ripristina query originali
        scheduler.default_queries = old_queries
