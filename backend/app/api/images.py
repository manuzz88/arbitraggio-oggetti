"""
Image Proxy - Proxy per caricare immagini da Subito.it evitando hotlink protection
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import httpx
import base64
from urllib.parse import unquote

router = APIRouter()


@router.get("/proxy")
async def proxy_image(url: str):
    """
    Proxy per caricare immagini esterne.
    Utile per bypassare hotlink protection di Subito.it
    """
    decoded_url = unquote(url)
    
    # Verifica che sia un URL di immagine valido
    allowed_domains = [
        "images.sbito.it",
        "img.subito.it", 
        "picsum.photos",
    ]
    
    if not any(domain in decoded_url for domain in allowed_domains):
        raise HTTPException(status_code=400, detail="Domain not allowed")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                decoded_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.subito.it/",
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                },
                follow_redirects=True,
                timeout=15.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Image not found")
            
            # Determina content type
            content_type = response.headers.get("content-type", "image/jpeg")
            
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache 24h
                }
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image fetch timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
