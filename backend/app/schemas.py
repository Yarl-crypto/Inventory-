from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models import UserRole, ChangeAction, ChangeStatus


# ---------- Auth ----------
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------- Items ----------
class ItemBase(BaseModel):
    category: str
    name: str
    price: Decimal
    description: Optional[str] = ""
    images: Optional[list[str]] = []
    keywords: Optional[list[str]] = []

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v < 0:
            raise ValueError("price cannot be negative")
        return v


class ItemCreate(ItemBase):
    item_no: str  # e.g. "BK-0001" - assigned by whoever proposes/creates


class ItemUpdate(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    price: Optional[Decimal] = None
    description: Optional[str] = None
    images: Optional[list[str]] = None
    keywords: Optional[list[str]] = None


class ItemOut(ItemBase):
    item_no: str
    date_added: datetime
    date_updated: datetime

    class Config:
        from_attributes = True


# ---------- Pending changes ----------
class PendingChangeOut(BaseModel):
    id: int
    item_no: Optional[str]
    action: ChangeAction
    payload: dict
    status: ChangeStatus
    submitted_by: int
    submitted_at: datetime
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    admin_note: Optional[str]

    class Config:
        from_attributes = True


class ReviewDecision(BaseModel):
    approve: bool
    admin_note: Optional[str] = None
