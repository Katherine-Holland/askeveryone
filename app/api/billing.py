# app/api/billing.py
import uuid
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from app.config import settings
from app.db.session import get_session
from app.db import billing_repo

router = APIRouter(prefix="/billing", tags=["billing"])


def _price_to_credits(price_id: str) -> int:
    mapping = {
        settings.stripe_price_starter: settings.credits_starter,
        settings.stripe_price_plus: settings.credits_plus,
        settings.stripe_price_power: settings.credits_power,
    }
    return int(mapping.get(price_id, 0))


@router.get("/status")
async def billing_status(session_id: str):
    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        row = db.execute(
            text("select user_id from chat_sessions where session_id=:sid"),
            {"sid": session_id},
        ).fetchone()

        user_id = row[0] if row and row[0] else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Not logged in")

        billing_repo.ensure_wallet_and_plan(db, user_id)
        bal = billing_repo.get_balance(db, user_id)
        plan = billing_repo.get_user_plan(db, user_id)

        return {"ok": True, "user_id": str(user_id), "plan": plan, "credits_balance": bal}
    finally:
        if db:
            db.close()


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET not set")
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY not set")

    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    if not sig:
        raise HTTPException(status_code=400, detail="Missing Stripe signature header")

    import stripe  # type: ignore
    stripe.api_key = settings.stripe_secret_key

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig,
            secret=settings.stripe_webhook_secret,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe signature verification failed: {type(e).__name__}")

    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        event_id = event.get("id")
        event_type = event.get("type")

        # Idempotency table
        exists = db.execute(
            text("select 1 from stripe_events where event_id=:eid"),
            {"eid": event_id},
        ).fetchone()
        if exists:
            return {"ok": True, "skipped": True}

        # Record event first
        db.execute(
            text(
                "insert into stripe_events (event_id, type, raw_json) "
                "values (:eid, :t, :raw)"
            ),
            {"eid": event_id, "t": event_type, "raw": payload.decode("utf-8")[:5000]},
        )
        db.commit()

        if event_type != "checkout.session.completed":
            return {"ok": True, "ignored": event_type}

        session = event["data"]["object"]
        md = session.get("metadata") or {}

        user_id_str = md.get("user_id")
        price_id = md.get("price_id")

        if not user_id_str:
            raise HTTPException(status_code=400, detail="Missing metadata.user_id on Checkout Session")
        if not price_id:
            raise HTTPException(status_code=400, detail="Missing metadata.price_id on Checkout Session")

        try:
            user_id = uuid.UUID(user_id_str)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid metadata.user_id")

        credits = _price_to_credits(price_id)
        if credits <= 0:
            raise HTTPException(status_code=400, detail=f"Unknown price_id: {price_id}")

        billing_repo.ensure_wallet_and_plan(db, user_id)

        # Idempotent credit grant based on Stripe checkout session id
        checkout_id = str(session.get("id"))  # cs_test_...
        granted_now = billing_repo.grant_credits(
            db,
            user_id,
            credits,
            reason="purchase",
            ref=checkout_id,
        )

        return {"ok": True, "granted": credits if granted_now else 0, "duplicate": (not granted_now), "user_id": str(user_id)}

    finally:
        if db:
            db.close()
