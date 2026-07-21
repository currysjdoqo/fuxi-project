from __future__ import annotations

import base64
import json
import os
import secrets
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode, quote

import httpx

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import PaymentOrder, User
from utils.billing import PLAN_CONFIG, apply_referral_commission, purchase_membership

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    HAS_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover
    HAS_CRYPTOGRAPHY = False


PAYMENT_PROVIDER_ALIPAY = "alipay"
PAYMENT_PROVIDER_WECHAT = "wechat"
PRODUCT_TYPE_MEMBERSHIP = "membership"
PRODUCT_TYPE_BALANCE_TOPUP = "balance_topup"
ORDER_STATUS_PENDING = "pending"
ORDER_STATUS_PAID = "paid"
ORDER_STATUS_FAILED = "failed"


def _normalize_pem(value: str) -> str:
    return value.strip().replace("\\n", "\n")


def _require_crypto() -> None:
    if not HAS_CRYPTOGRAPHY:
        raise HTTPException(status_code=500, detail="cryptography dependency is required for payment signing")


def _get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "").strip()
    if required and not value:
        raise HTTPException(status_code=503, detail=f"Payment config missing: {name}")
    return value


def _money_str(amount_cents: int) -> str:
    return f"{Decimal(amount_cents) / Decimal(100):.2f}"


def generate_order_no() -> str:
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(4).upper()
    return f"FX{now}{suffix}"


def get_frontend_base_url() -> str:
    return _get_env("FRONTEND_BASE_URL", required=False) or _get_env("APP_BASE_URL")


def get_alipay_notify_url() -> str:
    configured = _get_env("ALIPAY_NOTIFY_URL", required=False)
    if configured:
        return configured
    return f"{_get_env('APP_BASE_URL').rstrip('/')}/api/billing/payments/alipay/notify"


def get_alipay_return_url() -> str:
    configured = _get_env("ALIPAY_RETURN_URL", required=False)
    if configured:
        return configured
    base = get_frontend_base_url().rstrip("/")
    return f"{base}/settings?payment_return=1"


def get_wechat_notify_url() -> str:
    configured = _get_env("WECHAT_NOTIFY_URL", required=False)
    if configured:
        return configured
    return f"{_get_env('APP_BASE_URL').rstrip('/')}/api/billing/payments/wechat/notify"


def alipay_is_configured() -> bool:
    return all(
        os.getenv(name, "").strip()
        for name in ("APP_BASE_URL", "ALIPAY_APP_ID", "ALIPAY_PRIVATE_KEY", "ALIPAY_PUBLIC_KEY")
    )


def wechat_is_configured() -> bool:
    return all(
        os.getenv(name, "").strip()
        for name in ("APP_BASE_URL", "WECHAT_APP_ID", "WECHAT_MCH_ID", "WECHAT_SERIAL_NO", "WECHAT_PRIVATE_KEY")
    )


def build_order_subject(product_type: str, plan: str | None = None, amount_cents: int | None = None) -> str:
    if product_type == PRODUCT_TYPE_MEMBERSHIP:
        config = PLAN_CONFIG.get(plan or "")
        if not config:
            raise HTTPException(status_code=400, detail="Invalid membership plan")
        return f"Study Hub Membership - {plan}"
    if product_type == PRODUCT_TYPE_BALANCE_TOPUP:
        return f"Study Hub Balance Top-up - {_money_str(amount_cents or 0)} CNY"
    raise HTTPException(status_code=400, detail="Invalid product type")


def resolve_order_amount(product_type: str, plan: str | None = None, amount_cents: int | None = None) -> int:
    if product_type == PRODUCT_TYPE_MEMBERSHIP:
        config = PLAN_CONFIG.get(plan or "")
        if not config:
            raise HTTPException(status_code=400, detail="Invalid membership plan")
        return int(config["price_cents"])
    if product_type == PRODUCT_TYPE_BALANCE_TOPUP:
        if amount_cents is None or amount_cents < 100 or amount_cents % 100 != 0:
            raise HTTPException(status_code=400, detail="Top-up amount must be at least 100 cents and divisible by 100")
        return int(amount_cents)
    raise HTTPException(status_code=400, detail="Invalid product type")


