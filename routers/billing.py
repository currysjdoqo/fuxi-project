from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User
from utils.billing import exchange_balance_for_credits, get_public_account_state, purchase_membership

router = APIRouter(prefix="/billing", tags=["billing"])


class PurchaseMembershipRequest(BaseModel):
    plan: str


class ExchangeCreditsRequest(BaseModel):
    amount_cents: int


@router.get("/status")
def billing_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_public_account_state(db, current_user)


@router.post("/membership/purchase")
def buy_membership(
    request: PurchaseMembershipRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return purchase_membership(db, current_user, request.plan, payer_user_id=current_user.id)


@router.post("/credits/exchange")
def exchange_credits(
    request: ExchangeCreditsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return exchange_balance_for_credits(db, current_user, request.amount_cents)
