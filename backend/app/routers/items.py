from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Item, User, PendingChange, ChangeAction, ChangeStatus
from app.schemas import ItemOut, ItemCreate, ItemUpdate, PendingChangeOut
from app.storage import upload_image

router = APIRouter(prefix="/items", tags=["items"])


# ---------- Read: open to any logged-in user ----------
@router.get("", response_model=list[ItemOut])
def list_items(
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Item)
    if category:
        q = q.filter(Item.category == category)
    return q.order_by(Item.name).offset(offset).limit(limit).all()


@router.get("/search", response_model=list[ItemOut])
def search_items(
    q: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    like = f"%{q}%"
    results = (
        db.query(Item)
        .filter(
            or_(
                Item.name.ilike(like),
                Item.category.ilike(like),
                Item.description.ilike(like),
                Item.item_no.ilike(like),
            )
        )
        .limit(50)
        .all()
    )
    # also match keywords (JSON array) in Python since JSON ILIKE isn't portable
    if not results:
        all_items = db.query(Item).all()
        results = [
            it for it in all_items
            if any(q.lower() in kw.lower() for kw in (it.keywords or []))
        ]
    return results


@router.get("/{item_no}", response_model=ItemOut)
def get_item(item_no: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.query(Item).filter(Item.item_no == item_no).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


# ---------- Image upload: any logged-in user (goes to storage, not yet attached to an item) ----------
@router.post("/upload-image")
async def upload_item_image(file: UploadFile = File(...), _: User = Depends(get_current_user)):
    content = await file.read()
    url = upload_image(content, file.filename, file.content_type)
    return {"url": url}


# ---------- Write: admin = immediate, staff = pending approval ----------
@router.post("", status_code=201)
def create_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(Item).filter(Item.item_no == payload.item_no).first():
        raise HTTPException(status_code=400, detail="item_no already exists")

    if current_user.role.value == "admin":
        item = Item(**payload.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"status": "created", "item": ItemOut.model_validate(item)}

    change = PendingChange(
        item_no=payload.item_no,
        action=ChangeAction.create,
        payload=payload.model_dump(mode="json"),
        submitted_by=current_user.id,
    )
    db.add(change)
    db.commit()
    db.refresh(change)
    return {"status": "pending_approval", "change": PendingChangeOut.model_validate(change)}


@router.put("/{item_no}")
def update_item(
    item_no: str,
    payload: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(Item).filter(Item.item_no == item_no).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    if current_user.role.value == "admin":
        for k, v in updates.items():
            setattr(item, k, v)
        item.date_updated = datetime.utcnow()
        db.commit()
        db.refresh(item)
        return {"status": "updated", "item": ItemOut.model_validate(item)}

    change = PendingChange(
        item_no=item_no,
        action=ChangeAction.update,
        payload={k: (str(v) if hasattr(v, "__float__") else v) for k, v in updates.items()},
        submitted_by=current_user.id,
    )
    db.add(change)
    db.commit()
    db.refresh(change)
    return {"status": "pending_approval", "change": PendingChangeOut.model_validate(change)}


@router.delete("/{item_no}")
def delete_item(
    item_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(Item).filter(Item.item_no == item_no).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if current_user.role.value == "admin":
        db.delete(item)
        db.commit()
        return {"status": "deleted"}

    change = PendingChange(
        item_no=item_no,
        action=ChangeAction.delete,
        payload={},
        submitted_by=current_user.id,
    )
    db.add(change)
    db.commit()
    db.refresh(change)
    return {"status": "pending_approval", "change": PendingChangeOut.model_validate(change)}
