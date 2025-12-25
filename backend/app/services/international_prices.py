"""
International Price Comparison - Confronto prezzi tra mercati internazionali
Supporta: USA, UK, Giappone, Germania, Francia, Italia

Per arbitraggio:
- Import: Comprare all'estero dove costa meno, vendere in Italia
- Export: Comprare in Italia, vendere all'estero dove vale di più
"""
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from loguru import logger
import re

from app.config import settings


@dataclass
class MarketPrice:
    """Prezzo in un mercato specifico"""
    country: str  # IT, US, UK, DE, FR, JP
    country_name: str
    currency: str
    price_local: float  # Prezzo in valuta locale
    price_eur: float  # Prezzo convertito in EUR
    condition: str = "used"  # new, used
    source: str = "ebay"  # ebay, amazon
    url: Optional[str] = None
    title: Optional[str] = None
    shipping_to_italy: Optional[float] = None  # Stima spedizione verso Italia


@dataclass
class InternationalComparison:
    """Confronto prezzi internazionale"""
    query: str
    italy_price: Optional[MarketPrice] = None
    prices: List[MarketPrice] = field(default_factory=list)
    
    @property
    def cheapest_market(self) -> Optional[MarketPrice]:
        """Mercato più economico"""
        if not self.prices:
            return None
        return min(self.prices, key=lambda p: p.price_eur + (p.shipping_to_italy or 0))
    
    @property
    def most_expensive_market(self) -> Optional[MarketPrice]:
        """Mercato più caro (per export)"""
        if not self.prices:
            return None
        return max(self.prices, key=lambda p: p.price_eur)
    
    def get_import_opportunity(self, italy_sell_price: float) -> Optional[Dict]:
        """
        Calcola opportunità di import (comprare estero, vendere Italia)
        """
        cheapest = self.cheapest_market
        if not cheapest:
            return None
        
        total_cost = cheapest.price_eur + (cheapest.shipping_to_italy or 15)
        
        # Aggiungi dogana se extra-UE
        if cheapest.country in ['US', 'UK', 'JP']:
            # IVA 22% + eventuale dazio (stimato 5%)
            if total_cost > 150:  # Soglia dogana
                total_cost *= 1.27  # +22% IVA + 5% dazio
            else:
                total_cost *= 1.22  # Solo IVA
        
        margin = italy_sell_price - total_cost
        margin_pct = (margin / total_cost) * 100 if total_cost > 0 else 0
        
        return {
            "source_country": cheapest.country_name,
            "buy_price": cheapest.price_eur,
            "shipping": cheapest.shipping_to_italy or 15,
            "customs": total_cost - cheapest.price_eur - (cheapest.shipping_to_italy or 15),
            "total_cost": total_cost,
            "sell_price_italy": italy_sell_price,
            "margin": margin,
            "margin_pct": margin_pct,
            "profitable": margin_pct > 20
        }
    
    def get_export_opportunity(self, italy_buy_price: float) -> Optional[Dict]:
        """
        Calcola opportunità di export (comprare Italia, vendere estero)
        """
        expensive = self.most_expensive_market
        if not expensive or expensive.country == 'IT':
            return None
        
        # Stima spedizione dall'Italia
        shipping_from_italy = 20 if expensive.country in ['US', 'JP'] else 12
        
        # Commissioni marketplace (circa 13%)
        sell_price_net = expensive.price_eur * 0.87
        
        total_revenue = sell_price_net - shipping_from_italy
        margin = total_revenue - italy_buy_price
        margin_pct = (margin / italy_buy_price) * 100 if italy_buy_price > 0 else 0
        
        return {
            "target_country": expensive.country_name,
            "buy_price_italy": italy_buy_price,
            "sell_price_abroad": expensive.price_eur,
            "shipping": shipping_from_italy,
            "fees": expensive.price_eur * 0.13,
            "net_revenue": total_revenue,
            "margin": margin,
            "margin_pct": margin_pct,
            "profitable": margin_pct > 25
        }
    
    def to_prompt_context(self) -> str:
        """Genera contesto per il prompt AI"""
        if not self.prices:
            return ""
        
        lines = [f"\n🌍 CONFRONTO PREZZI INTERNAZIONALE per '{self.query}':"]
        
        # Ordina per prezzo
        sorted_prices = sorted(self.prices, key=lambda p: p.price_eur)
        
        for p in sorted_prices[:5]:
            flag = {"IT": "🇮🇹", "US": "🇺🇸", "UK": "🇬🇧", "DE": "🇩🇪", "FR": "🇫🇷", "JP": "🇯🇵"}.get(p.country, "🌐")
            shipping_info = f" (+€{p.shipping_to_italy:.0f} sped.)" if p.shipping_to_italy else ""
            lines.append(f"   {flag} {p.country_name}: €{p.price_eur:.0f}{shipping_info}")
        
        # Suggerimento
        cheapest = self.cheapest_market
        if cheapest and self.italy_price:
            diff = self.italy_price.price_eur - cheapest.price_eur
            if diff > 20:
                lines.append(f"\n   💡 IMPORT: Risparmio €{diff:.0f} comprando da {cheapest.country_name}")
        
        return "\n".join(lines)


