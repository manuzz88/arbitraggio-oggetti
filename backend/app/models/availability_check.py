import uuid
from datetime import datetime
from sqlalchemy import Column, Boolean, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class AvailabilityCheck(Base):
    __tablename__ = "availability_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    
    checked_at = Column(DateTime, default=datetime.utcnow)
    is_available = Column(Boolean, nullable=False)
    current_price = Column(Numeric(10, 2))
    price_changed = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Relationships
    item = relationship("Item", back_populates="availability_checks")

    def __repr__(self):
        return f"<AvailabilityCheck {self.item_id} - {'Available' if self.is_available else 'Unavailable'}>"
