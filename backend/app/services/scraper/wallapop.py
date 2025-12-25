import httpx
from typing import List, Dict, Any, Optional
from loguru import logger
import json


class WallapopScraper:
    """Scraper per Wallapop usando le API pubbliche"""
    
    BASE_URL = "https://api.wallapop.com/api/v3"
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
    
    async def start(self):
        """Inizializza il client HTTP"""
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
                "Origin": "https://it.wallapop.com",
                "Referer": "https://it.wallapop.com/",
            },
            timeout=30.0,
            follow_redirects=True,
        )
        logger.info("WallapopScraper started")
    
    async def stop(self):
        """Chiude il client"""
        if self.client:
            await self.client.aclose()
            logger.info("WallapopScraper stopped")
    
    async def search(self, query: str, max_items: int = 40) -> List[Dict[str, Any]]:
        """
        Cerca prodotti su Wallapop
        
        Args:
            query: Termine di ricerca
            max_items: Numero massimo di risultati
            
        Returns:
            Lista di items trovati
        """
        if not self.client:
            await self.start()
        
        logger.info(f"Searching Wallapop for: {query}")
        
        items = []
        
        try:
            # API di ricerca Wallapop
            url = f"{self.BASE_URL}/general/search"
            params = {
                "keywords": query,
                "latitude": 41.9028,  # Roma
                "longitude": 12.4964,
                "filters_source": "quick_filters",
                "order_by": "newest",
            }
            
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                search_objects = data.get("search_objects", [])
                
                logger.info(f"Found {len(search_objects)} items on Wallapop")
                
                for obj in search_objects[:max_items]:
                    try:
                        item = self._parse_item(obj)
                        if item:
                            items.append(item)
                    except Exception as e:
                        logger.warning(f"Error parsing item: {e}")
                        continue
            else:
                logger.warning(f"Wallapop API returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error searching Wallapop: {e}")
        
        return items
    
    def _parse_item(self, obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parsa un oggetto dalla risposta API"""
        try:
            content = obj.get("content", {})
            
            # Estrai immagini
            images = []
            for img in content.get("images", []):
                if "urls" in img:
                    # Prendi la versione large
                    img_url = img["urls"].get("big") or img["urls"].get("medium") or img["urls"].get("small")
                    if img_url:
                        images.append(img_url)
            
            # Estrai prezzo
            price = content.get("price", {})
            price_amount = price.get("amount", 0)
            
            item_id = content.get("id", "")
            
            return {
                "source_id": str(item_id),
                "source_url": f"https://it.wallapop.com/item/{content.get('web_slug', item_id)}",
                "original_title": content.get("title", ""),
                "original_description": content.get("description", ""),
                "original_price": float(price_amount),
                "original_currency": price.get("currency", "EUR"),
                "original_images": images[:5],
                "original_location": content.get("location", {}).get("city", ""),
                "seller_info": {
                    "id": content.get("user", {}).get("id"),
                    "name": content.get("user", {}).get("micro_name"),
                },
            }
        except Exception as e:
            logger.warning(f"Error parsing Wallapop item: {e}")
            return None
    
    async def get_item_details(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Ottiene dettagli di un singolo item"""
        if not self.client:
            await self.start()
        
        try:
            url = f"{self.BASE_URL}/items/{item_id}"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                return self._parse_item({"content": response.json()})
        except Exception as e:
            logger.error(f"Error getting item details: {e}")
        
        return None
    
    async def check_availability(self, item_url: str) -> bool:
        """Verifica se un item è ancora disponibile"""
        if not self.client:
            await self.start()
        
        try:
            response = await self.client.get(item_url)
            return response.status_code == 200 and "sold" not in response.text.lower()
        except:
            return False
