import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class OrderStatus(str, enum.Enum):
    PENDING_PURCHASE = "pending_purchase"  # Venduto, devo comprare l'originale
    PURCHASED = "purchased"                 # Comprato l'originale
    SHIPPED_TO_ME = "shipped_to_me"        # In spedizione verso di me
    RECEIVED = "received"                   # Ricevuto
    SHIPPED_TO_BUYER = "shipped_to_buyer"  # Spedito al compratore
    DELIVERED = "delivered"                 # Consegnato
    COMPLETED = "completed"                 # Completato
    REFUNDED = "refunded"                   # Rimborsato
    CANCELLED = "cancelled"                 # Cancellato


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)
    
    # Platform order info
    platform_order_id = Column(String(255))
    
    # Dettagli vendita
    sale_price = Column(Numeric(10, 2), nullable=False)
    platform_fees = Column(Numeric(10, 2))
    shipping_cost_received = Column(Numeric(10, 2))
    
    # Costo acquisto originale
    purchase_price = Column(Numeric(10, 2))
    purchase_shipping = Column(Numeric(10, 2))
    purchase_date = Column(DateTime)
    purchase_url = Column(Text)
    
    # Spedizione al buyer
    shipping_cost_paid = Column(Numeric(10, 2))
    tracking_number = Column(String(100))
    
    # Profitto
    gross_profit = Column(Numeric(10, 2))
    net_profit = Column(Numeric(10, 2))
    
    # Status
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING_PURCHASE, index=True)
    notes = Column(Text)
    
    # Buyer info
    buyer_username = Column(String(255))
    buyer_info = Column(JSON)
    shipping_address = Column(JSON)
    
    # Timestamps
    sold_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    listing = relationship("Listing", back_populates="orders")

    def calculate_profit(self):
        """Calcola il profitto netto dell'ordine"""
        if not all([self.sale_price, self.purchase_price]):
            return None
        
        revenue = self.sale_price + (self.shipping_cost_received or 0)
        costs = (
            self.purchase_price +
            (self.purchase_shipping or 0) +
            (self.platform_fees or 0) +
            (self.shipping_cost_paid or 0)
        )
        
        self.gross_profit = self.sale_price - self.purchase_price
        self.net_profit = revenue - costs
        return self.net_profit

    def __repr__(self):
        return f"<Order {self.id} - {self.status.value}>"
