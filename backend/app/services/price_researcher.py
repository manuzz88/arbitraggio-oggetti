"""
Price Researcher - Ricerca prezzi di mercato da multiple fonti
Fornisce dati reali a GPT-4 per stime accurate

Fonti:
- eBay Browse API (ufficiale) - prezzi attivi
- eBay scraping - prezzi venduti
- Amazon scraping
- Google Shopping scraping
"""
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from loguru import logger
import re
import json

from app.config import settings
from app.services.ebay_api import ebay_api, EbayMarketData
from app.services.pricecharting_api import pricecharting_api, PriceChartingResult
from app.services.international_prices import international_prices, InternationalComparison


@dataclass
class PriceData:
    """Dati prezzo da una fonte"""
    source: str
    price: float
    currency: str = "EUR"
    condition: str = "used"  # new, used, refurbished
    url: Optional[str] = None
    title: Optional[str] = None


@dataclass 
class MarketResearch:
    """Risultato ricerca di mercato"""
    query: str
    ebay_sold_prices: List[PriceData]
    ebay_active_prices: List[PriceData]
    amazon_prices: List[PriceData]
    google_shopping_prices: List[PriceData]
    pricecharting: Optional[PriceChartingResult] = None  # Gaming/Retro prices
    international: Optional[InternationalComparison] = None  # Prezzi internazionali
    
    @property
    def avg_ebay_sold(self) -> Optional[float]:
        if not self.ebay_sold_prices:
            return None
        return sum(p.price for p in self.ebay_sold_prices) / len(self.ebay_sold_prices)
    
    @property
    def min_ebay_sold(self) -> Optional[float]:
        if not self.ebay_sold_prices:
            return None
        return min(p.price for p in self.ebay_sold_prices)
    
    @property
    def max_ebay_sold(self) -> Optional[float]:
        if not self.ebay_sold_prices:
            return None
        return max(p.price for p in self.ebay_sold_prices)
    
    @property
    def avg_amazon(self) -> Optional[float]:
        if not self.amazon_prices:
            return None
        return sum(p.price for p in self.amazon_prices) / len(self.amazon_prices)
    
    def to_prompt_context(self) -> str:
        """Genera contesto per il prompt AI"""
        lines = [f"DATI DI MERCATO per '{self.query}':"]
        
        if self.ebay_sold_prices:
            lines.append(f"\n📊 eBay VENDUTI (prezzi reali di vendita):")
            lines.append(f"   - Media: €{self.avg_ebay_sold:.0f}")
            lines.append(f"   - Range: €{self.min_ebay_sold:.0f} - €{self.max_ebay_sold:.0f}")
            lines.append(f"   - Campione: {len(self.ebay_sold_prices)} vendite recenti")
        
        if self.ebay_active_prices:
            avg = sum(p.price for p in self.ebay_active_prices) / len(self.ebay_active_prices)
            lines.append(f"\n📦 eBay ATTIVI (inserzioni correnti):")
            lines.append(f"   - Media richiesta: €{avg:.0f}")
            lines.append(f"   - {len(self.ebay_active_prices)} inserzioni attive")
        
        if self.amazon_prices:
            lines.append(f"\n🛒 Amazon (prezzi nuovo):")
            lines.append(f"   - Media: €{self.avg_amazon:.0f}")
            lines.append(f"   - {len(self.amazon_prices)} risultati")
        
        if self.google_shopping_prices:
            avg = sum(p.price for p in self.google_shopping_prices) / len(self.google_shopping_prices)
            min_p = min(p.price for p in self.google_shopping_prices)
            lines.append(f"\n🔍 Google Shopping:")
            lines.append(f"   - Prezzo più basso: €{min_p:.0f}")
            lines.append(f"   - Media: €{avg:.0f}")
        
        # PriceCharting per gaming/retro
        if self.pricecharting and self.pricecharting.products:
            lines.append(self.pricecharting.to_prompt_context())
        
        # Prezzi internazionali
        if self.international and self.international.prices:
            lines.append(self.international.to_prompt_context())
        
        if not any([self.ebay_sold_prices, self.amazon_prices, self.google_shopping_prices, 
                    self.pricecharting and self.pricecharting.products,
                    self.international and self.international.prices]):
            lines.append("\n⚠️ Nessun dato di mercato trovato - usa la tua conoscenza")
        
        return "\n".join(lines)


