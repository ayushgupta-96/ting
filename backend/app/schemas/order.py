from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
import re

class CouponRequest(BaseModel):
    mobile: Optional[str] = Field(None, pattern=r"^[0-9]{10,15}$")
    cart_id: str = Field(..., min_length=1, max_length=100)
    address_id: str = Field(..., min_length=1, max_length=100)
    restaurant_id: str = Field(..., min_length=1, max_length=100)
    cart_value: float = Field(..., gt=0.0)
    lat: float = Field(28.458901, ge=-90.0, le=90.0)
    lng: float = Field(77.497186, ge=-180.0, le=180.0)
    code: Optional[str] = Field(None, max_length=50)

class PaymentOptionsRequest(BaseModel):
    mobile: Optional[str] = Field(None, pattern=r"^[0-9]{10,15}$")
    cart_id: str = Field(..., min_length=1, max_length=100)
    address_id: str = Field(..., min_length=1, max_length=100)
    restaurant_id: str = Field(..., min_length=1, max_length=100)
    cart_value: float = Field(..., gt=0.0)
    lat: float = Field(28.458901, ge=-90.0, le=90.0)
    lng: float = Field(77.497186, ge=-180.0, le=180.0)

class PlaceOrderRequest(BaseModel):
    mobile: Optional[str] = Field(None, pattern=r"^[0-9]{10,15}$")
    cart_id: str = Field(..., min_length=1, max_length=100)
    address_id: str = Field(..., min_length=1, max_length=100)
    lat: float = Field(28.458901, ge=-90.0, le=90.0)
    lng: float = Field(77.497186, ge=-180.0, le=180.0)
    amount: float = Field(..., gt=0.0)
    method: Literal["cod", "upi"] = "cod"
    snap: Optional[Dict[str, Any]] = None
