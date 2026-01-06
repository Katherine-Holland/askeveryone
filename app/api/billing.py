# app/api/billing.py
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from app.config import settings
from app.db.session import get_session
from app.db import billing_repo

router = APIRouter(prefix="/billing", tags=["billing"])


def _plan_to_price(plan: str) -> str:
    plan = (plan or "").lower().strip()
    if plan == "starter":
        return settings.stripe_price_starter
    if plan == "plus":
        return settings.stripe_price_plus
    if plan == "power":
        return settings.stripe_price_power
    raise HTTPException(status_code=400, detail="Invalid plan. Use starter|plus|power")


def _safe_frontend_url(path: str) -> str:
    base = getattr(settings, "frontend_base_url", "") or getattr(settings, "FRONTEND_BASE_URL", "")  # tolerate either
    if not base:
        # fallback to same origin if you want, but better to set env var
        base = "https://askeveryone.onrender.com"
    return base.rstrip("/") + path


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


@router.post("/checkout")
async def create_checkout(session_id: str, plan: str):
    """
    Create a Stripe Checkout Session for subscriptions (Starter/Plus/Power).
    Returns: { ok: true, url: "https://checkout.stripe.com/..." }
    """
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY not set")

    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        # Resolve user from session (must be logged in)
        row = db.execute(
            text("select user_id from chat_sessions where session_id=:sid"),
            {"sid": session_id},
        ).fetchone()
        user_id = row[0] if row and row[0] else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Not logged in")

        # Ensure plan + wallet rows exist
        billing_repo.ensure_wallet_and_plan(db, user_id)

        import stripe  # type: ignore
        stripe.api_key = settings.stripe_secret_key

        price_id = _plan_to_price(plan)

        # Fetch stripe_customer_id from users table if present
        row2 = db.execute(
            text("select stripe_customer_id from users where user_id=:uid"),
            {"uid": user_id},
        ).fetchone()
        stripe_customer_id = row2[0] if row2 and row2[0] else None

        # Create customer if missing
        if not stripe_customer_id:
            cust = stripe.Customer.create(
                metadata={"user_id": str(user_id)},
            )
            stripe_customer_id = cust["id"]
            db.execute(
                text("update users set stripe_customer_id=:cid where user_id=:uid"),
                {"cid": stripe_customer_id, "uid": user_id},
            )
            db.commit()

        success_url = _safe_frontend_url("/billing/success?session_id={CHECKOUT_SESSION_ID}")
        cancel_url = _safe_frontend_url("/billing/cancel")

        # Create Checkout Session (subscription)
        checkout = stripe.checkout.Session.create(
            mode="subscription",
            customer=stripe_customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            allow_promotion_codes=True,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user_id),
                "plan": plan.lower().strip(),
                "price_id": price_id,
            },
        )

        return {"ok": True, "url": checkout["url"]}
    finally:
        if db:
            db.close()


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Subscription webhooks:
    - checkout.session.completed -> capture customer + subscription + price, mark paid
    - customer.subscription.created/updated/deleted -> keep plan accurate
    """
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

        # Idempotency
        exists = db.execute(
            text("select 1 from stripe_events where event_id=:eid"),
            {"eid": event_id},
        ).fetchone()
        if exists:
            return {"ok": True, "skipped": True}

        # Record event first (truncate raw for debugging)
        db.execute(
            text("insert into stripe_events (event_id, type, raw_json) values (:eid, :t, :raw)"),
            {"eid": event_id, "t": event_type, "raw": payload.decode("utf-8")[:5000]},
        )
        db.commit()

        # -----------------------------
        # Helper: set plan state in DB
        # -----------------------------
        def set_user_plan(user_id: uuid.UUID, plan_value: str) -> None:
            # You currently store only free/paid in user_plans.
            # If you want per-tier, we can add a tier column later.
            db.execute(
                text(
                    "insert into user_plans (user_id, plan) values (:uid, :p) "
                    "on conflict (user_id) do update set plan=:p, updated_at=now()"
                ),
                {"uid": user_id, "p": plan_value},
            )
            db.commit()

        # -----------------------------
        # checkout.session.completed
        # -----------------------------
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            md = session.get("metadata") or {}

            user_id_str = md.get("user_id")
            plan = (md.get("plan") or "").lower().strip()
            price_id = md.get("price_id")

            if not user_id_str:
                return {"ok": True, "ignored": "missing_user_id"}
            try:
                user_id = uuid.UUID(user_id_str)
            except Exception:
                return {"ok": True, "ignored": "bad_user_id"}

            # Store stripe_customer_id if returned
            stripe_customer_id = session.get("customer")
            if stripe_customer_id:
                db.execute(
                    text("update users set stripe_customer_id=:cid where user_id=:uid"),
                    {"cid": stripe_customer_id, "uid": user_id},
                )
                db.commit()

            # Mark paid if subscription exists
            # Checkout session contains subscription id in subscription mode
            sub_id = session.get("subscription")
            if sub_id:
                set_user_plan(user_id, "paid")
                return {"ok": True, "event": event_type, "user_id": str(user_id), "plan": "paid", "tier": plan, "sub": sub_id}

            # If it wasn't subscription mode, you can still support credit packs later:
            return {"ok": True, "event": event_type, "note": "no subscription on session"}

        # -----------------------------
        # Subscription lifecycle events
        # -----------------------------
        if event_type in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
            sub = event["data"]["object"]
            customer_id = sub.get("customer")
            status = (sub.get("status") or "").lower()

            # Find our user by stripe_customer_id
            if not customer_id:
                return {"ok": True, "ignored": "no_customer"}

            row = db.execute(
                text("select user_id from users where stripe_customer_id=:cid"),
                {"cid": customer_id},
            ).fetchone()
            if not row or not row[0]:
                return {"ok": True, "ignored": "unknown_customer"}

            user_id = row[0]

            # Active-like statuses
            is_active = status in ("active", "trialing")
            set_user_plan(user_id, "paid" if is_active else "free")

            return {"ok": True, "event": event_type, "user_id": str(user_id), "status": status, "plan": ("paid" if is_active else "free")}

        # Ignore the rest
        return {"ok": True, "ignored": event_type}

    finally:
        if db:
            db.close()
