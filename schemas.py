from pydantic import BaseModel, EmailStr
from typing import List, Optional, Literal
from datetime import datetime


class ItemIn(BaseModel):
    name: str
    qty: int
    unit: str = "Tablets"
    category: str = "Other"


class RequestCreate(BaseModel):
    hospital: str
    contact: str
    email: EmailStr
    phone: Optional[str] = ""
    priority: Literal["normal", "urgent"] = "normal"
    notes: Optional[str] = ""
    items: List[ItemIn]


class ItemOut(BaseModel):
    name: str
    qty: int
    unit: str
    category: str

    class Config:
        from_attributes = True


class RequestOut(BaseModel):
    id: str
    hospital: str
    contact: str
    email: str
    phone: str
    priority: str
    notes: str
    status: str
    admin_note: str
    date_submitted: datetime
    date_actioned: Optional[datetime]
    items: List[ItemOut]

    class Config:
        from_attributes = True


class ActionRequest(BaseModel):
    status: Literal["pending", "processing", "fulfilled", "cancelled"]
    admin_note: Optional[str] = ""


class MessageResponse(BaseModel):
    message: str
    request_id: Optional[str] = None
