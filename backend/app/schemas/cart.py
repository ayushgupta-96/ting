from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CartItem(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., ge=0.0)
    base_price: Optional[float] = Field(None, ge=0.0)
    quantity: int = Field(1, ge=1, le=100)
    image_id: Optional[str] = None
    addons: Optional[List[Any]] = []
    variants: Optional[List[Any]] = []

class RestaurantBrief(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    parent_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    image: Optional[str] = None
    area: Optional[str] = None
    sla: Optional[str] = None

class SearchCartRequest(BaseModel):
    mobile: Optional[str] = Field(None, pattern=r"^[0-9]{10,15}$")
    restaurant: RestaurantBrief
    items: List[CartItem]
    address_id: Optional[str] = ""
    cart_id: Optional[str] = ""
    lat: float = Field(28.458901, ge=-90.0, le=90.0)
    lng: float = Field(77.497186, ge=-180.0, le=180.0)
    cooking: Optional[str] = Field("", max_length=500)
    incognito: bool = True

class SyncCartStateRequest(BaseModel):
    cart: Dict[str, Any]
    loc: Optional[Dict[str, Any]] = None
