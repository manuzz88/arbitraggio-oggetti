import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ListingStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHING = "publishing"
    ACTIVE = "active"
    PAUSED = "paused"
    SOLD = "sold"
    ENDED = "ended"
    ERROR = "error"


class DestinationPlatform(str, enum.Enum):
    EBAY = "ebay"
    ETSY = "etsy"
    BACKMARKET = "backmarket"


class Listing(Base):
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    
    # Piattaforma destinazione
    platform = Column(SQLEnum(DestinationPlatform), nullable=False, index=True)
    platform_listing_id = Column(String(255))
    listing_url = Column(Text)
    
    # Dati migliorati
    enhanced_title = Column(Text, nullable=False)
    enhanced_description = Column(Text, nullable=False)
    enhanced_images = Column(JSON, default=list)  # Paths locali delle immagini migliorate
    
    # Pricing
    listing_price = Column(Numeric(10, 2), nullable=False)
    shipping_price = Column(Numeric(10, 2), default=0)
    
    # eBay specific
    ebay_category_id = Column(String(50))
    ebay_item_specifics = Column(JSON)
    
    # Performance
    views = Column(Integer, default=0)
    watchers = Column(Integer, default=0)
    
    # Status
    status = Column(SQLEnum(ListingStatus), default=ListingStatus.DRAFT, index=True)
    error_message = Column(Text)
    
    # Timestamps
    published_at = Column(DateTime)
    sold_at = Column(DateTime)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    item = relationship("Item", back_populates="listings")
    orders = relationship("Order", back_populates="listing", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Listing {self.id} - {self.platform.value}>"
