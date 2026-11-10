from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    
    # Toing session mapping
    access_key = Column(String(100), nullable=True, index=True)  # x-user-key returned by validate_webapp
    active_mobile = Column(String(20), nullable=True, index=True)
    
    # Location & Address Cache
    default_address_id = Column(String(100), nullable=True)
    lat = Column(Float, nullable=True, default=28.458901)
    lng = Column(Float, nullable=True, default=77.497186)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AccountSession(Base):
    __tablename__ = "account_sessions"
    __table_args__ = (
        UniqueConstraint("telegram_id", "mobile", name="uq_telegram_account_mobile"),
    )

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, index=True, nullable=False)
    mobile = Column(String(20), index=True, nullable=False)
    name = Column(String(100), nullable=True)
    token = Column(Text, nullable=False)
    tid = Column(Text, nullable=False)
    sid = Column(String(100), nullable=True)
    device_id = Column(String(100), nullable=True)
    customer_id = Column(String(100), nullable=True)
    status = Column(String(20), default="fresh")  # 'fresh' | 'used'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SavedAddressLink(Base):
    __tablename__ = "saved_address_links"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, index=True, nullable=True)
    mobile = Column(String(20), index=True, nullable=False)
    link = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OrderRecord(Base):
    __tablename__ = "order_records"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(100), unique=True, index=True, nullable=False)
    telegram_id = Column(BigInteger, index=True, nullable=False)
    mobile = Column(String(20), nullable=False)
    restaurant_name = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="upi")  # cod or upi
    status = Column(String(50), default="PLACED")
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
