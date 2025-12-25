from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.item import ItemStatus, SourcePlatform


class AIValidation(BaseModel):
    categoria: Optional[str] = None
    brand: Optional[str] = None
    modello: Optional[str] = None
    stato: Optional[str] = None
    stato_score: Optional[int] = None
    difetti_visibili: List[str] = []
    corrispondenza_descrizione: Optional[str] = None
    note_corrispondenza: Optional[str] = None
    score_affidabilita: Optional[int] = None
    prezzo_stimato: Optional[Dict[str, Any]] = None
    raccomandazione: Optional[str] = None
    margine_potenziale: Optional[float] = None


class ItemBase(BaseModel):
    original_title: str
    original_description: Optional[str] = None
    original_price: float
    original_currency: str = "EUR"
    original_images: List[str] = []
    original_location: Optional[str] = None


class ItemCreate(ItemBase):
    source_platform: SourcePlatform
    source_url: str
    source_id: str
    seller_info: Optional[Dict[str, Any]] = None


class ItemUpdate(BaseModel):
    status: Optional[ItemStatus] = None
    rejection_reason: Optional[str] = None
    ai_validation: Optional[Dict[str, Any]] = None
    ai_score: Optional[int] = None
    estimated_value_min: Optional[float] = None
    estimated_value_max: Optional[float] = None


class ItemApprove(BaseModel):
    listing_price: Optional[float] = None
    platform: str = "ebay"


class ItemResponse(ItemBase):
    id: UUID
    source_platform: SourcePlatform
    source_url: str
    source_id: str
    seller_info: Optional[Dict[str, Any]] = None
    
    ai_validation: Optional[Dict[str, Any]] = None
    ai_score: Optional[int] = None
    ai_category: Optional[str] = None
    ai_brand: Optional[str] = None
    ai_model: Optional[str] = None
    ai_condition: Optional[str] = None
    estimated_value_min: Optional[float] = None
    estimated_value_max: Optional[float] = None
    potential_margin: Optional[float] = None
    
    status: ItemStatus
    rejection_reason: Optional[str] = None
    
    found_at: datetime
    analyzed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    items: List[ItemResponse]
    total: int
    page: int
    per_page: int
    pages: int
