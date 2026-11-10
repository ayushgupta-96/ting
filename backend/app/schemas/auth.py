from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ValidateWebappRequest(BaseModel):
    init_data: str = Field(..., min_length=10, max_length=5000)

class ValidateWebappResponse(BaseModel):
    valid: bool
    user_id: int
    access_key: str
    accounts_count: Optional[int] = 0

class LoginJsonRequest(BaseModel):
    json_data: str = Field(..., min_length=1, max_length=5000)

class JsonLoginPayload(BaseModel):
    token: str = Field(..., min_length=1)
    tid: str = Field(..., min_length=1)
    sid: str = Field(..., min_length=1)
    deviceId: Optional[str] = "dev_default"
    customerId: Optional[str] = "cust_default"
    mobile: str = Field(..., min_length=10)
    name: Optional[str] = None

    class Config:
        extra = "allow"

class ToggleStatusRequest(BaseModel):
    id: Optional[str] = None
    mobile: Optional[str] = None

class SwitchSessionRequest(BaseModel):
    mobile: str = Field(..., pattern=r"^[0-9]{10,15}$")

class AddressItem(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    receiver_name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    lng: Optional[float] = Field(None, ge=-180.0, le=180.0)
    tag: Optional[str] = None
