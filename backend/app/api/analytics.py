from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.models.item import Item, ItemStatus
from app.models.listing import Listing, ListingStatus
from app.models.order import Order, OrderStatus

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Statistiche principali per dashboard"""
    
    # Items stats
    items_pending = await db.scalar(
        select(func.count(Item.id)).where(Item.status == ItemStatus.PENDING)
    )
    items_approved = await db.scalar(
        select(func.count(Item.id)).where(Item.status == ItemStatus.APPROVED)
    )
    items_listed = await db.scalar(
        select(func.count(Item.id)).where(Item.status == ItemStatus.LISTED)
    )
    
    # Listings stats
    listings_active = await db.scalar(
        select(func.count(Listing.id)).where(Listing.status == ListingStatus.ACTIVE)
    )
    
    # Orders stats
    orders_pending = await db.scalar(
        select(func.count(Order.id)).where(
            Order.status.in_([OrderStatus.PENDING_PURCHASE, OrderStatus.PURCHASED, OrderStatus.RECEIVED])
        )
    )
    orders_completed = await db.scalar(
        select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED)
    )
    
    # Profitti totali
    total_profit = await db.scalar(
        select(func.sum(Order.net_profit)).where(Order.status == OrderStatus.COMPLETED)
    ) or 0
    
    # Profitti ultimo mese
    month_ago = datetime.utcnow() - timedelta(days=30)
    monthly_profit = await db.scalar(
        select(func.sum(Order.net_profit)).where(
            and_(
                Order.status == OrderStatus.COMPLETED,
                Order.completed_at >= month_ago
            )
        )
    ) or 0
    
    return {
        "items": {
            "pending": items_pending,
            "approved": items_approved,
            "listed": items_listed
        },
        "listings": {
            "active": listings_active
        },
        "orders": {
            "pending_action": orders_pending,
            "completed": orders_completed
        },
        "profit": {
            "total": float(total_profit),
            "monthly": float(monthly_profit)
        }
    }


@router.get("/profit/daily")
async def get_daily_profit(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Profitto giornaliero per grafico"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(
            func.date(Order.completed_at).label("date"),
            func.sum(Order.net_profit).label("profit"),
            func.count(Order.id).label("orders")
        )
        .where(
            and_(
                Order.status == OrderStatus.COMPLETED,
                Order.completed_at >= start_date
            )
        )
        .group_by(func.date(Order.completed_at))
        .order_by(func.date(Order.completed_at))
    )
    
    data = result.all()
    
    return {
        "data": [
            {
                "date": str(row.date),
                "profit": float(row.profit) if row.profit else 0,
                "orders": row.orders
            }
            for row in data
        ]
    }


@router.get("/sources")
async def get_source_stats(db: AsyncSession = Depends(get_db)):
    """Statistiche per piattaforma source"""
    result = await db.execute(
        select(
            Item.source_platform,
            func.count(Item.id).label("total"),
            func.count(Item.id).filter(Item.status == ItemStatus.APPROVED).label("approved"),
            func.count(Item.id).filter(Item.status == ItemStatus.SOLD).label("sold"),
            func.avg(Item.ai_score).label("avg_score")
        )
        .group_by(Item.source_platform)
    )
    
    data = result.all()
    
    return {
        "sources": [
            {
                "platform": row.source_platform.value if row.source_platform else "unknown",
                "total": row.total,
                "approved": row.approved,
                "sold": row.sold,
                "avg_score": round(float(row.avg_score), 1) if row.avg_score else 0
            }
            for row in data
        ]
    }


@router.get("/categories")
async def get_category_stats(db: AsyncSession = Depends(get_db)):
    """Statistiche per categoria (rilevata da AI)"""
    result = await db.execute(
        select(
            Item.ai_category,
            func.count(Item.id).label("total"),
            func.avg(Item.potential_margin).label("avg_margin")
        )
        .where(Item.ai_category.isnot(None))
        .group_by(Item.ai_category)
        .order_by(func.count(Item.id).desc())
        .limit(10)
    )
    
    data = result.all()
    
    return {
        "categories": [
            {
                "category": row.ai_category,
                "total": row.total,
                "avg_margin": round(float(row.avg_margin), 2) if row.avg_margin else 0
            }
            for row in data
        ]
    }
