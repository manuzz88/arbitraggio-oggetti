import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, Numeric, DateTime, ForeignKey
# SQLite compatible - use String instead of UUID
from sqlalchemy.orm import relationship
from app.database import Base


class AvailabilityCheck(Base):
    __tablename__ = "availability_checks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = Column(String(36), ForeignKey("items.id"), nullable=False)
    
    checked_at = Column(DateTime, default=datetime.utcnow)
    is_available = Column(Boolean, nullable=False)
    current_price = Column(Numeric(10, 2))
    price_changed = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Relationships
    item = relationship("Item", back_populates="availability_checks")

    def __repr__(self):
        return f"<AvailabilityCheck {self.item_id} - {'Available' if self.is_available else 'Unavailable'}>"
