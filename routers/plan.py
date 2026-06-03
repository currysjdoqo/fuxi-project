from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from database import get_db
from auth import get_current_user
from models import PlanItem, User

router = APIRouter(prefix="/plan", tags=["plan"])


class PlanItemCreate(BaseModel):
    date: str
    content: str


class PlanItemUpdate(BaseModel):
    content: Optional[str] = None
    completed: Optional[int] = None


class PlanItemResponse(BaseModel):
    id: int
    user_id: int
    date: str
    content: str
    completed: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/items", response_model=PlanItemResponse)
def create_plan_item(
    item: PlanItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = item.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="计划内容不能为空")

    db_item = PlanItem(
        user_id=current_user.id,
        date=item.date,
        content=content,
        completed=0
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/items/{date}", response_model=List[PlanItemResponse])
def get_plan_items_by_date(
    date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(PlanItem).filter(
        PlanItem.user_id == current_user.id,
        PlanItem.date == date
    ).order_by(PlanItem.created_at).all()
    return items


@router.get("/items/range/{start_date}/{end_date}", response_model=List[PlanItemResponse])
def get_plan_items_by_range(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(PlanItem).filter(
        PlanItem.user_id == current_user.id,
        PlanItem.date >= start_date,
        PlanItem.date <= end_date
    ).order_by(PlanItem.date, PlanItem.created_at).all()
    return items


@router.put("/items/{item_id}", response_model=PlanItemResponse)
def update_plan_item(
    item_id: int,
    item_update: PlanItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_item = db.query(PlanItem).filter(
        PlanItem.id == item_id,
        PlanItem.user_id == current_user.id
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Plan item not found")
    
    if item_update.content is not None:
        content = item_update.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="计划内容不能为空")
        db_item.content = content
    if item_update.completed is not None:
        db_item.completed = item_update.completed
    
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/items/{item_id}")
def delete_plan_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_item = db.query(PlanItem).filter(
        PlanItem.id == item_id,
        PlanItem.user_id == current_user.id
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Plan item not found")
    
    db.delete(db_item)
    db.commit()
    return {"detail": "Plan item deleted successfully"}
