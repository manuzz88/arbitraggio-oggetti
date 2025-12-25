"""
Mock Scraper per testing del sistema.
Genera dati fittizi realistici per testare il flusso completo.
"""
import random
import uuid
from typing import List, Dict, Any
from loguru import logger


# Dati mock realistici
MOCK_PRODUCTS = [
    {
        "category": "console",
        "items": [
            {"title": "Nintendo Switch OLED Bianco", "price_range": (200, 280), "brand": "Nintendo"},
            {"title": "PlayStation 5 Digital Edition", "price_range": (350, 420), "brand": "Sony"},
            {"title": "Xbox Series S 512GB", "price_range": (180, 250), "brand": "Microsoft"},
            {"title": "Nintendo Switch Lite Turchese", "price_range": (120, 160), "brand": "Nintendo"},
            {"title": "PS4 Pro 1TB con 2 controller", "price_range": (180, 240), "brand": "Sony"},
        ]
    },
    {
        "category": "smartphone",
        "items": [
            {"title": "iPhone 13 128GB Blu", "price_range": (450, 550), "brand": "Apple"},
            {"title": "iPhone 12 64GB Nero", "price_range": (320, 400), "brand": "Apple"},
            {"title": "Samsung Galaxy S23 256GB", "price_range": (500, 600), "brand": "Samsung"},
            {"title": "iPhone 14 Pro 256GB Viola", "price_range": (700, 850), "brand": "Apple"},
            {"title": "Google Pixel 7 128GB", "price_range": (350, 420), "brand": "Google"},
        ]
    },
    {
        "category": "computer",
        "items": [
            {"title": "MacBook Air M1 256GB Grigio", "price_range": (650, 800), "brand": "Apple"},
            {"title": "MacBook Pro 14 M2 Pro", "price_range": (1400, 1700), "brand": "Apple"},
            {"title": "Dell XPS 13 i7 16GB RAM", "price_range": (600, 750), "brand": "Dell"},
            {"title": "iPad Pro 11 M2 128GB WiFi", "price_range": (550, 680), "brand": "Apple"},
            {"title": "Surface Pro 9 i5 256GB", "price_range": (700, 850), "brand": "Microsoft"},
        ]
    },
    {
        "category": "audio",
        "items": [
            {"title": "AirPods Pro 2 con custodia MagSafe", "price_range": (150, 200), "brand": "Apple"},
            {"title": "Sony WH-1000XM5 Nero", "price_range": (220, 280), "brand": "Sony"},
            {"title": "Bose QuietComfort 45", "price_range": (180, 240), "brand": "Bose"},
            {"title": "AirPods Max Grigio Siderale", "price_range": (350, 450), "brand": "Apple"},
            {"title": "Samsung Galaxy Buds2 Pro", "price_range": (100, 140), "brand": "Samsung"},
        ]
    },
]

LOCATIONS = ["Milano", "Roma", "Napoli", "Torino", "Bologna", "Firenze", "Palermo", "Genova", "Bari", "Verona"]
CONDITIONS = ["Come nuovo", "Ottime condizioni", "Buone condizioni", "Usato", "Qualche segno d'uso"]

SAMPLE_IMAGES = [
    "https://picsum.photos/seed/{}/800/600",
]


class MockScraper:
    """Scraper mock per testing"""
    
    def __init__(self):
        self.platform = "mock"
        logger.info("MockScraper initialized")
    
    async def start(self):
        logger.info("MockScraper started")
    
    async def stop(self):
        logger.info("MockScraper stopped")
    
    async def search(self, query: str, max_pages: int = 1) -> List[Dict[str, Any]]:
        """
        Genera risultati mock basati sulla query
        """
        logger.info(f"MockScraper searching for: {query}")
        
        items = []
        query_lower = query.lower()
        
        # Trova prodotti che matchano la query
        for category in MOCK_PRODUCTS:
            for product in category["items"]:
                title_lower = product["title"].lower()
                # Match se la query è contenuta nel titolo o viceversa
                if any(word in title_lower for word in query_lower.split()) or \
                   any(word in query_lower for word in title_lower.split()):
                    # Genera varianti
                    for _ in range(random.randint(2, 5)):
                        item = self._generate_item(product, category["category"])
                        items.append(item)
        
        # Se non trova nulla, genera comunque qualche risultato generico
        if not items:
            for _ in range(random.randint(3, 8)):
                category = random.choice(MOCK_PRODUCTS)
                product = random.choice(category["items"])
                item = self._generate_item(product, category["category"])
                items.append(item)
        
        random.shuffle(items)
        logger.info(f"MockScraper found {len(items)} items")
        return items[:20]  # Max 20 items
    
    def _generate_item(self, product: Dict, category: str) -> Dict[str, Any]:
        """Genera un item mock realistico"""
        item_id = str(uuid.uuid4())[:8]
        price_min, price_max = product["price_range"]
        
        # Prezzo con variazione
        base_price = random.uniform(price_min, price_max)
        # Alcuni prezzi sono "affari" (sotto mercato)
        if random.random() < 0.3:
            base_price *= random.uniform(0.7, 0.85)
        
        price = round(base_price, 0)
        
        # Stima valore di mercato (per calcolo margine)
        market_value = round(random.uniform(price_min, price_max) * 1.1, 0)
        
        condition = random.choice(CONDITIONS)
        location = random.choice(LOCATIONS)
        
        # Genera descrizione
        descriptions = [
            f"Vendo {product['title']} in {condition.lower()}. Funziona perfettamente.",
            f"{product['title']} usato pochissimo. {condition}. Vendo per inutilizzo.",
            f"Cedo {product['title']}. Condizioni: {condition.lower()}. Prezzo trattabile.",
            f"{product['title']} - {condition}. Completo di tutto. Spedizione possibile.",
        ]
        
        # Genera immagini fake (usando picsum per placeholder)
        num_images = random.randint(1, 4)
        images = [f"https://picsum.photos/seed/{item_id}_{i}/800/600" for i in range(num_images)]
        
        return {
            "source_id": f"mock_{item_id}",
            "source_url": f"https://example.com/annuncio/{item_id}",
            "original_title": product["title"],
            "original_description": random.choice(descriptions),
            "original_price": price,
            "original_currency": "EUR",
            "original_images": images,
            "original_location": location,
            "seller_info": {
                "id": f"seller_{random.randint(1000, 9999)}",
                "name": f"Utente{random.randint(100, 999)}",
                "rating": round(random.uniform(4.0, 5.0), 1),
            },
            # Dati extra per AI mock
            "_mock_data": {
                "brand": product["brand"],
                "category": category,
                "condition": condition,
                "market_value": market_value,
                "margin_potential": round((market_value - price) / price * 100, 1) if price > 0 else 0,
            }
        }
    
    async def get_item_details(self, url: str) -> Dict[str, Any]:
        """Ritorna dettagli mock di un item"""
        category = random.choice(MOCK_PRODUCTS)
        product = random.choice(category["items"])
        return self._generate_item(product, category["category"])
    
    async def check_availability(self, url: str) -> bool:
        """Simula check disponibilità (90% disponibile)"""
        return random.random() < 0.9
