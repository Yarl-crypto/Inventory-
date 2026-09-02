import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"  # regular user - can propose changes, cannot apply directly


class ChangeAction(str, enum.Enum):
    create = "create"
    update = "update"
    delete = "delete"


class ChangeStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.staff)
    created_at = Column(DateTime, default=datetime.utcnow)

    proposed_changes = relationship("PendingChange", back_populates="submitted_by_user",
                                     foreign_keys="PendingChange.submitted_by")


class Item(Base):
    __tablename__ = "items"

    item_no = Column(String(30), primary_key=True)
    category = Column(String(80), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, default="")
    images = Column(JSON, default=list)       # list of image URLs
    keywords = Column(JSON, default=list)      # list of search keywords
    date_added = Column(DateTime, default=datetime.utcnow)
    date_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PendingChange(Base):
    __tablename__ = "pending_changes"

    id = Column(Integer, primary_key=True, index=True)
    item_no = Column(String(30), nullable=True)  # null when action == create (no item_no assigned yet)
    action = Column(Enum(ChangeAction), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)  # proposed field values
    status = Column(Enum(ChangeStatus), nullable=False, default=ChangeStatus.pending)

    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    admin_note = Column(String(300), nullable=True)

    submitted_by_user = relationship("User", back_populates="proposed_changes",
                                      foreign_keys=[submitted_by])
