import base64
import httpx
from typing import List, Dict, Any, Optional
from loguru import logger
import json

from app.config import settings


class VisionAnalyzer:
    """Analizza immagini prodotti con GPT-4 Vision"""
    
    ANALYSIS_PROMPT = """Analizza questa immagine di un prodotto in vendita su un marketplace second-hand.

Descrizione originale del venditore: "{description}"
Prezzo richiesto: {price}€

Fornisci un'analisi dettagliata in formato JSON con i seguenti campi:

{{
    "categoria": "categoria principale del prodotto (es: Elettronica, Abbigliamento, Videogiochi, etc.)",
    "brand": "marca/brand se riconoscibile, altrimenti null",
    "modello": "modello specifico se riconoscibile, altrimenti null",
    "stato": "Nuovo/Come Nuovo/Buono/Accettabile/Danneggiato",
    "stato_score": "da 1 a 10, dove 10 è perfetto",
    "difetti_visibili": ["lista di difetti visibili nelle foto"],
    "corrispondenza_descrizione": "Sì/No/Parziale - la descrizione corrisponde a ciò che vedi?",
    "note_corrispondenza": "spiegazione se ci sono discrepanze",
    "autenticita": "Autentico/Sospetto/Non verificabile",
    "note_autenticita": "eventuali segnali di contraffazione",
    "score_affidabilita": "da 1 a 10, quanto è affidabile questo annuncio",
    "prezzo_stimato": {{
        "min": prezzo_minimo_mercato,
        "max": prezzo_massimo_mercato,
        "currency": "EUR"
    }},
    "margine_potenziale": "percentuale di margine stimato rispetto al prezzo richiesto",
    "raccomandazione": "APPROVA/RIFIUTA/VERIFICA",
    "motivo_raccomandazione": "spiegazione della raccomandazione",
    "keywords_seo": ["lista di keyword per ottimizzare il listing"],
    "target_audience": "descrizione del target di acquirenti ideale"
}}

Rispondi SOLO con il JSON, senza altro testo."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def analyze_images(
        self,
        image_urls: List[str],
        description: str,
        price: float
    ) -> Dict[str, Any]:
        """Analizza le immagini di un prodotto con GPT-4 Vision"""
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured, returning mock analysis")
            return self._mock_analysis()
        
        try:
            # Prepara le immagini per l'API
            content = [
                {
                    "type": "text",
                    "text": self.ANALYSIS_PROMPT.format(
                        description=description,
                        price=price
                    )
                }
            ]
            
            # Aggiungi le immagini (max 4 per non superare limiti)
            for url in image_urls[:4]:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": url, "detail": "high"}
                })
            
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    "max_tokens": 1500
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Estrai il JSON dalla risposta
            text = result["choices"][0]["message"]["content"]
            
            # Pulisci il testo se contiene markdown
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            analysis = json.loads(text.strip())
            logger.info(f"Image analysis completed: score={analysis.get('score_affidabilita')}")
            
            return analysis
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during image analysis: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during image analysis: {e}")
            raise
    
    async def analyze_from_bytes(
        self,
        images: List[bytes],
        description: str,
        price: float
    ) -> Dict[str, Any]:
        """Analizza immagini da bytes (base64)"""
        
        if not self.api_key:
            return self._mock_analysis()
        
        content = [
            {
                "type": "text",
                "text": self.ANALYSIS_PROMPT.format(
                    description=description,
                    price=price
                )
            }
        ]
        
        for img_bytes in images[:4]:
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}",
                    "detail": "high"
                }
            })
        
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": 1500
                }
            )
            
            response.raise_for_status()
            result = response.json()
            text = result["choices"][0]["message"]["content"]
            
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
            
        except Exception as e:
            logger.error(f"Error analyzing images from bytes: {e}")
            raise
    
    def _mock_analysis(self) -> Dict[str, Any]:
        """Ritorna analisi mock per testing"""
        return {
            "categoria": "Test Category",
            "brand": None,
            "modello": None,
            "stato": "Buono",
            "stato_score": 7,
            "difetti_visibili": [],
            "corrispondenza_descrizione": "Non verificabile",
            "note_corrispondenza": "API key non configurata",
            "autenticita": "Non verificabile",
            "note_autenticita": None,
            "score_affidabilita": 5,
            "prezzo_stimato": {"min": 0, "max": 0, "currency": "EUR"},
            "margine_potenziale": 0,
            "raccomandazione": "VERIFICA",
            "motivo_raccomandazione": "Analisi mock - configurare OpenAI API key",
            "keywords_seo": [],
            "target_audience": "N/A"
        }
    
    async def close(self):
        await self.client.aclose()
