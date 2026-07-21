from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User
from utils.billing import exchange_balance_for_credits, get_public_account_state
from utils.payments import (
    PAYMENT_PROVIDER_ALIPAY,
    PAYMENT_PROVIDER_WECHAT,
    PRODUCT_TYPE_BALANCE_TOPUP,
    PRODUCT_TYPE_MEMBERSHIP,
    alipay_is_configured,
    create_payment_order,
    find_user_order,
    get_frontend_base_url,
    mark_paid_from_alipay,
    mark_paid_from_wechat_callback,
    serialize_order,
    wechat_is_configured,
)

router = APIRouter(prefix="/billing", tags=["billing"])


class ExchangeCreditsRequest(BaseModel):
    amount_cents: int


class CreatePaymentRequest(BaseModel):
    provider: str = PAYMENT_PROVIDER_ALIPAY
    product_type: str
    plan: str | None = None
    amount_cents: int | None = None


@router.get("/status")
def billing_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {
        **get_public_account_state(db, current_user),
        "providers": {
            PAYMENT_PROVIDER_ALIPAY: {
                "configured": alipay_is_configured(),
            },
            PAYMENT_PROVIDER_WECHAT: {
                "configured": wechat_is_configured(),
            },
        },
    }


@router.post("/payments/create")
def create_order(
    request: CreatePaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = create_payment_order(
        db=db,
        user=current_user,
        provider=request.provider,
        product_type=request.product_type,
        plan=request.plan,
        amount_cents=request.amount_cents,
    )
    return serialize_order(order)


@router.get("/payments/{order_no}")
def get_order(
    order_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = find_user_order(db, current_user.id, order_no)
    return serialize_order(order)


@router.post("/credits/exchange")
def exchange_credits(
    request: ExchangeCreditsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return exchange_balance_for_credits(db, current_user, request.amount_cents)


@router.get("/payments/alipay/return")
def alipay_return(order_no: str | None = None):
    base = get_frontend_base_url().rstrip("/")
    target = f"{base}/settings?payment_return=1"
    if order_no:
        target += f"&order_no={order_no}"
    return RedirectResponse(target)


@router.post("/payments/alipay/notify")
async def alipay_notify(request: Request):
    form = await request.form()
    payload = {key: str(value) for key, value in form.items()}
    from database import SessionLocal

    db = SessionLocal()
    try:
        mark_paid_from_alipay(db, payload)
    finally:
        db.close()
    return PlainTextResponse("success")


@router.get("/payments/alipay/notify")
def alipay_notify_get():
    return HTMLResponse("ok")


@router.post("/payments/wechat/notify")
async def wechat_notify(request: Request):
    payload = await request.json()
    from database import SessionLocal

    db = SessionLocal()
    try:
        mark_paid_from_wechat_callback(db, payload)
    finally:
        db.close()
    return JSONResponse({"code": "SUCCESS", "message": "成功"})
