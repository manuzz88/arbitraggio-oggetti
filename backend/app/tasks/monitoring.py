import asyncio
from datetime import datetime
from loguru import logger

from app.tasks import celery_app
from app.services.scraper.subito import SubitoScraper
from app.services.platforms.ebay import EbayService
from app.database import AsyncSessionLocal
from app.models.item import Item, ItemStatus
from app.models.listing import Listing, ListingStatus
from app.models.order import Order, OrderStatus
from app.models.availability_check import AvailabilityCheck
from app.config import settings


@celery_app.task(bind=True)
def check_all_availability(self):
    """
    Verifica disponibilità di tutti gli items listati.
    Se un item non è più disponibile, rimuove il listing.
    """
    logger.info("Starting availability check for all listed items")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_check_availability_async())


async def _check_availability_async():
    """Versione async del check disponibilità"""
    scraper = SubitoScraper()
    unavailable_count = 0
    checked_count = 0
    
    try:
        await scraper.start()
        
        async with AsyncSessionLocal() as db:
            # Trova tutti gli items listati
            result = await db.execute(
                "SELECT id, source_url, source_platform FROM items WHERE status = 'listed'"
            )
            items = result.fetchall()
            
            for item in items:
                item_id = item[0]
                source_url = item[1]
                platform = item[2]
                
                try:
                    # Check disponibilità
                    if platform == "subito":
                        is_available = await scraper.check_availability(source_url)
                    else:
                        is_available = True  # Skip per altre piattaforme
                    
                    # Salva check
                    check = AvailabilityCheck(
                        item_id=item_id,
                        is_available=is_available,
                    )
                    db.add(check)
                    
                    checked_count += 1
                    
                    if not is_available:
                        logger.warning(f"Item {item_id} no longer available!")
                        unavailable_count += 1
                        
                        # Aggiorna status item
                        await db.execute(
                            f"UPDATE items SET status = 'unavailable' WHERE id = '{item_id}'"
                        )
                        
                        # Termina listings attivi
                        await db.execute(
                            f"UPDATE listings SET status = 'ended' WHERE item_id = '{item_id}' AND status = 'active'"
                        )
                        
                        # TODO: Rimuovi da eBay via API
                    
                    await db.commit()
                    
                    # Delay tra check
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error checking item {item_id}: {e}")
                    continue
        
        logger.info(f"Availability check completed. Checked: {checked_count}, Unavailable: {unavailable_count}")
        return {
            "status": "success",
            "checked": checked_count,
            "unavailable": unavailable_count
        }
        
    except Exception as e:
        logger.error(f"Availability check failed: {e}")
        raise
    finally:
        await scraper.stop()


@celery_app.task(bind=True)
def check_single_availability(self, item_id: str):
    """Check disponibilità di un singolo item"""
    logger.info(f"Checking availability for item {item_id}")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_check_single_async(item_id))


async def _check_single_async(item_id: str):
    """Versione async per singolo check"""
    scraper = SubitoScraper()
    
    try:
        await scraper.start()
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                f"SELECT source_url, source_platform FROM items WHERE id = '{item_id}'"
            )
            item = result.fetchone()
            
            if not item:
                return {"status": "error", "message": "Item not found"}
            
            source_url, platform = item
            
            if platform == "subito":
                is_available = await scraper.check_availability(source_url)
            else:
                is_available = True
            
            # Salva check
            check = AvailabilityCheck(
                item_id=item_id,
                is_available=is_available,
            )
            db.add(check)
            await db.commit()
            
            return {
                "status": "success",
                "item_id": item_id,
                "is_available": is_available
            }
            
    finally:
        await scraper.stop()


@celery_app.task(bind=True)
def sync_ebay_orders(self):
    """
    Sincronizza ordini da eBay.
    Crea nuovi ordini nel database quando vengono ricevuti su eBay.
    """
    logger.info("Syncing eBay orders")
    
    if not settings.EBAY_APP_ID:
        logger.warning("eBay API not configured, skipping order sync")
        return {"status": "skipped", "reason": "eBay not configured"}
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_sync_orders_async())


async def _sync_orders_async():
    """Versione async per sync ordini"""
    ebay = EbayService()
    new_orders = 0
    
    try:
        # Ottieni ordini da eBay
        orders_response = await ebay.get_orders(limit=50)
        orders = orders_response.get("orders", [])
        
        async with AsyncSessionLocal() as db:
            for ebay_order in orders:
                order_id = ebay_order.get("orderId")
                
                # Verifica se esiste già
                result = await db.execute(
                    f"SELECT id FROM orders WHERE platform_order_id = '{order_id}'"
                )
                if result.scalar():
                    continue
                
                # Trova il listing corrispondente
                line_items = ebay_order.get("lineItems", [])
                if not line_items:
                    continue
                
                sku = line_items[0].get("sku")
                if not sku:
                    continue
                
                result = await db.execute(
                    f"SELECT id, item_id FROM listings WHERE id = '{sku}'"
                )
                listing = result.fetchone()
                
                if not listing:
                    continue
                
                listing_id, item_id = listing
                
                # Crea ordine
                price_summary = ebay_order.get("pricingSummary", {})
                total = price_summary.get("total", {}).get("value", 0)
                
                order = Order(
                    listing_id=listing_id,
                    platform_order_id=order_id,
                    sale_price=float(total),
                    status=OrderStatus.PENDING_PURCHASE,
                    buyer_username=ebay_order.get("buyer", {}).get("username"),
                    buyer_info=ebay_order.get("buyer"),
                    shipping_address=ebay_order.get("fulfillmentStartInstructions", [{}])[0].get("shippingStep", {}).get("shipTo"),
                    sold_at=datetime.utcnow(),
                )
                
                db.add(order)
                new_orders += 1
                
                # Aggiorna listing status
                await db.execute(
                    f"UPDATE listings SET status = 'sold', sold_at = '{datetime.utcnow()}' WHERE id = '{listing_id}'"
                )
                
                # Aggiorna item status
                await db.execute(
                    f"UPDATE items SET status = 'sold' WHERE id = '{item_id}'"
                )
            
            await db.commit()
        
        logger.info(f"eBay order sync completed. New orders: {new_orders}")
        return {"status": "success", "new_orders": new_orders}
        
    except Exception as e:
        logger.error(f"eBay order sync failed: {e}")
        raise
    finally:
        await ebay.close()


@celery_app.task(bind=True)
def update_listing_stats(self):
    """Aggiorna statistiche dei listing (views, watchers)"""
    logger.info("Updating listing stats from eBay")
    
    if not settings.EBAY_APP_ID:
        return {"status": "skipped"}
    
    # TODO: Implementare chiamata API eBay per ottenere stats
    return {"status": "not_implemented"}
