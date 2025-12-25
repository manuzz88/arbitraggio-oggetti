from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from uuid import UUID

from app.database import get_db
from app.models.listing import Listing, ListingStatus, DestinationPlatform
from app.schemas.listing import ListingCreate, ListingUpdate, ListingResponse, ListingListResponse

router = APIRouter()


@router.get("/", response_model=ListingListResponse)
async def get_listings(
    status: Optional[ListingStatus] = None,
    platform: Optional[DestinationPlatform] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Lista listings con filtri"""
    query = select(Listing)
    count_query = select(func.count(Listing.id))
    
    if status:
        query = query.where(Listing.status == status)
        count_query = count_query.where(Listing.status == status)
    
    if platform:
        query = query.where(Listing.platform == platform)
        count_query = count_query.where(Listing.platform == platform)
    
    total = await db.scalar(count_query)
    
    query = query.order_by(Listing.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    listings = result.scalars().all()
    
    return ListingListResponse(
        listings=[ListingResponse.model_validate(l) for l in listings],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/active", response_model=ListingListResponse)
async def get_active_listings(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Lista listings attivi"""
    query = select(Listing).where(Listing.status == ListingStatus.ACTIVE)
    count_query = select(func.count(Listing.id)).where(Listing.status == ListingStatus.ACTIVE)
    
    total = await db.scalar(count_query)
    
    query = query.order_by(Listing.published_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    listings = result.scalars().all()
    
    return ListingListResponse(
        listings=[ListingResponse.model_validate(l) for l in listings],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: UUID, db: AsyncSession = Depends(get_db)):
    """Dettaglio listing"""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    return ListingResponse.model_validate(listing)


@router.post("/", response_model=ListingResponse)
async def create_listing(listing_data: ListingCreate, db: AsyncSession = Depends(get_db)):
    """Crea nuovo listing"""
    listing = Listing(**listing_data.model_dump())
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return ListingResponse.model_validate(listing)


@router.patch("/{listing_id}", response_model=ListingResponse)
async def update_listing(listing_id: UUID, listing_data: ListingUpdate, db: AsyncSession = Depends(get_db)):
    """Aggiorna listing"""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    update_data = listing_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(listing, field, value)
    
    await db.commit()
    await db.refresh(listing)
    return ListingResponse.model_validate(listing)


@router.post("/{listing_id}/publish")
async def publish_listing(listing_id: UUID, db: AsyncSession = Depends(get_db)):
    """Pubblica listing su piattaforma destinazione"""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing.status not in [ListingStatus.DRAFT, ListingStatus.PAUSED]:
        raise HTTPException(status_code=400, detail=f"Cannot publish listing with status: {listing.status}")
    
    # TODO: Trigger pubblicazione su eBay/Etsy
    # from app.services.platforms.ebay import publish_to_ebay
    # result = await publish_to_ebay(listing)
    
    listing.status = ListingStatus.PUBLISHING
    await db.commit()
    
    return {"message": "Publishing started", "listing_id": str(listing_id)}


@router.post("/{listing_id}/end")
async def end_listing(listing_id: UUID, db: AsyncSession = Depends(get_db)):
    """Termina listing"""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # TODO: Rimuovi da eBay/Etsy
    
    listing.status = ListingStatus.ENDED
    await db.commit()
    
    return {"message": "Listing ended"}


@router.delete("/{listing_id}")
async def delete_listing(listing_id: UUID, db: AsyncSession = Depends(get_db)):
    """Elimina listing"""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    await db.delete(listing)
    await db.commit()
    return {"message": "Listing deleted"}
