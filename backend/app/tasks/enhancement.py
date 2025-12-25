import asyncio
import os
from pathlib import Path
from typing import Optional
from uuid import UUID
from loguru import logger

from app.tasks import celery_app
from app.services.ai.vision import VisionAnalyzer
from app.services.ai.enhancement import ImageEnhancer
from app.services.ai.description import DescriptionGenerator
from app.services.platforms.ebay import EbayService
from app.database import AsyncSessionLocal
from app.models.item import Item, ItemStatus
from app.models.listing import Listing, ListingStatus, DestinationPlatform
from app.config import settings
import httpx


IMAGES_DIR = Path("./data/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


@celery_app.task(bind=True, max_retries=3)
def process_approved_item(self, item_id: str, listing_price: Optional[float] = None, platform: str = "ebay"):
    """
    Processa un item approvato:
    1. Scarica immagini originali
    2. Migliora immagini con AI
    3. Genera titolo e descrizione ottimizzati
    4. Crea e pubblica listing su eBay
    """
    logger.info(f"Processing approved item: {item_id}")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_process_item_async(item_id, listing_price, platform))


async def _process_item_async(item_id: str, listing_price: Optional[float], platform: str):
    """Versione async del processing"""
    
    enhancer = ImageEnhancer()
    desc_generator = DescriptionGenerator()
    
    async with AsyncSessionLocal() as db:
        # Carica item
        result = await db.execute(f"SELECT * FROM items WHERE id = '{item_id}'")
        item = result.fetchone()
        
        if not item:
            raise ValueError(f"Item {item_id} not found")
        
        item_dict = dict(item._mapping)
        
        try:
            # 1. Scarica immagini originali
            logger.info("Downloading original images...")
            original_images = item_dict.get("original_images", [])
            downloaded_images = []
            
            async with httpx.AsyncClient() as client:
                for i, url in enumerate(original_images[:5]):  # Max 5 immagini
                    try:
                        response = await client.get(url, timeout=30)
                        if response.status_code == 200:
                            downloaded_images.append(response.content)
                    except Exception as e:
                        logger.warning(f"Failed to download image {i}: {e}")
            
            if not downloaded_images:
                raise ValueError("No images could be downloaded")
            
            # 2. Migliora immagini
            logger.info("Enhancing images...")
            enhanced_images = await enhancer.enhance_images(
                downloaded_images,
                upscale=True,
                remove_background=False
            )
            
            # Salva immagini migliorate
            item_images_dir = IMAGES_DIR / item_id
            item_images_dir.mkdir(exist_ok=True)
            
            enhanced_paths = []
            for i, img_bytes in enumerate(enhanced_images):
                img_path = item_images_dir / f"enhanced_{i}.jpg"
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                enhanced_paths.append(str(img_path))
            
            # 3. Genera titolo e descrizione
            logger.info("Generating listing content...")
            ai_validation = item_dict.get("ai_validation", {})
            
            content = await desc_generator.generate_listing_content(
                ai_validation,
                item_dict.get("original_description", item_dict.get("original_title", "")),
                listing_price or float(item_dict.get("original_price", 0))
            )
            
            # Calcola prezzo se non specificato
            if not listing_price:
                estimated_max = item_dict.get("estimated_value_max")
                original_price = float(item_dict.get("original_price", 0))
                
                if estimated_max:
                    listing_price = float(estimated_max) * 0.9  # 90% del max stimato
                else:
                    listing_price = original_price * 1.4  # +40% markup
            
            # 4. Crea listing nel database
            listing = Listing(
                item_id=UUID(item_id),
                platform=DestinationPlatform.EBAY if platform == "ebay" else DestinationPlatform.ETSY,
                enhanced_title=content["title"],
                enhanced_description=content["description"],
                enhanced_images=enhanced_paths,
                listing_price=listing_price,
                status=ListingStatus.DRAFT,
            )
            
            db.add(listing)
            await db.commit()
            await db.refresh(listing)
            
            # 5. Pubblica su eBay (se configurato)
            if platform == "ebay" and settings.EBAY_APP_ID:
                logger.info("Publishing to eBay...")
                try:
                    ebay = EbayService()
                    
                    # TODO: Upload immagini su hosting e ottenere URL pubblici
                    # Per ora usiamo le immagini originali
                    image_urls = original_images[:5]
                    
                    result = await ebay.create_and_publish_listing(
                        sku=str(listing.id),
                        title=content["title"],
                        description=content["description"],
                        price=listing_price,
                        category_id="139971",  # TODO: Categoria dinamica
                        images=image_urls,
                        condition="USED_GOOD",
                    )
                    
                    listing.platform_listing_id = result.get("listing_id")
                    listing.listing_url = result.get("listing_url")
                    listing.status = ListingStatus.ACTIVE
                    
                    await ebay.close()
                    
                except Exception as e:
                    logger.error(f"eBay publishing failed: {e}")
                    listing.status = ListingStatus.ERROR
                    listing.error_message = str(e)
            
            # Aggiorna status item
            await db.execute(
                f"UPDATE items SET status = 'listed' WHERE id = '{item_id}'"
            )
            await db.commit()
            
            logger.info(f"Item {item_id} processed successfully")
            return {
                "status": "success",
                "listing_id": str(listing.id),
                "listing_url": listing.listing_url
            }
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
        finally:
            await desc_generator.close()


@celery_app.task(bind=True)
def enhance_images_only(self, image_urls: list, item_id: str):
    """Task per migliorare solo le immagini"""
    logger.info(f"Enhancing images for item {item_id}")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_enhance_only_async(image_urls, item_id))


async def _enhance_only_async(image_urls: list, item_id: str):
    """Versione async per enhancement solo immagini"""
    enhancer = ImageEnhancer()
    
    # Scarica immagini
    downloaded = []
    async with httpx.AsyncClient() as client:
        for url in image_urls[:5]:
            try:
                response = await client.get(url, timeout=30)
                if response.status_code == 200:
                    downloaded.append(response.content)
            except:
                pass
    
    if not downloaded:
        return {"status": "error", "message": "No images downloaded"}
    
    # Migliora
    enhanced = await enhancer.enhance_images(downloaded)
    
    # Salva
    item_dir = IMAGES_DIR / item_id
    item_dir.mkdir(exist_ok=True)
    
    paths = []
    for i, img in enumerate(enhanced):
        path = item_dir / f"enhanced_{i}.jpg"
        with open(path, "wb") as f:
            f.write(img)
        paths.append(str(path))
    
    return {"status": "success", "paths": paths}
