"""
AI Analyzer Service - Valuta opportunità di arbitraggio usando GPT-4
Con ricerca prezzi reali da eBay, Amazon, Google Shopping
"""
import json
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from loguru import logger

from app.config import settings
from app.services.price_researcher import price_researcher, MarketResearch


class AIAnalyzer:
    """Analizza prodotti per identificare opportunità di arbitraggio ad alto margine"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Più economico, ottimo per analisi
        self.use_price_research = True  # Abilita ricerca prezzi reali
    
    async def analyze_item(
        self,
        title: str,
        description: str,
        price: float,
        images: List[str],
        location: str = "",
        condition: str = "",
        skip_price_research: bool = False
    ) -> Dict[str, Any]:
        """
        Analizza un item e restituisce:
        - score: 1-100 (potenziale di profitto)
        - category: categoria prodotto
        - brand: marca identificata
        - model: modello identificato
        - estimated_value_min: valore minimo stimato
        - estimated_value_max: valore massimo stimato
        - margin_percentage: margine potenziale %
        - recommendation: buy/skip/watch
        - reasoning: spiegazione
        """
        
        try:
            # Ricerca prezzi di mercato reali (se abilitata)
            market_data: Optional[MarketResearch] = None
            market_context = ""
            
            if self.use_price_research and not skip_price_research:
                try:
                    await price_researcher.start()
                    market_data = await price_researcher.research(title)
                    market_context = market_data.to_prompt_context()
                    await price_researcher.stop()
                    logger.info(f"Market research completed: eBay sold={len(market_data.ebay_sold_prices)}, Amazon={len(market_data.amazon_prices)}")
                except Exception as e:
                    logger.warning(f"Price research failed, continuing without: {e}")
            
            # Prepara il prompt con dati di mercato
            prompt = self._build_analysis_prompt(
                title, description, price, location, condition, market_context
            )
            
            # Usa sempre analisi testuale (le immagini di Subito.it sono protette)
            result = await self._analyze_text_only(prompt)
            
            # Aggiungi dati di mercato al risultato
            if market_data:
                result["market_data"] = {
                    "ebay_sold_avg": market_data.avg_ebay_sold,
                    "ebay_sold_min": market_data.min_ebay_sold,
                    "ebay_sold_max": market_data.max_ebay_sold,
                    "amazon_avg": market_data.avg_amazon,
                    "sources_checked": ["ebay_sold", "ebay_active", "amazon", "google_shopping"]
                }
            
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._default_response(str(e))
    
    def _build_analysis_prompt(
        self,
        title: str,
        description: str,
        price: float,
        location: str,
        condition: str,
        market_context: str = ""
    ) -> str:
        market_section = f"\n{market_context}\n" if market_context else "\n⚠️ Nessun dato di mercato disponibile - usa la tua conoscenza dei prezzi.\n"
        
        return f"""Sei un esperto di arbitraggio online. Analizza questo annuncio da Subito.it e valuta se è un'opportunità di profitto per rivenderlo su eBay/Vinted.

ANNUNCIO:
- Titolo: {title}
- Descrizione: {description or 'Non disponibile'}
- Prezzo richiesto: €{price}
- Località: {location or 'Non specificata'}
- Condizione: {condition or 'Non specificata'}
{market_section}
ANALIZZA E RISPONDI IN JSON:
{{
    "score": <1-100, dove 100 = opportunità eccezionale>,
    "category": "<categoria merceologica>",
    "brand": "<marca se identificabile, altrimenti null>",
    "model": "<modello se identificabile, altrimenti null>",
    "estimated_value_min": <prezzo minimo di rivendita stimato in EUR>,
    "estimated_value_max": <prezzo massimo di rivendita stimato in EUR>,
    "margin_percentage": <margine % potenziale>,
    "recommendation": "<BUY|SKIP|WATCH>",
    "reasoning": "<spiegazione breve in italiano>",
    "red_flags": ["<eventuali segnali di allarme>"],
    "selling_tips": "<consigli per la rivendita>"
}}

