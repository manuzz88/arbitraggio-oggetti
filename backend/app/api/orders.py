from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderListResponse

router = APIRouter()


@router.get("/", response_model=OrderListResponse)
async def get_orders(
    status: Optional[OrderStatus] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Lista ordini con filtri"""
    query = select(Order)
    count_query = select(func.count(Order.id))
    
    if status:
        query = query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)
    
    total = await db.scalar(count_query)
    
    query = query.order_by(Order.sold_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/pending", response_model=OrderListResponse)
async def get_pending_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Ordini che richiedono azione (da acquistare/spedire)"""
    pending_statuses = [
        OrderStatus.PENDING_PURCHASE,
        OrderStatus.PURCHASED,
        OrderStatus.RECEIVED
    ]
    
    query = select(Order).where(Order.status.in_(pending_statuses))
    count_query = select(func.count(Order.id)).where(Order.status.in_(pending_statuses))
    
    total = await db.scalar(count_query)
    
    query = query.order_by(Order.sold_at.asc())  # Più vecchi prima
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    """Dettaglio ordine"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse.model_validate(order)


@router.post("/", response_model=OrderResponse)
async def create_order(order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    """Crea nuovo ordine (quando viene venduto un listing)"""
    order = Order(**order_data.model_dump())
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return OrderResponse.model_validate(order)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(order_id: UUID, order_data: OrderUpdate, db: AsyncSession = Depends(get_db)):
    """Aggiorna ordine"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    update_data = order_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    # Ricalcola profitto se abbiamo i dati necessari
    if order.sale_price and order.purchase_price:
        order.calculate_profit()
    
    await db.commit()
    await db.refresh(order)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/mark-purchased", response_model=OrderResponse)
async def mark_purchased(
    order_id: UUID,
    purchase_price: float,
    purchase_shipping: float = 0,
    purchase_url: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Segna ordine come acquistato dal source"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = OrderStatus.PURCHASED
    order.purchase_price = purchase_price
    order.purchase_shipping = purchase_shipping
    order.purchase_url = purchase_url
    order.purchase_date = datetime.utcnow()
    order.calculate_profit()
    
    await db.commit()
    await db.refresh(order)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/mark-shipped", response_model=OrderResponse)
async def mark_shipped(
    order_id: UUID,
    tracking_number: str,
    shipping_cost: float = 0,
    db: AsyncSession = Depends(get_db)
):
    """Segna ordine come spedito al buyer"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = OrderStatus.SHIPPED_TO_BUYER
    order.tracking_number = tracking_number
    order.shipping_cost_paid = shipping_cost
    order.calculate_profit()
    
    await db.commit()
    await db.refresh(order)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/complete", response_model=OrderResponse)
async def complete_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    """Completa ordine"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = OrderStatus.COMPLETED
    order.completed_at = datetime.utcnow()
    order.calculate_profit()
    
    await db.commit()
    await db.refresh(order)
    return OrderResponse.model_validate(order)
