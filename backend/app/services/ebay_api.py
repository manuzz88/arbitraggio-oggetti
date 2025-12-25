"""
eBay Browse API - API ufficiale per prezzi di mercato
Documentazione: https://developer.ebay.com/api-docs/buy/browse/overview.html
"""
import httpx
import base64
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger

from app.config import settings


@dataclass
class EbayPrice:
    """Prezzo da eBay"""
    item_id: str
    title: str
    price: float
    currency: str
    condition: str  # NEW, USED, REFURBISHED
    sold: bool
    sold_date: Optional[datetime] = None
    image_url: Optional[str] = None
    item_url: Optional[str] = None
    seller_feedback: Optional[int] = None


@dataclass
class EbayMarketData:
    """Dati di mercato da eBay API"""
    query: str
    sold_items: List[EbayPrice]
    active_items: List[EbayPrice]
    
    @property
    def avg_sold_price(self) -> Optional[float]:
        if not self.sold_items:
            return None
        return sum(p.price for p in self.sold_items) / len(self.sold_items)
    
    @property
    def min_sold_price(self) -> Optional[float]:
        if not self.sold_items:
            return None
        return min(p.price for p in self.sold_items)
    
    @property
    def max_sold_price(self) -> Optional[float]:
        if not self.sold_items:
            return None
        return max(p.price for p in self.sold_items)
    
    @property
    def avg_active_price(self) -> Optional[float]:
        if not self.active_items:
            return None
        return sum(p.price for p in self.active_items) / len(self.active_items)
    
    def to_prompt_context(self) -> str:
        """Genera contesto per il prompt AI"""
        lines = [f"📊 DATI eBay API UFFICIALE per '{self.query}':"]
        
        if self.sold_items:
            # Separa usato e nuovo
            used_sold = [p for p in self.sold_items if p.condition in ['USED', 'USED_EXCELLENT', 'USED_GOOD', 'USED_ACCEPTABLE']]
            new_sold = [p for p in self.sold_items if p.condition in ['NEW', 'NEW_WITH_TAGS', 'NEW_WITHOUT_TAGS']]
            
            if used_sold:
                avg = sum(p.price for p in used_sold) / len(used_sold)
                min_p = min(p.price for p in used_sold)
                max_p = max(p.price for p in used_sold)
                lines.append(f"\n🔄 eBay VENDUTI USATO ({len(used_sold)} vendite):")
                lines.append(f"   - Media: €{avg:.0f}")
                lines.append(f"   - Range: €{min_p:.0f} - €{max_p:.0f}")
            
            if new_sold:
                avg = sum(p.price for p in new_sold) / len(new_sold)
                lines.append(f"\n🆕 eBay VENDUTI NUOVO ({len(new_sold)} vendite):")
                lines.append(f"   - Media: €{avg:.0f}")
        
        if self.active_items:
            used_active = [p for p in self.active_items if 'USED' in p.condition.upper()]
            if used_active:
                avg = sum(p.price for p in used_active) / len(used_active)
                min_p = min(p.price for p in used_active)
                lines.append(f"\n📦 eBay ATTIVI USATO ({len(used_active)} inserzioni):")
                lines.append(f"   - Prezzo più basso: €{min_p:.0f}")
                lines.append(f"   - Media richiesta: €{avg:.0f}")
        
        if not self.sold_items and not self.active_items:
            lines.append("\n⚠️ Nessun dato eBay trovato")
        
        return "\n".join(lines)


