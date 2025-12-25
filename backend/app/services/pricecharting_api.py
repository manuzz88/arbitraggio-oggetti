"""
PriceCharting API - Prezzi per videogiochi, console, retrogaming, LEGO
Documentazione: https://www.pricecharting.com/api-documentation

API gratuita per uso base, ottima per:
- Videogiochi (tutte le console)
- Console e accessori
- Amiibo
- LEGO sets
"""
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from loguru import logger

from app.config import settings


@dataclass
class PriceChartingPrice:
    """Prezzo da PriceCharting"""
    product_id: str
    product_name: str
    console: str  # es: "Nintendo Switch", "PlayStation 5"
    
    # Prezzi in USD (PriceCharting usa USD)
    loose_price: Optional[float] = None  # Solo gioco/item
    cib_price: Optional[float] = None    # Complete In Box
    new_price: Optional[float] = None    # Nuovo sigillato
    
    # Prezzi convertiti in EUR (approssimativo)
    loose_price_eur: Optional[float] = None
    cib_price_eur: Optional[float] = None
    new_price_eur: Optional[float] = None
    
    product_url: Optional[str] = None


@dataclass
class PriceChartingResult:
    """Risultato ricerca PriceCharting"""
    query: str
    products: List[PriceChartingPrice]
    
    @property
    def best_match(self) -> Optional[PriceChartingPrice]:
        """Ritorna il prodotto più rilevante"""
        return self.products[0] if self.products else None
    
    @property
    def avg_loose_eur(self) -> Optional[float]:
        prices = [p.loose_price_eur for p in self.products if p.loose_price_eur]
        return sum(prices) / len(prices) if prices else None
    
    @property
    def avg_cib_eur(self) -> Optional[float]:
        prices = [p.cib_price_eur for p in self.products if p.cib_price_eur]
        return sum(prices) / len(prices) if prices else None
    
    def to_prompt_context(self) -> str:
        """Genera contesto per il prompt AI"""
        if not self.products:
            return ""
        
        lines = [f"🎮 PRICECHARTING (Gaming/Retro) per '{self.query}':"]
        
        best = self.best_match
        if best:
            lines.append(f"\n   Prodotto: {best.product_name}")
            lines.append(f"   Console: {best.console}")
            
            if best.loose_price_eur:
                lines.append(f"   💿 Solo gioco (loose): €{best.loose_price_eur:.0f}")
            if best.cib_price_eur:
                lines.append(f"   📦 Completo (CIB): €{best.cib_price_eur:.0f}")
            if best.new_price_eur:
                lines.append(f"   🆕 Nuovo sigillato: €{best.new_price_eur:.0f}")
        
        if len(self.products) > 1:
            lines.append(f"\n   ({len(self.products)} prodotti simili trovati)")
        
        return "\n".join(lines)


