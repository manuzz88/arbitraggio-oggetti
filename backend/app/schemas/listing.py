from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.listing import ListingStatus, DestinationPlatform


class ListingBase(BaseModel):
    enhanced_title: str
    enhanced_description: str
    listing_price: float
    shipping_price: float = 0


class ListingCreate(ListingBase):
    item_id: UUID
    platform: DestinationPlatform
    enhanced_images: List[str] = []
    ebay_category_id: Optional[str] = None
    ebay_item_specifics: Optional[Dict[str, Any]] = None


class ListingUpdate(BaseModel):
    enhanced_title: Optional[str] = None
    enhanced_description: Optional[str] = None
    listing_price: Optional[float] = None
    shipping_price: Optional[float] = None
    status: Optional[ListingStatus] = None
    views: Optional[int] = None
    watchers: Optional[int] = None


class ListingResponse(ListingBase):
    id: UUID
    item_id: UUID
    platform: DestinationPlatform
    platform_listing_id: Optional[str] = None
    listing_url: Optional[str] = None
    enhanced_images: List[str] = []
    
    ebay_category_id: Optional[str] = None
    ebay_item_specifics: Optional[Dict[str, Any]] = None
    
    views: int
    watchers: int
    status: ListingStatus
    error_message: Optional[str] = None
    
    published_at: Optional[datetime] = None
    sold_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ListingListResponse(BaseModel):
    listings: List[ListingResponse]
    total: int
    page: int
    per_page: int
