"""
Scraper per Subito.it usando ScraperAPI per bypassare protezioni anti-bot.
"""
import httpx
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, quote
from bs4 import BeautifulSoup
from loguru import logger

from app.config import settings


class SubitoScraperAPI:
    """Scraper per Subito.it tramite ScraperAPI"""
    
    BASE_URL = "https://www.subito.it"
    SCRAPER_API_URL = "https://api.scraperapi.com"
    
    def __init__(self):
        self.api_key = settings.SCRAPER_API_KEY
        self.client: Optional[httpx.AsyncClient] = None
        
        if not self.api_key:
            raise ValueError("SCRAPER_API_KEY not configured in .env")
    
    async def start(self):
        """Inizializza il client HTTP"""
        self.client = httpx.AsyncClient(timeout=60.0)
        logger.info("SubitoScraperAPI started")
    
    async def stop(self):
        """Chiude il client"""
        if self.client:
            await self.client.aclose()
            logger.info("SubitoScraperAPI stopped")
    
    async def _fetch_with_scraperapi(self, url: str, render_js: bool = True) -> Optional[str]:
        """
        Fetch una pagina tramite ScraperAPI
        
        Args:
            url: URL da scrapare
            render_js: Se True, esegue JavaScript (necessario per siti dinamici)
        """
        if not self.client:
            await self.start()
        
        params = {
            "api_key": self.api_key,
            "url": url,
            "country_code": "it",  # IP italiano
        }
        
        if render_js:
            params["render"] = "true"
        
        try:
            logger.debug(f"Fetching via ScraperAPI: {url}")
            response = await self.client.get(self.SCRAPER_API_URL, params=params)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"ScraperAPI returned {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"ScraperAPI request failed: {e}")
            return None
    
    def _build_search_url(self, query: str, page: int = 1) -> str:
        """Costruisce URL di ricerca per Subito.it"""
        params = {
            "q": query,
        }
        if page > 1:
            params["o"] = page
        
        return f"{self.BASE_URL}/annunci-italia/vendita/usato/?{urlencode(params)}"
    
    async def search(self, query: str, max_pages: int = 1) -> List[Dict[str, Any]]:
        """
        Cerca prodotti su Subito.it
        
        Args:
            query: Termine di ricerca
            max_pages: Numero massimo di pagine da scrapare
            
        Returns:
            Lista di items trovati
        """
        logger.info(f"Searching Subito.it for: {query}")
        all_items = []
        
        for page in range(1, max_pages + 1):
            url = self._build_search_url(query, page)
            logger.info(f"Scraping page {page}: {url}")
            
            html = await self._fetch_with_scraperapi(url)
            
            if not html:
                logger.warning(f"Failed to fetch page {page}")
                break
            
            items = self._parse_search_results(html)
            
            if not items:
                logger.info(f"No more items found on page {page}")
                break
            
            all_items.extend(items)
            logger.info(f"Found {len(items)} items on page {page}")
        
        logger.info(f"Total items found: {len(all_items)}")
        return all_items
    
    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Parsa i risultati della ricerca da __NEXT_DATA__ JSON"""
        items = []
        
        # Subito.it usa Next.js - i dati sono in __NEXT_DATA__
        import re
        import json
        
        match = re.search(r'__NEXT_DATA__[^>]*>({.*?})</script>', html, re.DOTALL)
        if not match:
            logger.warning("Could not find __NEXT_DATA__ in HTML")
            return items
        
        try:
            data = json.loads(match.group(1))
            items_list = data.get('props', {}).get('pageProps', {}).get('initialState', {}).get('items', {}).get('list', [])
            
            logger.info(f"Found {len(items_list)} items in __NEXT_DATA__")
            
            for wrapper in items_list:
                try:
                    item_data = wrapper.get('item', {})
                    if not item_data:
                        continue
                    
                    # Estrai dati base
                    subject = item_data.get('subject', '')
                    if not subject:
                        continue
                    
                    # Estrai ID dall'URN (formato: id:ad:uuid:list:123456789)
                    urn = item_data.get('urn', '')
                    parts = urn.split(':')
                    item_id = parts[-1] if parts else ''
                    
                    # Estrai prezzo da features
                    price = 0.0
                    features = item_data.get('features', {})
                    if isinstance(features, dict):
                        price_feature = features.get('/price', {})
                        if price_feature:
                            values = price_feature.get('values', [])
                            if values:
                                price_str = values[0].get('key', '0')
                                try:
                                    price = float(price_str.replace(',', '.'))
                                except:
                                    pass
                    
                    # Estrai immagini
                    img_urls = []
                    images = item_data.get('images', [])
                    for img in images[:5]:
                        if isinstance(img, dict):
                            # Subito usa cdnBaseUrl per le immagini
                            cdn_url = img.get('cdnBaseUrl', '')
                            if cdn_url:
                                # Usa rule=gallery-mobile-2x-auto per immagini accessibili
                                img_urls.append(f"{cdn_url}?rule=gallery-mobile-2x-auto")
                    
                    # Estrai URL
                    urls = item_data.get('urls', {})
                    detail_url = urls.get('default', '') if isinstance(urls, dict) else ''
                    
                    # Estrai location
                    geo = item_data.get('geo', {})
                    location = ''
                    if isinstance(geo, dict):
                        city = geo.get('city', {})
                        if isinstance(city, dict):
                            location = city.get('value', '')
                    
                    # Estrai descrizione
                    body = item_data.get('body', '')
                    
                    # Estrai condizione
                    condition = ''
                    if isinstance(features, dict):
                        cond_feature = features.get('/item_condition', {})
                        if cond_feature:
                            values = cond_feature.get('values', [])
                            if values:
                                condition = values[0].get('value', '')
                    
                    items.append({
                        "source_id": f"subito_{item_id}",
                        "source_url": detail_url,
                        "original_title": subject,
                        "original_description": body,
                        "original_price": price,
                        "original_currency": "EUR",
                        "original_images": img_urls,
                        "original_location": location,
                        "seller_info": {
                            "condition": condition,
                        },
                    })
                    
                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue
                    
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse __NEXT_DATA__ JSON: {e}")
        
        return items
    
    async def get_item_details(self, url: str) -> Optional[Dict[str, Any]]:
        """Ottiene dettagli completi di un annuncio"""
        html = await self._fetch_with_scraperapi(url)
        
        if not html:
            return None
        
        soup = BeautifulSoup(html, "lxml")
        
        try:
            # Titolo
            title_elem = soup.select_one("h1")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Descrizione
            desc_elem = soup.select_one('[class*="description"]')
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Prezzo
            price = 0.0
            price_elem = soup.select_one('[class*="price"]')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_text = price_text.replace("€", "").replace(".", "").replace(",", ".").strip()
                try:
                    price = float(price_text)
                except:
                    pass
            
            # Immagini
            images = []
            for img in soup.select('img[src*="images.subito"]'):
                src = img.get("src")
                if src:
                    # Prendi versione alta qualità
                    src = src.replace("/thumbs/", "/images/")
                    images.append(src)
            
            # Location
            location = ""
            loc_elem = soup.select_one('[class*="location"]')
            if loc_elem:
                location = loc_elem.get_text(strip=True)
            
            # Estrai ID dall'URL
            item_id = url.split("-")[-1].replace(".htm", "")
            
            return {
                "source_id": f"subito_{item_id}",
                "source_url": url,
                "original_title": title,
                "original_description": description,
                "original_price": price,
                "original_currency": "EUR",
                "original_images": images[:5],
                "original_location": location,
                "seller_info": {},
            }
            
        except Exception as e:
            logger.error(f"Error parsing item details: {e}")
            return None
    
    async def check_availability(self, url: str) -> bool:
        """Verifica se un annuncio è ancora disponibile"""
        html = await self._fetch_with_scraperapi(url, render_js=False)
        
        if not html:
            return False
        
        # Se la pagina contiene "annuncio non disponibile" o redirect
        if "non disponibile" in html.lower() or "annuncio rimosso" in html.lower():
            return False
        
        return True
