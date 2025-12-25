import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger

from app.config import settings


class EbayService:
    """Servizio per interagire con eBay API"""
    
    # URLs
    SANDBOX_API_URL = "https://api.sandbox.ebay.com"
    PRODUCTION_API_URL = "https://api.ebay.com"
    SANDBOX_AUTH_URL = "https://auth.sandbox.ebay.com"
    PRODUCTION_AUTH_URL = "https://auth.ebay.com"
    
    def __init__(self):
        self.app_id = settings.EBAY_APP_ID
        self.cert_id = settings.EBAY_CERT_ID
        self.dev_id = settings.EBAY_DEV_ID
        self.redirect_uri = settings.EBAY_REDIRECT_URI
        self.refresh_token = settings.EBAY_REFRESH_TOKEN
        self.sandbox = settings.EBAY_SANDBOX
        
        self.api_url = self.SANDBOX_API_URL if self.sandbox else self.PRODUCTION_API_URL
        self.auth_url = self.SANDBOX_AUTH_URL if self.sandbox else self.PRODUCTION_AUTH_URL
        
        self._access_token = None
        self._token_expires_at = None
        
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _get_access_token(self) -> str:
        """Ottieni access token (con refresh se necessario)"""
        
        # Se abbiamo un token valido, usalo
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token
        
        if not all([self.app_id, self.cert_id, self.refresh_token]):
            raise ValueError("eBay API credentials not configured")
        
        # Refresh token
        import base64
        credentials = base64.b64encode(f"{self.app_id}:{self.cert_id}".encode()).decode()
        
        response = await self.client.post(
            f"{self.auth_url}/identity/v1/oauth2/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}"
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "scope": "https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.fulfillment"
            }
        )
        
        response.raise_for_status()
        data = response.json()
        
        self._access_token = data["access_token"]
        self._token_expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])
        
        return self._access_token
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Esegui richiesta autenticata"""
        
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Content-Language": "it-IT",
        }
        
        url = f"{self.api_url}{endpoint}"
        
        response = await self.client.request(
            method,
            url,
            headers=headers,
            json=data,
            params=params
        )
        
        if response.status_code >= 400:
            logger.error(f"eBay API error: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        if response.content:
            return response.json()
        return {}
    
    async def create_inventory_item(
        self,
        sku: str,
        title: str,
        description: str,
        price: float,
        quantity: int = 1,
        condition: str = "USED_EXCELLENT",
        category_id: str = None,
        images: List[str] = None,
        item_specifics: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Crea un inventory item su eBay
        
        Args:
            sku: Identificativo univoco (es: UUID dell'item)
            title: Titolo del listing
            description: Descrizione HTML
            price: Prezzo in EUR
            quantity: Quantità disponibile
            condition: Condizione (USED_EXCELLENT, USED_GOOD, etc.)
            category_id: ID categoria eBay
            images: Lista URL immagini
            item_specifics: Specifiche prodotto
        """
        
        data = {
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": quantity
                }
            },
            "condition": condition,
            "product": {
                "title": title,
                "description": description,
                "imageUrls": images or [],
            }
        }
        
        if item_specifics:
            data["product"]["aspects"] = {
                k: [v] for k, v in item_specifics.items()
            }
        
        return await self._request(
            "PUT",
            f"/sell/inventory/v1/inventory_item/{sku}",
            data=data
        )
    
    async def create_offer(
        self,
        sku: str,
        price: float,
        category_id: str,
        marketplace_id: str = "EBAY_IT",
        currency: str = "EUR",
        listing_duration: str = "GTC",
        shipping_cost: float = 0
    ) -> Dict[str, Any]:
        """
        Crea un'offerta per un inventory item
        
        Returns:
            Dict con offerId
        """
        
        data = {
            "sku": sku,
            "marketplaceId": marketplace_id,
            "format": "FIXED_PRICE",
            "listingDuration": listing_duration,
            "pricingSummary": {
                "price": {
                    "value": str(price),
                    "currency": currency
                }
            },
            "categoryId": category_id,
            "listingPolicies": {
                "fulfillmentPolicyId": "YOUR_FULFILLMENT_POLICY_ID",  # Da configurare
                "paymentPolicyId": "YOUR_PAYMENT_POLICY_ID",
                "returnPolicyId": "YOUR_RETURN_POLICY_ID"
            }
        }
        
        return await self._request(
            "POST",
            "/sell/inventory/v1/offer",
            data=data
        )
    
    async def publish_offer(self, offer_id: str) -> Dict[str, Any]:
        """
        Pubblica un'offerta (rende il listing attivo)
        
        Returns:
            Dict con listingId
        """
        return await self._request(
            "POST",
            f"/sell/inventory/v1/offer/{offer_id}/publish"
        )
    
    async def create_and_publish_listing(
        self,
        sku: str,
        title: str,
        description: str,
        price: float,
        category_id: str,
        images: List[str] = None,
        condition: str = "USED_EXCELLENT",
        item_specifics: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Crea e pubblica un listing in un'unica operazione
        
        Returns:
            Dict con listing_id e listing_url
        """
        
        # 1. Crea inventory item
        await self.create_inventory_item(
            sku=sku,
            title=title,
            description=description,
            price=price,
            condition=condition,
            category_id=category_id,
            images=images,
            item_specifics=item_specifics
        )
        
        logger.info(f"Created inventory item: {sku}")
        
        # 2. Crea offer
        offer_response = await self.create_offer(
            sku=sku,
            price=price,
            category_id=category_id
        )
        
        offer_id = offer_response.get("offerId")
        logger.info(f"Created offer: {offer_id}")
        
        # 3. Pubblica
        publish_response = await self.publish_offer(offer_id)
        
        listing_id = publish_response.get("listingId")
        logger.info(f"Published listing: {listing_id}")
        
        return {
            "sku": sku,
            "offer_id": offer_id,
            "listing_id": listing_id,
            "listing_url": f"https://www.ebay.it/itm/{listing_id}"
        }
    
    async def end_listing(self, listing_id: str, reason: str = "NOT_AVAILABLE") -> Dict[str, Any]:
        """Termina un listing attivo"""
        return await self._request(
            "POST",
            f"/sell/inventory/v1/offer/{listing_id}/withdraw"
        )
    
    async def get_orders(
        self,
        limit: int = 50,
        offset: int = 0,
        order_status: str = None
    ) -> Dict[str, Any]:
        """Ottieni ordini ricevuti"""
        
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if order_status:
            params["filter"] = f"orderfulfillmentstatus:{{{order_status}}}"
        
        return await self._request(
            "GET",
            "/sell/fulfillment/v1/order",
            params=params
        )
    
    async def get_category_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Ottieni suggerimenti categoria per un prodotto"""
        
        response = await self._request(
            "GET",
            "/commerce/taxonomy/v1/category_tree/101/get_category_suggestions",  # 101 = eBay IT
            params={"q": query}
        )
        
        suggestions = response.get("categorySuggestions", [])
        return [
            {
                "category_id": s["category"]["categoryId"],
                "category_name": s["category"]["categoryName"],
                "category_path": " > ".join(
                    [a["categoryName"] for a in s.get("categoryTreeNodeAncestors", [])]
                )
            }
            for s in suggestions
        ]
    
    async def close(self):
        await self.client.aclose()
