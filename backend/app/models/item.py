import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ItemStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    LISTED = "listed"
    SOLD = "sold"
    UNAVAILABLE = "unavailable"


class SourcePlatform(str, enum.Enum):
    FACEBOOK = "facebook"
    SUBITO = "subito"
    WALLAPOP = "wallapop"
    VINTED = "vinted"
    OTHER = "other"


class Item(Base):
    __tablename__ = "items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_platform = Column(SQLEnum(SourcePlatform), nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    source_id = Column(String(255), nullable=False)
    
    # Dati originali
    original_title = Column(Text, nullable=False)
    original_description = Column(Text)
    original_price = Column(Numeric(10, 2), nullable=False)
    original_currency = Column(String(3), default="EUR")
    original_images = Column(JSON, default=list)
    original_location = Column(String(255))
    seller_info = Column(JSON, default=dict)
    
    # AI Analysis
    ai_validation = Column(JSON)
    ai_score = Column(Integer)
    ai_category = Column(String(100))
    ai_brand = Column(String(100))
    ai_model = Column(String(100))
    ai_condition = Column(String(50))
    estimated_value_min = Column(Numeric(10, 2))
    estimated_value_max = Column(Numeric(10, 2))
    potential_margin = Column(Numeric(10, 2))
    
    # Status
    status = Column(SQLEnum(ItemStatus), default=ItemStatus.PENDING, index=True)
    rejection_reason = Column(Text)
    
    # Timestamps
    found_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime)
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    listings = relationship("Listing", back_populates="item", cascade="all, delete-orphan")
    availability_checks = relationship("AvailabilityCheck", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item {self.id} - {self.original_title[:30]}>"
