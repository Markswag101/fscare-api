from pydantic import BaseModel, EmailStr
from typing import List, Optional, Literal
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────
class HospitalRegister(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = ""
    address: Optional[str] = ""
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    approved: Optional[bool] = None


# ── Requests ──────────────────────────────────────────────────────────────────
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


# ── Hospital ──────────────────────────────────────────────────────────────────
class HospitalOut(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    address: str
    approved: bool
    date_registered: datetime
    class Config:
        from_attributes = True