CRITERI DI VALUTAZIONE:
- Score 80-100: Margine >40%, prodotto richiesto, facile da vendere
- Score 60-79: Margine 25-40%, buona opportunità
- Score 40-59: Margine 15-25%, rischio medio
- Score <40: Margine basso o rischio alto, SKIP

Considera:
1. Prezzo di mercato su eBay per prodotti simili VENDUTI (non in vendita)
2. Domanda del prodotto
3. Facilità di spedizione
4. Rischio di contraffazione
5. Stagionalità

Rispondi SOLO con il JSON, nessun altro testo."""

    async def _analyze_with_vision(self, prompt: str, images: List[str]) -> Dict[str, Any]:
        """Analisi con GPT-4 Vision per vedere le immagini"""
        
        # Costruisci i messaggi con immagini
        content = [{"type": "text", "text": prompt}]
        
        for img_url in images[:3]:  # Max 3 immagini
            content.append({
                "type": "image_url",
                "image_url": {"url": img_url, "detail": "low"}
            })
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Sei un esperto di e-commerce e arbitraggio. Analizza prodotti e stima il loro valore di mercato."
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        return self._parse_response(response.choices[0].message.content)
    
    async def _analyze_text_only(self, prompt: str) -> Dict[str, Any]:
        """Analisi solo testo (senza immagini)"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Sei un esperto di e-commerce e arbitraggio. Analizza prodotti e stima il loro valore di mercato."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        return self._parse_response(response.choices[0].message.content)
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parsa la risposta JSON da GPT"""
        try:
            # Rimuovi eventuale markdown
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            data = json.loads(content)
            
            # Valida e normalizza
            return {
                "score": min(100, max(1, int(data.get("score", 50)))),
                "category": data.get("category", "Altro"),
                "brand": data.get("brand"),
                "model": data.get("model"),
                "estimated_value_min": float(data.get("estimated_value_min", 0)),
                "estimated_value_max": float(data.get("estimated_value_max", 0)),
                "margin_percentage": float(data.get("margin_percentage", 0)),
                "recommendation": data.get("recommendation", "SKIP").upper(),
                "reasoning": data.get("reasoning", ""),
                "red_flags": data.get("red_flags", []),
                "selling_tips": data.get("selling_tips", ""),
                "analyzed": True
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return self._default_response(f"Parse error: {e}")
    
    def _default_response(self, error: str = "") -> Dict[str, Any]:
        """Risposta di default in caso di errore"""
        return {
            "score": 0,
            "category": "Sconosciuto",
            "brand": None,
            "model": None,
            "estimated_value_min": 0,
            "estimated_value_max": 0,
            "margin_percentage": 0,
            "recommendation": "SKIP",
            "reasoning": f"Analisi non disponibile: {error}" if error else "Analisi non disponibile",
            "red_flags": [],
            "selling_tips": "",
            "analyzed": False
        }
    
    async def batch_analyze(
        self,
        items: List[Dict[str, Any]],
        min_price: float = 10,
        max_price: float = 500
    ) -> List[Dict[str, Any]]:
        """
        Analizza un batch di items, filtrando prima per prezzo.
        Restituisce solo quelli con score >= 60.
        """
        results = []
        
        for item in items:
            price = item.get("original_price", 0)
            
            # Filtro prezzo base
            if price < min_price or price > max_price:
                continue
            
            analysis = await self.analyze_item(
                title=item.get("original_title", ""),
                description=item.get("original_description", ""),
                price=price,
                images=item.get("original_images", []),
                location=item.get("original_location", ""),
                condition=item.get("seller_info", {}).get("condition", "")
            )
            
            # Aggiungi solo se score >= 60
            if analysis.get("score", 0) >= 60:
                results.append({
                    "item": item,
                    "analysis": analysis
                })
        
        # Ordina per score decrescente
        results.sort(key=lambda x: x["analysis"]["score"], reverse=True)
        
        return results
