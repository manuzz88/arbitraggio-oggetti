from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from app.models.order import OrderStatus


class OrderBase(BaseModel):
    sale_price: float
    platform_fees: Optional[float] = None
    shipping_cost_received: Optional[float] = None


class OrderCreate(OrderBase):
    listing_id: UUID
    platform_order_id: Optional[str] = None
    buyer_username: Optional[str] = None
    buyer_info: Optional[Dict[str, Any]] = None
    shipping_address: Optional[Dict[str, Any]] = None


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    purchase_price: Optional[float] = None
    purchase_shipping: Optional[float] = None
    purchase_date: Optional[datetime] = None
    purchase_url: Optional[str] = None
    shipping_cost_paid: Optional[float] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


class OrderResponse(OrderBase):
    id: UUID
    listing_id: UUID
    platform_order_id: Optional[str] = None
    
    purchase_price: Optional[float] = None
    purchase_shipping: Optional[float] = None
    purchase_date: Optional[datetime] = None
    purchase_url: Optional[str] = None
    
    shipping_cost_paid: Optional[float] = None
    tracking_number: Optional[str] = None
    
    gross_profit: Optional[float] = None
    net_profit: Optional[float] = None
    
    status: OrderStatus
    notes: Optional[str] = None
    
    buyer_username: Optional[str] = None
    buyer_info: Optional[Dict[str, Any]] = None
    shipping_address: Optional[Dict[str, Any]] = None
    
    sold_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    per_page: int