def create_payment_order(
    db: Session,
    user: User,
    provider: str,
    product_type: str,
    plan: str | None = None,
    amount_cents: int | None = None,
) -> PaymentOrder:
    if provider not in {PAYMENT_PROVIDER_ALIPAY, PAYMENT_PROVIDER_WECHAT}:
        raise HTTPException(status_code=400, detail="Unsupported payment provider")

    resolved_amount = resolve_order_amount(product_type, plan, amount_cents)
    subject = build_order_subject(product_type, plan, resolved_amount)
    order = PaymentOrder(
        order_no=generate_order_no(),
        user_id=user.id,
        provider=provider,
        product_type=product_type,
        plan=plan,
        amount_cents=resolved_amount,
        status=ORDER_STATUS_PENDING,
        subject=subject,
    )
    db.add(order)
    db.flush()
    if provider == PAYMENT_PROVIDER_ALIPAY:
        order.payment_url = build_alipay_page_pay_url(order)
    else:
        order.payment_url = build_wechat_native_pay_url(order)
    db.commit()
    db.refresh(order)
    return order


def _load_private_key():
    _require_crypto()
    private_key = _normalize_pem(_get_env("ALIPAY_PRIVATE_KEY"))
    return serialization.load_pem_private_key(private_key.encode("utf-8"), password=None)


def _load_public_key():
    _require_crypto()
    public_key = _normalize_pem(_get_env("ALIPAY_PUBLIC_KEY"))
    return serialization.load_pem_public_key(public_key.encode("utf-8"))