class PriceResearcher:
    """Ricerca prezzi da multiple fonti"""
    
    def __init__(self):
        self.scraper_api_key = settings.SCRAPER_API_KEY
        self.client: Optional[httpx.AsyncClient] = None
    
    async def start(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        # Inizializza tutti i servizi
        await ebay_api.start()
        await pricecharting_api.start()
        await international_prices.start()
        logger.info("PriceResearcher started (eBay + PriceCharting + International)")
    
    async def stop(self):
        if self.client:
            await self.client.aclose()
        await ebay_api.stop()
        await pricecharting_api.stop()
        await international_prices.stop()
        logger.info("PriceResearcher stopped")
    
    async def research(self, product_name: str, brand: str = None, model: str = None) -> MarketResearch:
        """
        Ricerca prezzi di mercato per un prodotto
        Usa eBay API ufficiale + PriceCharting (gaming) + scraping per altre fonti
        """
        # Costruisci query di ricerca ottimale
        query = self._build_search_query(product_name, brand, model)
        logger.info(f"Researching prices for: {query}")
        
        # Verifica se è un prodotto gaming/retro per PriceCharting
        is_gaming = pricecharting_api.is_gaming_product(product_name)
        
        # Esegui ricerche in parallelo
        tasks = [
            self._search_ebay_api(query),  # eBay API ufficiale
            self._search_ebay_sold(query),  # Scraping venduti (backup)
            self._search_amazon(query),
            self._search_google_shopping(query),
        ]
        
        # Aggiungi PriceCharting solo per prodotti gaming
        if is_gaming:
            tasks.append(self._search_pricecharting(query))
            logger.info(f"Gaming product detected, adding PriceCharting search")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Gestisci errori
        ebay_api_data = results[0] if not isinstance(results[0], Exception) else None
        ebay_sold = results[1] if not isinstance(results[1], Exception) else []
        amazon = results[2] if not isinstance(results[2], Exception) else []
        google = results[3] if not isinstance(results[3], Exception) else []
        pricecharting_data = None
        if is_gaming and len(results) > 4:
            pricecharting_data = results[4] if not isinstance(results[4], Exception) else None
        
        # Combina dati eBay API con scraping
        ebay_active = []
        if ebay_api_data and ebay_api_data.active_items:
            # Converti da EbayPrice a PriceData
            for item in ebay_api_data.active_items:
                ebay_active.append(PriceData(
                    source="ebay_api",
                    price=item.price,
                    currency=item.currency,
                    condition=item.condition.lower(),
                    url=item.item_url,
                    title=item.title
                ))
            logger.info(f"eBay API: {len(ebay_active)} items found")
        
        return MarketResearch(
            query=query,
            ebay_sold_prices=ebay_sold,
            ebay_active_prices=ebay_active,
            amazon_prices=amazon,
            google_shopping_prices=google,
            pricecharting=pricecharting_data,
            international=None  # Ricerca internazionale separata per performance
        )
    
    async def research_international(self, product_name: str, markets: List[str] = None) -> InternationalComparison:
        """
        Ricerca prezzi internazionali per arbitraggio import/export
        Mercati: IT, US, UK, DE, JP
        """
        query = self._build_search_query(product_name)
        return await international_prices.compare_prices(query, markets)
    
    async def _search_pricecharting(self, query: str) -> Optional[PriceChartingResult]:
        """Cerca prezzi su PriceCharting (gaming/retro)"""
        try:
            return await pricecharting_api.search(query)
        except Exception as e:
            logger.warning(f"PriceCharting search failed: {e}")
            return None
    
    async def _search_ebay_api(self, query: str) -> Optional[EbayMarketData]:
        """Cerca prezzi tramite eBay Browse API ufficiale"""
        try:
            return await ebay_api.get_market_data(query)
        except Exception as e:
            logger.warning(f"eBay API search failed: {e}")
            return None
    
    def _build_search_query(self, product_name: str, brand: str = None, model: str = None) -> str:
        """Costruisce query di ricerca ottimale"""
        # Estrai parole chiave dal titolo
        query = product_name
        
        # Pulisci il titolo
        query = re.sub(r'[^\w\s]', ' ', query)
        query = ' '.join(query.split()[:6])  # Max 6 parole
        
        # Aggiungi brand/model se disponibili e non già presenti
        if brand and brand.lower() not in query.lower():
            query = f"{brand} {query}"
        if model and model.lower() not in query.lower():
            query = f"{query} {model}"
        
        return query.strip()
    
    async def _fetch_with_scraper(self, url: str) -> Optional[str]:
        """Fetch URL tramite ScraperAPI"""
        if not self.client or not self.scraper_api_key:
            return None
        
        try:
            response = await self.client.get(
                "https://api.scraperapi.com",
                params={
                    "api_key": self.scraper_api_key,
                    "url": url,
                    "render": "false"
                }
            )
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.warning(f"Scraper fetch failed for {url}: {e}")
        
        return None
    
    async def _search_ebay_sold(self, query: str) -> List[PriceData]:
        """Cerca prezzi eBay venduti (completati)"""
        prices = []
        
        # eBay Italia - articoli venduti
        url = f"https://www.ebay.it/sch/i.html?_nkw={query.replace(' ', '+')}&LH_Complete=1&LH_Sold=1&_sop=13"
        
        html = await self._fetch_with_scraper(url)
        if not html:
            return prices
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cerca i risultati
            items = soup.select('.s-item')
            
            for item in items[:10]:  # Max 10 risultati
                try:
                    # Prezzo
                    price_el = item.select_one('.s-item__price')
                    if not price_el:
                        continue
                    
                    price_text = price_el.get_text()
                    # Estrai numero dal prezzo (es: "EUR 450,00" -> 450.0)
                    price_match = re.search(r'[\d.,]+', price_text.replace('.', '').replace(',', '.'))
                    if not price_match:
                        continue
                    
                    price = float(price_match.group())
                    if price < 5 or price > 10000:  # Filtra prezzi anomali
                        continue
                    
                    # Titolo
                    title_el = item.select_one('.s-item__title')
                    title = title_el.get_text() if title_el else None
                    
                    # URL
                    link_el = item.select_one('.s-item__link')
                    item_url = link_el.get('href') if link_el else None
                    
                    prices.append(PriceData(
                        source="ebay_sold",
                        price=price,
                        condition="used",
                        url=item_url,
                        title=title
                    ))
                    
                except Exception as e:
                    continue
            
            logger.info(f"eBay sold: found {len(prices)} prices for '{query}'")
            
        except Exception as e:
            logger.error(f"eBay sold parsing error: {e}")
        
        return prices
    
    async def _search_ebay_active(self, query: str) -> List[PriceData]:
        """Cerca prezzi eBay attivi"""
        prices = []
        
        url = f"https://www.ebay.it/sch/i.html?_nkw={query.replace(' ', '+')}&_sop=15"
        
        html = await self._fetch_with_scraper(url)
        if not html:
            return prices
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('.s-item')
            
            for item in items[:8]:
                try:
                    price_el = item.select_one('.s-item__price')
                    if not price_el:
                        continue
                    
                    price_text = price_el.get_text()
                    price_match = re.search(r'[\d.,]+', price_text.replace('.', '').replace(',', '.'))
                    if not price_match:
                        continue
                    
                    price = float(price_match.group())
                    if price < 5 or price > 10000:
                        continue
                    
                    title_el = item.select_one('.s-item__title')
                    title = title_el.get_text() if title_el else None
                    
                    prices.append(PriceData(
                        source="ebay_active",
                        price=price,
                        condition="used",
                        title=title
                    ))
                    
                except:
                    continue
            
            logger.info(f"eBay active: found {len(prices)} prices for '{query}'")
            
        except Exception as e:
            logger.error(f"eBay active parsing error: {e}")
        
        return prices
    
    async def _search_amazon(self, query: str) -> List[PriceData]:
        """Cerca prezzi Amazon (nuovo)"""
        prices = []
        
        url = f"https://www.amazon.it/s?k={query.replace(' ', '+')}"
        
        html = await self._fetch_with_scraper(url)
        if not html:
            return prices
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cerca risultati Amazon
            items = soup.select('[data-component-type="s-search-result"]')
            
            for item in items[:6]:
                try:
                    # Prezzo intero
                    price_whole = item.select_one('.a-price-whole')
                    if not price_whole:
                        continue
                    
                    price_text = price_whole.get_text().replace('.', '').replace(',', '.')
                    price = float(re.sub(r'[^\d.]', '', price_text))
                    
                    # Prezzo decimale
                    price_frac = item.select_one('.a-price-fraction')
                    if price_frac:
                        frac = price_frac.get_text()
                        price += float(f"0.{frac}")
                    
                    if price < 5 or price > 10000:
                        continue
                    
                    # Titolo
                    title_el = item.select_one('h2 span')
                    title = title_el.get_text() if title_el else None
                    
                    prices.append(PriceData(
                        source="amazon",
                        price=price,
                        condition="new",
                        title=title
                    ))
                    
                except:
                    continue
            
            logger.info(f"Amazon: found {len(prices)} prices for '{query}'")
            
        except Exception as e:
            logger.error(f"Amazon parsing error: {e}")
        
        return prices
    
    async def _search_google_shopping(self, query: str) -> List[PriceData]:
        """Cerca prezzi Google Shopping"""
        prices = []
        
        # Google Shopping Italia
        url = f"https://www.google.it/search?q={query.replace(' ', '+')}&tbm=shop&hl=it"
        
        html = await self._fetch_with_scraper(url)
        if not html:
            return prices
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cerca prezzi nei risultati
            # Google Shopping ha struttura variabile, cerchiamo pattern comuni
            price_elements = soup.find_all(string=re.compile(r'€\s*[\d.,]+'))
            
            for price_text in price_elements[:8]:
                try:
                    # Estrai prezzo
                    match = re.search(r'€\s*([\d.,]+)', str(price_text))
                    if not match:
                        continue
                    
                    price_str = match.group(1).replace('.', '').replace(',', '.')
                    price = float(price_str)
                    
                    if price < 5 or price > 10000:
                        continue
                    
                    prices.append(PriceData(
                        source="google_shopping",
                        price=price,
                        condition="new"
                    ))
                    
                except:
                    continue
            
            # Rimuovi duplicati
            seen = set()
            unique_prices = []
            for p in prices:
                if p.price not in seen:
                    seen.add(p.price)
                    unique_prices.append(p)
            
            logger.info(f"Google Shopping: found {len(unique_prices)} prices for '{query}'")
            return unique_prices
            
        except Exception as e:
            logger.error(f"Google Shopping parsing error: {e}")
        
        return prices


# Singleton instance
price_researcher = PriceResearcher()
