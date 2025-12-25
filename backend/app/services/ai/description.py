import httpx
from typing import Dict, Any, Optional
from loguru import logger

from app.config import settings


class DescriptionGenerator:
    """Genera titoli e descrizioni ottimizzate per i listing"""
    
    TITLE_PROMPT = """Genera un titolo ottimizzato per eBay per questo prodotto.

Informazioni prodotto:
- Categoria: {category}
- Brand: {brand}
- Modello: {model}
- Condizioni: {condition}
- Keywords SEO suggerite: {keywords}

Descrizione originale: "{original_description}"

Regole per il titolo:
1. Massimo 80 caratteri
2. Includi brand e modello se disponibili
3. Includi condizioni (es: "Ottime condizioni", "Come nuovo")
4. Usa keywords rilevanti per la ricerca
5. NO simboli speciali inutili, NO tutto maiuscolo
6. Deve essere professionale e attraente

Rispondi SOLO con il titolo, nient'altro."""

    DESCRIPTION_PROMPT = """Genera una descrizione professionale per eBay per questo prodotto.

Informazioni prodotto:
- Categoria: {category}
- Brand: {brand}
- Modello: {model}
- Condizioni: {condition}
- Difetti noti: {defects}
- Prezzo: {price}€
- Keywords SEO: {keywords}
- Target audience: {target}

Descrizione originale del venditore: "{original_description}"

Genera una descrizione che:
1. Sia professionale e dettagliata
2. Elenchi le specifiche tecniche (se note)
3. Descriva onestamente le condizioni
4. Menzioni eventuali difetti in modo trasparente
5. Includa keywords per SEO
6. Abbia una struttura chiara con sezioni
7. Sia in italiano
8. Lunghezza: 150-300 parole

Usa questo formato:
📦 DESCRIZIONE
[descrizione generale]

✨ CONDIZIONI
[stato del prodotto]

📋 SPECIFICHE
[lista specifiche se disponibili]

🚚 SPEDIZIONE
Spedizione rapida e tracciata in tutta Italia.

Rispondi SOLO con la descrizione formattata."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def generate_title(
        self,
        ai_analysis: Dict[str, Any],
        original_description: str
    ) -> str:
        """Genera titolo ottimizzato"""
        
        if not self.api_key:
            return self._mock_title(ai_analysis, original_description)
        
        prompt = self.TITLE_PROMPT.format(
            category=ai_analysis.get("categoria", "N/A"),
            brand=ai_analysis.get("brand") or "N/A",
            model=ai_analysis.get("modello") or "N/A",
            condition=ai_analysis.get("stato", "Usato"),
            keywords=", ".join(ai_analysis.get("keywords_seo", [])),
            original_description=original_description[:500]
        )
        
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.7
                }
            )
            
            response.raise_for_status()
            result = response.json()
            title = result["choices"][0]["message"]["content"].strip()
            
            # Assicurati che non superi 80 caratteri
            if len(title) > 80:
                title = title[:77] + "..."
            
            return title
            
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return self._mock_title(ai_analysis, original_description)
    
    async def generate_description(
        self,
        ai_analysis: Dict[str, Any],
        original_description: str,
        price: float
    ) -> str:
        """Genera descrizione ottimizzata"""
        
        if not self.api_key:
            return self._mock_description(ai_analysis, original_description)
        
        defects = ai_analysis.get("difetti_visibili", [])
        defects_str = ", ".join(defects) if defects else "Nessun difetto visibile"
        
        prompt = self.DESCRIPTION_PROMPT.format(
            category=ai_analysis.get("categoria", "N/A"),
            brand=ai_analysis.get("brand") or "N/A",
            model=ai_analysis.get("modello") or "N/A",
            condition=ai_analysis.get("stato", "Usato"),
            defects=defects_str,
            price=price,
            keywords=", ".join(ai_analysis.get("keywords_seo", [])),
            target=ai_analysis.get("target_audience", "N/A"),
            original_description=original_description[:1000]
        )
        
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800,
                    "temperature": 0.7
                }
            )
            
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating description: {e}")
            return self._mock_description(ai_analysis, original_description)
    
    async def generate_listing_content(
        self,
        ai_analysis: Dict[str, Any],
        original_description: str,
        price: float
    ) -> Dict[str, str]:
        """Genera titolo e descrizione insieme"""
        
        title = await self.generate_title(ai_analysis, original_description)
        description = await self.generate_description(ai_analysis, original_description, price)
        
        return {
            "title": title,
            "description": description
        }
    
    def _mock_title(self, ai_analysis: Dict[str, Any], original: str) -> str:
        """Titolo mock per testing"""
        brand = ai_analysis.get("brand", "")
        model = ai_analysis.get("modello", "")
        condition = ai_analysis.get("stato", "Usato")
        
        parts = [p for p in [brand, model] if p]
        if parts:
            return f"{' '.join(parts)} - {condition}"
        return original[:77] + "..." if len(original) > 80 else original
    
    def _mock_description(self, ai_analysis: Dict[str, Any], original: str) -> str:
        """Descrizione mock per testing"""
        return f"""📦 DESCRIZIONE
{original}

✨ CONDIZIONI
{ai_analysis.get('stato', 'Usato')}

🚚 SPEDIZIONE
Spedizione rapida e tracciata in tutta Italia."""
    
    async def close(self):
        await self.client.aclose()