def sign_alipay_content(content: str) -> str:
    private_key = _load_private_key()
    signature = private_key.sign(
        content.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def verify_alipay_signature(params: dict[str, str]) -> bool:
    signature = params.get("sign", "")
    sign_type = params.get("sign_type", "")
    if not signature or sign_type.upper() != "RSA2":
        return False

    unsigned = {k: v for k, v in params.items() if k not in {"sign", "sign_type"} and v not in (None, "")}
    content = "&".join(f"{k}={unsigned[k]}" for k in sorted(unsigned))
    try:
        _load_public_key().verify(
            base64.b64decode(signature),
            content.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def build_alipay_page_pay_url(order: PaymentOrder) -> str:
    if not alipay_is_configured():
        raise HTTPException(status_code=503, detail="Alipay is not configured")

    biz_content = {
        "out_trade_no": order.order_no,
        "product_code": "FAST_INSTANT_TRADE_PAY",
        "total_amount": _money_str(order.amount_cents),
        "subject": order.subject,
    }
    params = {
        "app_id": _get_env("ALIPAY_APP_ID"),
        "method": "alipay.trade.page.pay",
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "notify_url": get_alipay_notify_url(),
        "return_url": get_alipay_return_url(),
        "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
    }
    content = "&".join(f"{k}={params[k]}" for k in sorted(params))
    params["sign"] = sign_alipay_content(content)
    gateway = _get_env("ALIPAY_GATEWAY", required=False) or "https://openapi.alipay.com/gateway.do"
    return f"{gateway}?{urlencode(params)}"


def _load_wechat_private_key():
    _require_crypto()
    private_key = _normalize_pem(_get_env("WECHAT_PRIVATE_KEY"))
    return serialization.load_pem_private_key(private_key.encode("utf-8"), password=None)


def _wechat_authorization(method: str, canonical_url: str, body: str = "") -> str:
    timestamp = str(int(datetime.utcnow().timestamp()))
    nonce_str = secrets.token_hex(16)
    message = f"{method}\n{canonical_url}\n{timestamp}\n{nonce_str}\n{body}\n"
    signature = _load_wechat_private_key().sign(
        message.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    signature_b64 = base64.b64encode(signature).decode("utf-8")
    return (
        'WECHATPAY2-SHA256-RSA2048 '
        f'mchid="{_get_env("WECHAT_MCH_ID")}",'
        f'nonce_str="{nonce_str}",'
        f'signature="{signature_b64}",'
        f'timestamp="{timestamp}",'
        f'serial_no="{_get_env("WECHAT_SERIAL_NO")}"'
    )


async def _wechat_request(method: str, canonical_url: str, json_body: dict | None = None) -> dict:
    if not wechat_is_configured():
        raise HTTPException(status_code=503, detail="WeChat Pay is not configured")

    body = json.dumps(json_body, ensure_ascii=False, separators=(",", ":")) if json_body is not None else ""
    gateway = _get_env("WECHAT_GATEWAY", required=False) or "https://api.mch.weixin.qq.com"
    headers = {
        "Authorization": _wechat_authorization(method, canonical_url, body),
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "study-hub-payments/1.0",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.request(
            method,
            f"{gateway}{canonical_url}",
            headers=headers,
            content=body.encode("utf-8") if body else None,
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"WeChat Pay request failed: HTTP {response.status_code} {response.text}")
    return response.json() if response.text else {}


def build_wechat_native_pay_url(order: PaymentOrder) -> str:
    import asyncio

    payload = {
        "appid": _get_env("WECHAT_APP_ID"),
        "mchid": _get_env("WECHAT_MCH_ID"),
        "description": order.subject,
        "out_trade_no": order.order_no,
        "notify_url": get_wechat_notify_url(),
        "amount": {
            "total": order.amount_cents,
            "currency": "CNY",
        },
    }
    result = asyncio.run(_wechat_request("POST", "/v3/pay/transactions/native", payload))
    code_url = result.get("code_url", "").strip()
    if not code_url:
        raise HTTPException(status_code=502, detail="WeChat Pay did not return a code_url")
    return code_url


def _wechat_query_order_sync(order_no: str) -> dict:
    import asyncio

    canonical_url = f"/v3/pay/transactions/out-trade-no/{quote(order_no, safe='')}?mchid={_get_env('WECHAT_MCH_ID')}"
    return asyncio.run(_wechat_request("GET", canonical_url))


def serialize_order(order: PaymentOrder) -> dict:
    return {
        "order_no": order.order_no,
        "provider": order.provider,
        "product_type": order.product_type,
        "plan": order.plan,
        "amount_cents": order.amount_cents,
        "status": order.status,
        "subject": order.subject,
        "payment_url": order.payment_url,
        "payment_mode": "redirect" if order.provider == PAYMENT_PROVIDER_ALIPAY else "wechat_native",
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def _credit_balance_topup(db: Session, user: User, amount_cents: int) -> None:
    user.balance_cents = (user.balance_cents or 0) + amount_cents
    db.add(user)
    from utils.billing import _log_wallet_tx  # local import avoids broader refactor

    _log_wallet_tx(
        db,
        user_id=user.id,
        source_user_id=user.id,
        amount_cents=amount_cents,
        tx_type="balance_topup",
        note="third-party payment",
    )
    apply_referral_commission(db, user, user.id, amount_cents)


def apply_paid_order(db: Session, order: PaymentOrder, provider_order_no: str | None = None, callback_payload: dict | None = None) -> PaymentOrder:
    if order.applied_at:
        return order

    user = db.query(User).filter(User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Order user not found")

    if order.product_type == PRODUCT_TYPE_MEMBERSHIP:
        purchase_membership(db, user, order.plan or "", payer_user_id=user.id)
    elif order.product_type == PRODUCT_TYPE_BALANCE_TOPUP:
        _credit_balance_topup(db, user, order.amount_cents)
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="Unsupported order type")

    db.refresh(user)
    order.status = ORDER_STATUS_PAID
    order.provider_order_no = provider_order_no or order.provider_order_no
    order.callback_payload = callback_payload or order.callback_payload
    order.paid_at = order.paid_at or datetime.utcnow()
    order.applied_at = datetime.utcnow()
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def mark_paid_from_alipay(db: Session, payload: dict[str, str]) -> PaymentOrder:
    if not verify_alipay_signature(payload):
        raise HTTPException(status_code=400, detail="Invalid Alipay signature")

    order_no = payload.get("out_trade_no", "").strip()
    trade_status = payload.get("trade_status", "").strip()
    trade_no = payload.get("trade_no", "").strip()
    total_amount = payload.get("total_amount", "").strip()

    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="Payment order not found")

    if trade_status not in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        return order

    if _money_str(order.amount_cents) != total_amount:
        raise HTTPException(status_code=400, detail="Payment amount mismatch")

    order.status = ORDER_STATUS_PAID
    order.provider_order_no = trade_no or order.provider_order_no
    order.callback_payload = dict(payload)
    order.paid_at = order.paid_at or datetime.utcnow()
    db.add(order)
    db.commit()
    db.refresh(order)
    return apply_paid_order(db, order, provider_order_no=trade_no, callback_payload=dict(payload))


def sync_wechat_order_status(db: Session, order: PaymentOrder) -> PaymentOrder:
    if order.provider != PAYMENT_PROVIDER_WECHAT or order.status == ORDER_STATUS_PAID:
        return order

    result = _wechat_query_order_sync(order.order_no)
    trade_state = result.get("trade_state", "").strip()
    transaction_id = result.get("transaction_id", "").strip()

    if trade_state == "SUCCESS":
        order.status = ORDER_STATUS_PAID
        order.provider_order_no = transaction_id or order.provider_order_no
        order.callback_payload = result
        order.paid_at = order.paid_at or datetime.utcnow()
        db.add(order)
        db.commit()
        db.refresh(order)
        return apply_paid_order(db, order, provider_order_no=transaction_id, callback_payload=result)

    if trade_state in {"CLOSED", "REVOKED", "PAYERROR"}:
        order.status = ORDER_STATUS_FAILED
        order.callback_payload = result
        db.add(order)
        db.commit()
        db.refresh(order)

    return order


def decrypt_wechat_callback_resource(payload: dict) -> dict | None:
    if not HAS_CRYPTOGRAPHY:
        return None
    api_v3_key = os.getenv("WECHAT_API_V3_KEY", "").strip()
    resource = payload.get("resource") or {}
    ciphertext = resource.get("ciphertext", "")
    nonce = resource.get("nonce", "")
    associated_data = resource.get("associated_data", "")
    if not api_v3_key or not ciphertext or not nonce:
        return None
    try:
        aesgcm = AESGCM(api_v3_key.encode("utf-8"))
        plain = aesgcm.decrypt(
            nonce.encode("utf-8"),
            base64.b64decode(ciphertext),
            associated_data.encode("utf-8") if associated_data else None,
        )
        return json.loads(plain.decode("utf-8"))
    except Exception:
        return None


def mark_paid_from_wechat_callback(db: Session, payload: dict) -> PaymentOrder | None:
    decrypted = decrypt_wechat_callback_resource(payload)
    if not decrypted:
        return None

    order_no = str(decrypted.get("out_trade_no", "")).strip()
    transaction_id = str(decrypted.get("transaction_id", "")).strip()
    trade_state = str(decrypted.get("trade_state", "")).strip()
    amount_info = decrypted.get("amount") or {}
    payer_total = int(amount_info.get("payer_total") or 0)

    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
    if not order:
        return None
    if trade_state != "SUCCESS":
        return order
    if payer_total != order.amount_cents:
        raise HTTPException(status_code=400, detail="Payment amount mismatch")

    order.status = ORDER_STATUS_PAID
    order.provider_order_no = transaction_id or order.provider_order_no
    order.callback_payload = payload
    order.paid_at = order.paid_at or datetime.utcnow()
    db.add(order)
    db.commit()
    db.refresh(order)
    return apply_paid_order(db, order, provider_order_no=transaction_id, callback_payload=payload)


def find_user_order(db: Session, user_id: int, order_no: str) -> PaymentOrder:
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no, PaymentOrder.user_id == user_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Payment order not found")
    if order.provider == PAYMENT_PROVIDER_WECHAT and order.status == ORDER_STATUS_PENDING:
        try:
            order = sync_wechat_order_status(db, order)
        except HTTPException:
            pass
    return order