class PriceChartingAPI:
    """
    Client per PriceCharting API
    
    L'API è gratuita per uso base.
    Per uso commerciale/alto volume: https://www.pricecharting.com/api-documentation
    """
    
    # Scraping della pagina pubblica (gratis)
    SEARCH_URL = "https://www.pricecharting.com/search-products"
    
    # Tasso di cambio USD -> EUR (approssimativo)
    USD_TO_EUR = 0.92
    
    # Categorie supportate
    GAMING_KEYWORDS = [
        'nintendo', 'switch', 'playstation', 'ps5', 'ps4', 'ps3', 'ps2', 'ps1',
        'xbox', 'game', 'gioco', 'videogioco', 'console', 'controller',
        'gameboy', 'game boy', 'ds', '3ds', 'wii', 'gamecube', 'n64',
        'sega', 'mega drive', 'dreamcast', 'saturn', 'atari',
        'amiibo', 'pokemon', 'zelda', 'mario', 'sonic',
        'retro', 'vintage', 'lego', 'set lego'
    ]
    
    def __init__(self):
        self.scraper_api_key = getattr(settings, 'SCRAPER_API_KEY', None)
        self.client: Optional[httpx.AsyncClient] = None
    
    async def start(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info("PriceChartingAPI started (using web scraping)")
    
    async def stop(self):
        if self.client:
            await self.client.aclose()
        logger.info("PriceChartingAPI stopped")
    
    def is_gaming_product(self, title: str) -> bool:
        """Verifica se il prodotto è gaming/retro (adatto per PriceCharting)"""
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in self.GAMING_KEYWORDS)
    
    async def search(self, query: str, limit: int = 5) -> PriceChartingResult:
        """
        Cerca un prodotto su PriceCharting tramite scraping
        
        Args:
            query: Nome del prodotto (es: "Super Mario Odyssey")
            limit: Max risultati
        """
        if not self.client:
            await self.start()
        
        products = []
        
        try:
            # Usa ScraperAPI per evitare blocchi
            search_url = f"https://www.pricecharting.com/search-products?q={query.replace(' ', '+')}&type=videogames"
            
            if self.scraper_api_key:
                response = await self.client.get(
                    "https://api.scraperapi.com",
                    params={
                        "api_key": self.scraper_api_key,
                        "url": search_url,
                        "render": "false"
                    }
                )
            else:
                response = await self.client.get(search_url)
            
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                import re
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Cerca le righe della tabella #games_table
                rows = soup.select('table#games_table tr')
                
                for row in rows[:limit + 1]:  # +1 per header
                    try:
                        # Salta header
                        if row.select_one('th'):
                            continue
                        
                        # Titolo e link
                        title_el = row.select_one('td.title a')
                        if not title_el:
                            continue
                        
                        product_name = title_el.get_text(strip=True)
                        product_url = title_el.get('href', '')
                        product_id = product_url.split('/')[-1] if product_url else ''
                        
                        # Console (dal URL: /game/nintendo-switch/...)
                        console = ''
                        if '/game/' in product_url:
                            parts = product_url.split('/game/')[-1].split('/')
                            if parts:
                                console = parts[0].replace('-', ' ').title()
                        
                        # Prezzi - cerca span.js-price nelle celle
                        price_spans = row.select('span.js-price')
                        
                        loose = None
                        cib = None
                        new = None
                        
                        for i, span in enumerate(price_spans[:3]):
                            price_text = span.get_text(strip=True)
                            # Estrai numero dal prezzo (es: "$45.99" -> 45.99)
                            match = re.search(r'\$?([\d,]+\.?\d*)', price_text.replace(',', ''))
                            if match:
                                price = float(match.group(1))
                                if i == 0:
                                    loose = price
                                elif i == 1:
                                    cib = price
                                elif i == 2:
                                    new = price
                        
                        # Converti in EUR
                        loose_eur = loose * self.USD_TO_EUR if loose else None
                        cib_eur = cib * self.USD_TO_EUR if cib else None
                        new_eur = new * self.USD_TO_EUR if new else None
                        
                        products.append(PriceChartingPrice(
                            product_id=product_id,
                            product_name=product_name,
                            console=console,
                            loose_price=loose,
                            cib_price=cib,
                            new_price=new,
                            loose_price_eur=loose_eur,
                            cib_price_eur=cib_eur,
                            new_price_eur=new_eur,
                            product_url=product_url if product_url.startswith('http') else f"https://www.pricecharting.com{product_url}"
                        ))
                        
                    except Exception as e:
                        logger.warning(f"Error parsing PriceCharting row: {e}")
                        continue
                
                logger.info(f"PriceCharting: found {len(products)} products for '{query}'")
                
            else:
                logger.warning(f"PriceCharting scraping error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"PriceCharting search error: {e}")
        
        return PriceChartingResult(query=query, products=products)
    
    async def get_product_prices(self, product_id: str) -> Optional[PriceChartingPrice]:
        """
        Ottieni prezzi dettagliati per un prodotto specifico
        """
        if not self.client:
            await self.start()
        
        try:
            params = {"id": product_id, "format": "json"}
            if self.api_key:
                params["api-key"] = self.api_key
            
            response = await self.client.get(
                f"{self.BASE_URL}/product",
                params=params
            )
            
            if response.status_code == 200:
                item = response.json()
                
                loose = item.get("loose-price", 0) / 100 if item.get("loose-price") else None
                cib = item.get("cib-price", 0) / 100 if item.get("cib-price") else None
                new = item.get("new-price", 0) / 100 if item.get("new-price") else None
                
                return PriceChartingPrice(
                    product_id=str(item.get("id", "")),
                    product_name=item.get("product-name", ""),
                    console=item.get("console-name", ""),
                    loose_price=loose,
                    cib_price=cib,
                    new_price=new,
                    loose_price_eur=loose * self.USD_TO_EUR if loose else None,
                    cib_price_eur=cib * self.USD_TO_EUR if cib else None,
                    new_price_eur=new * self.USD_TO_EUR if new else None,
                    product_url=f"https://www.pricecharting.com/game/{product_id}"
                )
                
        except Exception as e:
            logger.error(f"PriceCharting get product error: {e}")
        
        return None


# Singleton
pricecharting_api = PriceChartingAPI()
