from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import KeepSeekUsage, User, WalletTransaction

FREE_DAILY_LIMIT = 5
MEMBER_MONTHLY_CALLS = 80
REFERRAL_COMMISSION_RATE = 0.12
CALL_CREDITS_PER_YUAN = 5

PLAN_CONFIG = {
    "month": {"label": "月卡", "days": 30, "price_cents": 1200, "calls": 80},
    "quarter": {"label": "季卡", "days": 90, "price_cents": 3000, "calls": 240},
    "year": {"label": "年卡", "days": 365, "price_cents": 10000, "calls": 960},
}


def _today_key() -> str:
    return datetime.utcnow().date().isoformat()


def generate_invite_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        exists = db.query(User).filter(User.invite_code == code).first()
        if not exists:
            return code


def ensure_user_invite_code(db: Session, user: User) -> str:
    if user.invite_code:
        return user.invite_code
    user.invite_code = generate_invite_code(db)
    db.commit()
    db.refresh(user)
    return user.invite_code


def get_public_account_state(db: Session, user: User) -> dict:
    if user.free_calls_date != _today_key():
        user.free_calls_date = _today_key()
        user.free_calls_used = 0
        db.commit()
        db.refresh(user)

    member_active = bool(user.member_expires_at and user.member_expires_at > datetime.utcnow())
    free_remaining = max(FREE_DAILY_LIMIT - (user.free_calls_used or 0), 0)

    return {
        "invite_code": ensure_user_invite_code(db, user),
        "invited_by_id": user.invited_by_id,
        "balance_cents": user.balance_cents or 0,
        "call_credits": user.call_credits or 0,
        "member_expires_at": user.member_expires_at.isoformat() if user.member_expires_at else None,
        "member_calls_remaining": user.member_calls_remaining or 0,
        "member_active": member_active,
        "free_daily_limit": FREE_DAILY_LIMIT,
        "free_calls_used_today": user.free_calls_used or 0,
        "free_calls_remaining_today": free_remaining,
    }


def _log_wallet_tx(
    db: Session,
    user_id: int,
    amount_cents: int,
    tx_type: str,
    source_user_id: int | None = None,
    note: str | None = None,
) -> None:
    db.add(
        WalletTransaction(
            user_id=user_id,
            source_user_id=source_user_id,
            amount_cents=amount_cents,
            tx_type=tx_type,
            note=note,
        )
    )


def apply_referral_commission(db: Session, receiver: User, payer_user_id: int, amount_cents: int) -> int:
    if not receiver.invited_by_id or amount_cents <= 0:
        return 0
    commission_cents = int(amount_cents * REFERRAL_COMMISSION_RATE)
    if commission_cents <= 0:
        return 0

    inviter = db.query(User).filter(User.id == receiver.invited_by_id).first()
    if not inviter:
        return 0

    inviter.balance_cents = (inviter.balance_cents or 0) + commission_cents
    _log_wallet_tx(
        db,
        user_id=inviter.id,
        source_user_id=payer_user_id,
        amount_cents=commission_cents,
        tx_type="commission",
        note="referral commission",
    )
    return commission_cents


def purchase_membership(db: Session, user: User, plan: str, payer_user_id: int | None = None) -> dict:
    config = PLAN_CONFIG.get(plan)
    if not config:
        raise HTTPException(status_code=400, detail="无效的会员套餐")

    now = datetime.utcnow()
    base_expiry = user.member_expires_at if user.member_expires_at and user.member_expires_at > now else now
    user.member_expires_at = base_expiry + timedelta(days=config["days"])
    user.member_calls_remaining = (user.member_calls_remaining or 0) + config["calls"]

    if payer_user_id is None:
        payer_user_id = user.id

    _log_wallet_tx(
        db,
        user_id=user.id,
        source_user_id=payer_user_id,
        amount_cents=-config["price_cents"],
        tx_type="membership_purchase",
        note=plan,
    )

    if user.invited_by_id:
        apply_referral_commission(db, user, payer_user_id, config["price_cents"])

    db.commit()
    db.refresh(user)
    return {
        "plan": plan,
        "price_cents": config["price_cents"],
        "member_expires_at": user.member_expires_at.isoformat() if user.member_expires_at else None,
        "member_calls_remaining": user.member_calls_remaining,
    }


