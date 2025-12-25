import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, quote_plus
from loguru import logger

from app.services.scraper.base import BaseScraper
from app.config import settings


class SubitoScraper(BaseScraper):
    """Scraper per Subito.it"""
    
    BASE_URL = "https://www.subito.it"
    SEARCH_URL = "https://www.subito.it/annunci-italia/vendita/usato/"
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        max_pages: int = None
    ) -> List[Dict[str, Any]]:
        """
        Cerca prodotti su Subito.it
        
        Args:
            query: Termine di ricerca
            category: Categoria (es: "informatica", "telefonia")
            min_price: Prezzo minimo
            max_price: Prezzo massimo
            max_pages: Numero massimo di pagine da scrapare
        
        Returns:
            Lista di item trovati
        """
        max_pages = max_pages or settings.SCRAPING_MAX_PAGES
        items = []
        
        page = await self.create_page()
        
        try:
            for page_num in range(1, max_pages + 1):
                # Costruisci URL
                url = self._build_search_url(query, category, min_price, max_price, page_num)
                logger.info(f"Scraping Subito page {page_num}: {url}")
                
                await page.goto(url, wait_until="domcontentloaded")
                await self.random_delay()
                
                # Aspetta che i risultati siano caricati
                try:
                    await page.wait_for_selector("[class*='items__item']", timeout=10000)
                except:
                    logger.warning(f"No results found on page {page_num}")
                    break
                
                # Scroll per caricare lazy content
                await self.human_scroll(page)
                
                # Estrai items
                page_items = await self._extract_items(page)
                
                if not page_items:
                    logger.info(f"No more items found, stopping at page {page_num}")
                    break
                
                items.extend(page_items)
                logger.info(f"Found {len(page_items)} items on page {page_num}")
                
                # Delay tra pagine
                await self.random_delay(2, 4)
            
            logger.info(f"Total items found: {len(items)}")
            return items
            
        except Exception as e:
            logger.error(f"Error during Subito search: {e}")
            raise
        finally:
            await page.context.close()
    
    def _build_search_url(
        self,
        query: str,
        category: Optional[str],
        min_price: Optional[float],
        max_price: Optional[float],
        page: int
    ) -> str:
        """Costruisce URL di ricerca"""
        
        # Base URL con query
        url = f"{self.SEARCH_URL}?q={quote_plus(query)}"
        
        # Aggiungi filtri
        if min_price:
            url += f"&ps={int(min_price)}"
        if max_price:
            url += f"&pe={int(max_price)}"
        if page > 1:
            url += f"&o={page}"
        
        return url
    
    async def _extract_items(self, page) -> List[Dict[str, Any]]:
        """Estrae items dalla pagina dei risultati"""
        items = []
        
        # Selettore per gli item (può cambiare, da aggiornare se necessario)
        item_elements = await page.query_selector_all("[class*='items__item'], [class*='ItemCard']")
        
        for element in item_elements:
            try:
                item = await self._parse_item_element(element)
                if item:
                    items.append(item)
            except Exception as e:
                logger.warning(f"Error parsing item: {e}")
                continue
        
        return items
    
    async def _parse_item_element(self, element) -> Optional[Dict[str, Any]]:
        """Parsa un singolo elemento item"""
        try:
            # Link
            link_el = await element.query_selector("a[href*='/annunci/']")
            if not link_el:
                return None
            
            url = await link_el.get_attribute("href")
            if not url.startswith("http"):
                url = self.BASE_URL + url
            
            # Estrai ID dall'URL
            source_id_match = re.search(r'/(\d+)\.htm', url)
            source_id = source_id_match.group(1) if source_id_match else None
            
            # Titolo
            title_el = await element.query_selector("[class*='title'], h2")
            title = await title_el.inner_text() if title_el else "N/A"
            
            # Prezzo
            price_el = await element.query_selector("[class*='price']")
            price_text = await price_el.inner_text() if price_el else "0"
            price = self._parse_price(price_text)
            
            # Immagine
            img_el = await element.query_selector("img")
            image_url = await img_el.get_attribute("src") if img_el else None
            
            # Location
            location_el = await element.query_selector("[class*='town'], [class*='location']")
            location = await location_el.inner_text() if location_el else None
            
            return {
                "source_platform": "subito",
                "source_url": url,
                "source_id": source_id,
                "original_title": title.strip(),
                "original_price": price,
                "original_currency": "EUR",
                "original_images": [image_url] if image_url else [],
                "original_location": location.strip() if location else None,
            }
            
        except Exception as e:
            logger.warning(f"Error parsing item element: {e}")
            return None
    
    def _parse_price(self, price_text: str) -> float:
        """Estrae prezzo numerico dal testo"""
        # Rimuovi tutto tranne numeri e virgola/punto
        price_clean = re.sub(r'[^\d,.]', '', price_text)
        # Sostituisci virgola con punto
        price_clean = price_clean.replace(',', '.')
        
        try:
            return float(price_clean)
        except ValueError:
            return 0.0
    
    async def get_item_details(self, url: str) -> Dict[str, Any]:
        """Ottieni dettagli completi di un annuncio"""
        page = await self.create_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await self.random_delay()
            
            # Titolo
            title_el = await page.query_selector("h1")
            title = await title_el.inner_text() if title_el else "N/A"
            
            # Prezzo
            price_el = await page.query_selector("[class*='price']")
            price_text = await price_el.inner_text() if price_el else "0"
            price = self._parse_price(price_text)
            
            # Descrizione
            desc_el = await page.query_selector("[class*='description']")
            description = await desc_el.inner_text() if desc_el else ""
            
            # Immagini
            images = []
            img_elements = await page.query_selector_all("[class*='gallery'] img, [class*='slider'] img")
            for img in img_elements:
                src = await img.get_attribute("src")
                if src and "placeholder" not in src:
                    images.append(src)
            
            # Location
            location_el = await page.query_selector("[class*='location'], [class*='town']")
            location = await location_el.inner_text() if location_el else None
            
            # Seller info
            seller_el = await page.query_selector("[class*='seller'], [class*='advertiser']")
            seller_name = await seller_el.inner_text() if seller_el else None
            
            # ID
            source_id_match = re.search(r'/(\d+)\.htm', url)
            source_id = source_id_match.group(1) if source_id_match else None
            
            return {
                "source_platform": "subito",
                "source_url": url,
                "source_id": source_id,
                "original_title": title.strip(),
                "original_description": description.strip(),
                "original_price": price,
                "original_currency": "EUR",
                "original_images": images,
                "original_location": location.strip() if location else None,
                "seller_info": {
                    "name": seller_name.strip() if seller_name else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting item details: {e}")
            raise
        finally:
            await page.context.close()
    
    async def check_availability(self, url: str) -> bool:
        """Verifica se l'annuncio è ancora disponibile"""
        page = await self.create_page()
        
        try:
            response = await page.goto(url, wait_until="domcontentloaded")
            
            # Check status code
            if response.status == 404:
                return False
            
            # Check per messaggi "annuncio non disponibile"
            content = await page.content()
            unavailable_patterns = [
                "annuncio non è più disponibile",
                "annuncio è stato rimosso",
                "pagina non trovata",
                "404"
            ]
            
            for pattern in unavailable_patterns:
                if pattern.lower() in content.lower():
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False
        finally:
            await page.context.close()
