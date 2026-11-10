from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SearchRestaurantsParams(BaseModel):
    q: str = Field(..., min_length=1, max_length=100)
    lat: float = Field(28.458901, ge=-90.0, le=90.0)
    lng: float = Field(77.497186, ge=-180.0, le=180.0)
    mobile: Optional[str] = Field(None, pattern=r"^[0-9]{10,15}$")

class OutletRequest(BaseModel):
    restaurant_id: str = Field(..., min_length=1, max_length=100)
    lat: float = Field(28.458901, ge=-90.0, le=90.0)
    lng: float = Field(77.497186, ge=-180.0, le=180.0)
    mobile: Optional[str] = Field(None, pattern=r"^[0-9]{10,15}$")

class MenuRequest(BaseModel):
    restaurant_id: str = Field(..., min_length=1, max_length=100)
    query: Optional[str] = Field("", max_length=200)
    metadata: Optional[str] = Field("", max_length=500)
    lat: float = Field(28.458901, ge=-90.0, le=90.0)
    lng: float = Field(77.497186, ge=-180.0, le=180.0)
    mobile: Optional[str] = Field(None, pattern=r"^[0-9]{10,15}$")

class MenuSearchRequest(BaseModel):
    restaurant_id: str = Field(..., min_length=1, max_length=100)
    query: str = Field(..., min_length=1, max_length=200)
    veg: bool = False
    lat: float = Field(28.458901, ge=-90.0, le=90.0)
    lng: float = Field(77.497186, ge=-180.0, le=180.0)
    mobile: Optional[str] = Field(None, pattern=r"^[0-9]{10,15}$")