class EbayBrowseAPI:
    """
    Client per eBay Browse API ufficiale
    
    Per ottenere le credenziali:
    1. Vai su https://developer.ebay.com/
    2. Crea un'applicazione
    3. Ottieni Client ID e Client Secret
    4. Aggiungi al .env: EBAY_CLIENT_ID e EBAY_CLIENT_SECRET
    """
    
    # Endpoints
    AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    BROWSE_URL = "https://api.ebay.com/buy/browse/v1"
    
    # Sandbox per test
    SANDBOX_AUTH_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    SANDBOX_BROWSE_URL = "https://api.sandbox.ebay.com/buy/browse/v1"
    
    def __init__(self, sandbox: bool = False):
        self.client_id = settings.EBAY_CLIENT_ID
        self.client_secret = settings.EBAY_CLIENT_SECRET
        self.sandbox = sandbox
        self.access_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        self.client: Optional[httpx.AsyncClient] = None
        
        # Scegli endpoint
        if sandbox:
            self.auth_url = self.SANDBOX_AUTH_URL
            self.browse_url = self.SANDBOX_BROWSE_URL
        else:
            self.auth_url = self.AUTH_URL
            self.browse_url = self.BROWSE_URL
    
    async def start(self):
        """Inizializza il client e ottieni token"""
        self.client = httpx.AsyncClient(timeout=30.0)
        
        if self.client_id and self.client_secret:
            await self._get_access_token()
            logger.info("EbayBrowseAPI started with authentication")
        else:
            logger.warning("EbayBrowseAPI: No credentials, API calls will fail. Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET")
    
    async def stop(self):
        """Chiudi il client"""
        if self.client:
            await self.client.aclose()
        logger.info("EbayBrowseAPI stopped")
    
    async def _get_access_token(self) -> bool:
        """Ottieni OAuth2 access token"""
        if not self.client_id or not self.client_secret:
            return False
        
        # Controlla se token ancora valido
        if self.access_token and self.token_expires:
            if datetime.now() < self.token_expires - timedelta(minutes=5):
                return True
        
        try:
            # Crea credenziali base64
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded = base64.b64encode(credentials.encode()).decode()
            
            response = await self.client.post(
                self.auth_url,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {encoded}"
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                expires_in = data.get("expires_in", 7200)
                self.token_expires = datetime.now() + timedelta(seconds=expires_in)
                logger.info(f"eBay OAuth token obtained, expires in {expires_in}s")
                return True
            else:
                logger.error(f"eBay OAuth failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"eBay OAuth error: {e}")
            return False
    
    async def search_items(
        self,
        query: str,
        limit: int = 20,
        filter_sold: bool = False,
        condition: str = None,  # NEW, USED
        min_price: float = None,
        max_price: float = None
    ) -> List[EbayPrice]:
        """
        Cerca items su eBay
        
        Args:
            query: Termine di ricerca
            limit: Max risultati (max 200)
            filter_sold: Se True, cerca solo venduti (richiede API avanzata)
            condition: NEW, USED, REFURBISHED
            min_price: Prezzo minimo
            max_price: Prezzo massimo
        """
        if not self.access_token:
            if not await self._get_access_token():
                logger.warning("No eBay access token, skipping search")
                return []
        
        try:
            # Costruisci filtri
            filters = []
            if condition:
                filters.append(f"conditions:{{{condition}}}")
            if min_price:
                filters.append(f"price:[{min_price}..{max_price or ''}],priceCurrency:EUR")
            
            params = {
                "q": query,
                "limit": min(limit, 200),
                "filter": ",".join(filters) if filters else None
            }
            
            # Rimuovi None
            params = {k: v for k, v in params.items() if v is not None}
            
            response = await self.client.get(
                f"{self.browse_url}/item_summary/search",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_IT",  # eBay Italia
                    "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=IT"
                },
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("itemSummaries", [])
                
                prices = []
                for item in items:
                    try:
                        price_info = item.get("price", {})
                        price = float(price_info.get("value", 0))
                        
                        # Condizione
                        cond = item.get("condition", "USED")
                        if isinstance(cond, dict):
                            cond = cond.get("conditionId", "USED")
                        
                        prices.append(EbayPrice(
                            item_id=item.get("itemId", ""),
                            title=item.get("title", ""),
                            price=price,
                            currency=price_info.get("currency", "EUR"),
                            condition=str(cond).upper(),
                            sold=False,
                            image_url=item.get("image", {}).get("imageUrl"),
                            item_url=item.get("itemWebUrl"),
                            seller_feedback=item.get("seller", {}).get("feedbackPercentage")
                        ))
                    except Exception as e:
                        continue
                
                logger.info(f"eBay API: found {len(prices)} items for '{query}'")
                return prices
                
            elif response.status_code == 401:
                # Token scaduto, riprova
                self.access_token = None
                if await self._get_access_token():
                    return await self.search_items(query, limit, filter_sold, condition, min_price, max_price)
            else:
                logger.error(f"eBay API error: {response.status_code} - {response.text[:200]}")
                
        except Exception as e:
            logger.error(f"eBay API search error: {e}")
        
        return []
    
    async def get_market_data(self, query: str) -> EbayMarketData:
        """
        Ottieni dati di mercato completi per un prodotto
        Cerca sia items attivi che (se possibile) venduti
        """
        # Cerca items attivi usati
        active_used = await self.search_items(query, limit=15, condition="USED")
        
        # Cerca items attivi nuovi per confronto
        active_new = await self.search_items(query, limit=10, condition="NEW")
        
        # Combina risultati
        all_active = active_used + active_new
        
        # Nota: eBay Browse API non supporta direttamente "sold items"
        # Per quello serve eBay Finding API (deprecata) o scraping
        # Usiamo i prezzi attivi come riferimento
        
        return EbayMarketData(
            query=query,
            sold_items=[],  # Richiede API diversa
            active_items=all_active
        )


# Singleton
ebay_api = EbayBrowseAPI()
