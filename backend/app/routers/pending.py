from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import PendingChange, Item, ChangeAction, ChangeStatus, User
from app.schemas import PendingChangeOut, ReviewDecision

router = APIRouter(prefix="/pending", tags=["pending changes"])


@router.get("", response_model=list[PendingChangeOut])
def list_pending(
    status_filter: ChangeStatus = ChangeStatus.pending,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return (
        db.query(PendingChange)
        .filter(PendingChange.status == status_filter)
        .order_by(PendingChange.submitted_at)
        .all()
    )


@router.post("/{change_id}/review", response_model=PendingChangeOut)
def review_change(
    change_id: int,
    decision: ReviewDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    change = db.query(PendingChange).filter(PendingChange.id == change_id).first()
    if not change:
        raise HTTPException(status_code=404, detail="Pending change not found")
    if change.status != ChangeStatus.pending:
        raise HTTPException(status_code=400, detail="This change was already reviewed")

    if decision.approve:
        _apply_change(db, change)
        change.status = ChangeStatus.approved
    else:
        change.status = ChangeStatus.rejected

    change.reviewed_by = admin.id
    change.reviewed_at = datetime.utcnow()
    change.admin_note = decision.admin_note
    db.commit()
    db.refresh(change)
    return change


def _apply_change(db: Session, change: PendingChange):
    if change.action == ChangeAction.create:
        if db.query(Item).filter(Item.item_no == change.item_no).first():
            raise HTTPException(status_code=400, detail="item_no already exists; cannot approve")
        db.add(Item(**change.payload))

    elif change.action == ChangeAction.update:
        item = db.query(Item).filter(Item.item_no == change.item_no).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item no longer exists; cannot approve")
        for k, v in change.payload.items():
            setattr(item, k, v)
        item.date_updated = datetime.utcnow()

    elif change.action == ChangeAction.delete:
        item = db.query(Item).filter(Item.item_no == change.item_no).first()
        if item:
            db.delete(item)