def exchange_balance_for_credits(db: Session, user: User, amount_cents: int) -> dict:
    if amount_cents <= 0 or amount_cents % 100 != 0:
        raise HTTPException(status_code=400, detail="兑换金额必须按元递增")
    if (user.balance_cents or 0) < amount_cents:
        raise HTTPException(status_code=400, detail="余额不足")

    yuan = amount_cents // 100
    credits = yuan * CALL_CREDITS_PER_YUAN
    user.balance_cents = (user.balance_cents or 0) - amount_cents
    user.call_credits = (user.call_credits or 0) + credits
    _log_wallet_tx(db, user.id, -amount_cents, "balance_exchange", note=f"{credits} credits")
    db.commit()
    db.refresh(user)
    return {
        "balance_cents": user.balance_cents,
        "call_credits": user.call_credits,
        "added_credits": credits,
    }


def consume_keepseek_use(
    db: Session,
    user: User,
    source: str,
    allow_credits: bool = False,
) -> dict:
    now = datetime.utcnow()
    today = now.date().isoformat()

    if user.free_calls_date != today:
        user.free_calls_date = today
        user.free_calls_used = 0

    member_active = bool(user.member_expires_at and user.member_expires_at > now)
    if member_active:
        if (user.member_calls_remaining or 0) > 0:
            user.member_calls_remaining -= 1
            db.add(KeepSeekUsage(user_id=user.id, source=source, cost_type="member"))
            db.commit()
            db.refresh(user)
            return {
                "allowed": True,
                "cost_type": "member",
                "member_calls_remaining": user.member_calls_remaining,
                "call_credits": user.call_credits or 0,
                "free_calls_remaining_today": max(FREE_DAILY_LIMIT - (user.free_calls_used or 0), 0),
            }
        if allow_credits and (user.call_credits or 0) > 0:
            user.call_credits -= 1
            db.add(KeepSeekUsage(user_id=user.id, source=source, cost_type="credit"))
            db.commit()
            db.refresh(user)
            return {
                "allowed": True,
                "cost_type": "credit",
                "member_calls_remaining": 0,
                "call_credits": user.call_credits,
                "free_calls_remaining_today": max(FREE_DAILY_LIMIT - (user.free_calls_used or 0), 0),
            }
        return {
            "allowed": False,
            "reason": "member_exhausted",
            "member_active": True,
            "member_calls_remaining": 0,
            "call_credits": user.call_credits or 0,
            "free_calls_remaining_today": max(FREE_DAILY_LIMIT - (user.free_calls_used or 0), 0),
        }

    if (user.free_calls_used or 0) < FREE_DAILY_LIMIT:
        user.free_calls_used = (user.free_calls_used or 0) + 1
        db.add(KeepSeekUsage(user_id=user.id, source=source, cost_type="free"))
        db.commit()
        db.refresh(user)
        return {
            "allowed": True,
            "cost_type": "free",
            "member_calls_remaining": user.member_calls_remaining or 0,
            "call_credits": user.call_credits or 0,
            "free_calls_remaining_today": FREE_DAILY_LIMIT - (user.free_calls_used or 0),
        }

    if allow_credits and (user.call_credits or 0) > 0:
        user.call_credits -= 1
        db.add(KeepSeekUsage(user_id=user.id, source=source, cost_type="credit"))
        db.commit()
        db.refresh(user)
        return {
            "allowed": True,
            "cost_type": "credit",
            "member_calls_remaining": user.member_calls_remaining or 0,
            "call_credits": user.call_credits,
            "free_calls_remaining_today": 0,
        }

    return {
        "allowed": False,
        "reason": "free_exhausted",
        "member_active": False,
        "member_calls_remaining": user.member_calls_remaining or 0,
        "call_credits": user.call_credits or 0,
        "free_calls_remaining_today": 0,
    }
