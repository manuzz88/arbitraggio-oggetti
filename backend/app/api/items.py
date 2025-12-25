from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models.item import Item, ItemStatus, SourcePlatform
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse, ItemListResponse, ItemApprove
from app.services.international_prices import international_prices

router = APIRouter()


@router.get("/", response_model=ItemListResponse)
async def get_items(
    status: Optional[ItemStatus] = None,
    source: Optional[SourcePlatform] = None,
    min_score: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Lista items con filtri e paginazione"""
    query = select(Item)
    count_query = select(func.count(Item.id))
    
    if status:
        query = query.where(Item.status == status)
        count_query = count_query.where(Item.status == status)
    
    if source:
        query = query.where(Item.source_platform == source)
        count_query = count_query.where(Item.source_platform == source)
    
    if min_score:
        query = query.where(Item.ai_score >= min_score)
        count_query = count_query.where(Item.ai_score >= min_score)
    
    total = await db.scalar(count_query)
    
    query = query.order_by(Item.found_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return ItemListResponse(
        items=[ItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.get("/pending", response_model=ItemListResponse)
async def get_pending_items(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Lista items in attesa di approvazione, ordinati per score"""
    query = select(Item).where(Item.status == ItemStatus.PENDING)
    count_query = select(func.count(Item.id)).where(Item.status == ItemStatus.PENDING)
    
    total = await db.scalar(count_query)
    
    query = query.order_by(Item.ai_score.desc().nullslast(), Item.found_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return ItemListResponse(
        items=[ItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.get("/compare-international")
async def compare_international_prices(
    query: str = Query(..., description="Prodotto da cercare"),
    markets: str = Query("IT,US,UK,DE,JP", description="Mercati separati da virgola")
):
    """
    Confronta prezzi internazionali per arbitraggio import/export
    
    Mercati supportati: IT, US, UK, DE, JP
    """
    market_list = [m.strip().upper() for m in markets.split(",")]
    
    await international_prices.start()
    comparison = await international_prices.compare_prices(query, market_list)
    await international_prices.stop()
    
    result = {
        "query": query,
        "markets_checked": market_list,
        "prices": []
    }
    
    for p in comparison.prices:
        result["prices"].append({
            "country": p.country,
            "country_name": p.country_name,
            "price_local": p.price_local,
            "currency": p.currency,
            "price_eur": round(p.price_eur, 2),
            "shipping_to_italy": p.shipping_to_italy,
            "total_cost_italy": round(p.price_eur + (p.shipping_to_italy or 0), 2)
        })
    
    result["prices"].sort(key=lambda x: x["total_cost_italy"])
    
    if comparison.prices:
        cheapest = comparison.cheapest_market
        italy = comparison.italy_price
        
        if cheapest and italy and cheapest.country != "IT":
            savings = italy.price_eur - (cheapest.price_eur + (cheapest.shipping_to_italy or 0))
            if savings > 10:
                result["import_opportunity"] = {
                    "buy_from": cheapest.country_name,
                    "buy_price": round(cheapest.price_eur, 2),
                    "shipping": cheapest.shipping_to_italy,
                    "italy_price": round(italy.price_eur, 2),
                    "potential_savings": round(savings, 2),
                    "recommendation": "IMPORT" if savings > 30 else "WATCH"
                }
    
    return result


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: UUID, db: AsyncSession = Depends(get_db)):
    """Dettaglio singolo item"""
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return ItemResponse.model_validate(item)


@router.post("/", response_model=ItemResponse)
async def create_item(item_data: ItemCreate, db: AsyncSession = Depends(get_db)):
    """Crea nuovo item (usato dallo scraper)"""
    item = Item(**item_data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ItemResponse.model_validate(item)


@router.post("/bulk", response_model=List[ItemResponse])
async def create_items_bulk(items_data: List[ItemCreate], db: AsyncSession = Depends(get_db)):
    """Crea multipli items in batch"""
    items = [Item(**item_data.model_dump()) for item_data in items_data]
    db.add_all(items)
    await db.commit()
    
    for item in items:
        await db.refresh(item)
    
    return [ItemResponse.model_validate(item) for item in items]


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(item_id: UUID, item_data: ItemUpdate, db: AsyncSession = Depends(get_db)):
    """Aggiorna item"""
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    await db.commit()
    await db.refresh(item)
    return ItemResponse.model_validate(item)


@router.post("/{item_id}/approve", response_model=ItemResponse)
async def approve_item(item_id: UUID, approve_data: ItemApprove, db: AsyncSession = Depends(get_db)):
    """Approva item e crea listing automatico"""
    from app.models.listing import Listing, ListingStatus, DestinationPlatform
    
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.status != ItemStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Item is not pending, current status: {item.status}")
    
    item.status = ItemStatus.APPROVED
    item.approved_at = datetime.utcnow()
    
    # Calcola prezzo listing
    listing_price = approve_data.listing_price
    if not listing_price:
        if item.estimated_value_max:
            listing_price = float(item.estimated_value_max) * 0.9
        else:
            listing_price = float(item.original_price) * 1.4  # +40% markup
    
    # Crea listing automaticamente
    platform = DestinationPlatform.EBAY
    if approve_data.platform == "etsy":
        platform = DestinationPlatform.ETSY
    
    listing = Listing(
        item_id=item.id,
        platform=platform,
        enhanced_title=item.original_title,  # Per ora usa titolo originale
        enhanced_description=item.original_description or f"Vendo {item.original_title} in ottime condizioni.",
        enhanced_images=item.original_images or [],
        listing_price=listing_price,
        status=ListingStatus.DRAFT,
    )
    
    db.add(listing)
    item.status = ItemStatus.LISTED
    
    await db.commit()
    await db.refresh(item)
    
    return ItemResponse.model_validate(item)


@router.post("/{item_id}/reject", response_model=ItemResponse)
async def reject_item(item_id: UUID, reason: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Rifiuta item"""
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.status = ItemStatus.REJECTED
    item.rejection_reason = reason
    
    await db.commit()
    await db.refresh(item)
    return ItemResponse.model_validate(item)


@router.delete("/{item_id}")
async def delete_item(item_id: UUID, db: AsyncSession = Depends(get_db)):
    """Elimina item"""
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.delete(item)
    await db.commit()
    return {"message": "Item deleted"}


@router.post("/{item_id}/analyze")
async def analyze_item_ai(item_id: UUID, db: AsyncSession = Depends(get_db)):
    """Analizza un item con AI per valutare potenziale di arbitraggio"""
    from app.services.ai_analyzer import AIAnalyzer
    
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    analyzer = AIAnalyzer()
    analysis = await analyzer.analyze_item(
        title=item.original_title,
        description=item.original_description or "",
        price=float(item.original_price),
        images=item.original_images or [],
        location=item.original_location or "",
        condition=item.seller_info.get("condition", "") if item.seller_info else ""
    )
    
    # Salva risultati nel database
    item.ai_score = analysis.get("score")
    item.ai_category = analysis.get("category")
    item.ai_brand = analysis.get("brand")
    item.ai_model = analysis.get("model")
    item.estimated_value_min = analysis.get("estimated_value_min")
    item.estimated_value_max = analysis.get("estimated_value_max")
    item.potential_margin = analysis.get("margin_percentage")
    item.ai_validation = analysis
    item.analyzed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(item)
    
    return {
        "item": ItemResponse.model_validate(item),
        "analysis": analysis
    }


@router.post("/analyze-pending")
async def analyze_pending_items(
    limit: int = Query(10, ge=1, le=50),
    min_price: float = Query(10, ge=0),
    max_price: float = Query(500, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Analizza tutti gli items pending con AI e restituisce le migliori opportunità"""
    from app.services.ai_analyzer import AIAnalyzer
    
    # Prendi items pending non ancora analizzati
    query = select(Item).where(
        Item.status == ItemStatus.PENDING,
        Item.ai_score.is_(None),
        Item.original_price >= min_price,
        Item.original_price <= max_price
    ).order_by(Item.found_at.desc()).limit(limit)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    if not items:
        return {"message": "Nessun item da analizzare", "opportunities": []}
    
    analyzer = AIAnalyzer()
    opportunities = []
    
    for item in items:
        analysis = await analyzer.analyze_item(
            title=item.original_title,
            description=item.original_description or "",
            price=float(item.original_price),
            images=item.original_images or [],
            location=item.original_location or "",
            condition=item.seller_info.get("condition", "") if item.seller_info else ""
        )
        
        # Salva risultati
        item.ai_score = analysis.get("score")
        item.ai_category = analysis.get("category")
        item.ai_brand = analysis.get("brand")
        item.ai_model = analysis.get("model")
        item.estimated_value_min = analysis.get("estimated_value_min")
        item.estimated_value_max = analysis.get("estimated_value_max")
        item.potential_margin = analysis.get("margin_percentage")
        item.ai_validation = analysis
        item.analyzed_at = datetime.utcnow()
        
        # Aggiungi alle opportunità se score >= 60
        if analysis.get("score", 0) >= 60:
            opportunities.append({
                "item": ItemResponse.model_validate(item),
                "analysis": analysis
            })
    
    await db.commit()
    
    # Ordina per score
    opportunities.sort(key=lambda x: x["analysis"]["score"], reverse=True)
    
    return {
        "analyzed": len(items),
        "opportunities_found": len(opportunities),
        "opportunities": opportunities
    }