class InternationalPriceService:
    """
    Servizio per confronto prezzi internazionali
    Cerca su eBay di diversi paesi
    """
    
    # Configurazione mercati eBay
    MARKETS = {
        "IT": {
            "name": "Italia",
            "domain": "ebay.it",
            "currency": "EUR",
            "rate_to_eur": 1.0,
            "shipping_to_italy": 0,
        },
        "US": {
            "name": "USA",
            "domain": "ebay.com",
            "currency": "USD",
            "rate_to_eur": 0.92,
            "shipping_to_italy": 25,  # Stima media
        },
        "UK": {
            "name": "Regno Unito",
            "domain": "ebay.co.uk",
            "currency": "GBP",
            "rate_to_eur": 1.17,
            "shipping_to_italy": 15,
        },
        "DE": {
            "name": "Germania",
            "domain": "ebay.de",
            "currency": "EUR",
            "rate_to_eur": 1.0,
            "shipping_to_italy": 10,
        },
        "FR": {
            "name": "Francia",
            "domain": "ebay.fr",
            "currency": "EUR",
            "rate_to_eur": 1.0,
            "shipping_to_italy": 10,
        },
        "JP": {
            "name": "Giappone",
            "domain": "ebay.com",  # eBay Japan usa ebay.com con filtro
            "currency": "JPY",
            "rate_to_eur": 0.0062,
            "shipping_to_italy": 35,
        },
    }
    
    def __init__(self):
        self.scraper_api_key = settings.SCRAPER_API_KEY
        self.client: Optional[httpx.AsyncClient] = None
    
    async def start(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info("InternationalPriceService started")
    
    async def stop(self):
        if self.client:
            await self.client.aclose()
        logger.info("InternationalPriceService stopped")
    
    async def compare_prices(
        self, 
        query: str, 
        markets: List[str] = None,
        condition: str = "used"
    ) -> InternationalComparison:
        """
        Confronta prezzi tra mercati internazionali
        
        Args:
            query: Prodotto da cercare
            markets: Lista codici paese (default: tutti)
            condition: "used" o "new"
        """
        if markets is None:
            markets = ["IT", "US", "UK", "DE", "JP"]
        
        logger.info(f"Comparing international prices for: {query}")
        
        # Cerca in parallelo su tutti i mercati
        tasks = [
            self._search_ebay_market(query, market, condition)
            for market in markets
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        prices = []
        italy_price = None
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Error searching {markets[i]}: {result}")
                continue
            if result:
                prices.append(result)
                if result.country == "IT":
                    italy_price = result
        
        logger.info(f"Found prices in {len(prices)} markets")
        
        return InternationalComparison(
            query=query,
            italy_price=italy_price,
            prices=prices
        )
    
    async def _search_ebay_market(
        self, 
        query: str, 
        country: str,
        condition: str = "used"
    ) -> Optional[MarketPrice]:
        """Cerca prezzo medio su eBay di un paese specifico"""
        
        market = self.MARKETS.get(country)
        if not market:
            return None
        
        try:
            # Costruisci URL eBay
            domain = market["domain"]
            
            # Filtro condizione
            condition_filter = ""
            if condition == "used":
                condition_filter = "&LH_ItemCondition=3000"  # Used
            elif condition == "new":
                condition_filter = "&LH_ItemCondition=1000"  # New
            
            # Per Giappone, usa filtro location
            location_filter = ""
            if country == "JP":
                location_filter = "&LH_PrefLoc=2&_sacat=0"  # International
            
            url = f"https://www.{domain}/sch/i.html?_nkw={query.replace(' ', '+')}&LH_Complete=1&LH_Sold=1{condition_filter}{location_filter}&_sop=13"
            
            # Fetch via ScraperAPI
            if not self.scraper_api_key:
                return None
            
            response = await self.client.get(
                "https://api.scraperapi.com",
                params={
                    "api_key": self.scraper_api_key,
                    "url": url,
                    "render": "false"
                }
            )
            
            if response.status_code != 200:
                return None
            
            # Parse risultati
            soup = BeautifulSoup(response.text, 'html.parser')
            
            prices = []
            items = soup.select('.s-item')
            
            for item in items[:10]:
                try:
                    price_el = item.select_one('.s-item__price')
                    if not price_el:
                        continue
                    
                    price_text = price_el.get_text().strip()
                    
                    # Estrai prezzo numerico - gestisce vari formati
                    # $45.99, £35.00, EUR 40,00, ¥5,000, 40,00 €
                    
                    # Rimuovi simboli valuta
                    price_clean = re.sub(r'[€$£¥]|EUR|USD|GBP|JPY', '', price_text)
                    
                    # Gestisci formato europeo (1.234,56) vs americano (1,234.56)
                    if ',' in price_clean and '.' in price_clean:
                        # Determina quale è il separatore decimale
                        if price_clean.rfind(',') > price_clean.rfind('.'):
                            # Formato europeo: 1.234,56
                            price_clean = price_clean.replace('.', '').replace(',', '.')
                        else:
                            # Formato americano: 1,234.56
                            price_clean = price_clean.replace(',', '')
                    elif ',' in price_clean:
                        # Solo virgola - potrebbe essere decimale (40,00) o migliaia (1,000)
                        if re.search(r',\d{2}$', price_clean):
                            price_clean = price_clean.replace(',', '.')
                        else:
                            price_clean = price_clean.replace(',', '')
                    
                    # Estrai numero
                    match = re.search(r'[\d.]+', price_clean)
                    if not match:
                        continue
                    
                    price_local = float(match.group())
                    
                    if price_local < 5 or price_local > 10000:
                        continue
                    
                    prices.append(price_local)
                    
                except Exception:
                    continue
            
            if not prices:
                return None
            
            # Calcola prezzo medio
            avg_price = sum(prices) / len(prices)
            price_eur = avg_price * market["rate_to_eur"]
            
            logger.info(f"eBay {country}: avg {market['currency']} {avg_price:.0f} = €{price_eur:.0f}")
            
            return MarketPrice(
                country=country,
                country_name=market["name"],
                currency=market["currency"],
                price_local=avg_price,
                price_eur=price_eur,
                condition=condition,
                source="ebay",
                shipping_to_italy=market["shipping_to_italy"]
            )
            
        except Exception as e:
            logger.error(f"Error searching eBay {country}: {e}")
            return None


# Singleton
international_prices = InternationalPriceService()
