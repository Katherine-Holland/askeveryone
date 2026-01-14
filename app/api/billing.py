# app/api/billing.py
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Request
from sqlalchemy import text

from app.config import settings
from app.db.session import get_session
from app.db import billing_repo

router = APIRouter(prefix="/billing", tags=["billing"])


# ----------------------------
# Helpers
# ----------------------------
def _normalize_plan(plan: str) -> str:
    p = (plan or "").lower().strip()
    if p in ("starter", "plus", "power"):
        return p
    raise HTTPException(status_code=400, detail="Invalid plan. Use starter|plus|power")


def _plan_to_price(plan: str) -> str:
    plan = _normalize_plan(plan)
    if plan == "starter":
        return settings.stripe_price_starter
    if plan == "plus":
        return settings.stripe_price_plus
    if plan == "power":
        return settings.stripe_price_power
    raise HTTPException(status_code=400, detail="Invalid plan. Use starter|plus|power")


def _safe_frontend_url(path: str) -> str:
    base = getattr(settings, "frontend_base_url", "") or getattr(settings, "FRONTEND_BASE_URL", "")
    if not base:
        base = "https://seekle.io"
    return base.rstrip("/") + path


# ----------------------------
# Status
# ----------------------------
@router.get("/status")
async def billing_status(session_id: str):
    """
    NOTE: This status endpoint expects a Seekle session_id (your UUID stored in localStorage),
    not a Stripe Checkout Session id (cs_...).
    """
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
        plan = billing_repo.get_user_plan(db, user_id)  # free|paid
        tier = billing_repo.get_user_tier(db, user_id)  # starter|plus|power|null

        return {
            "ok": True,
            "user_id": str(user_id),
            "plan": plan,
            "tier": tier,
            "credits_balance": bal,
        }
    finally:
        if db:
            db.close()


# ----------------------------
# Upgrade-first attach (missing piece)
# ----------------------------
@router.post("/start")
async def billing_start(payload: dict = Body(...)):
    """
    Upgrade-first flow:
    - Takes { session_id, email }
    - Finds/creates a user row for that email
    - Attaches chat_sessions.session_id -> user_id (marks is_anonymous=false)
    This allows checkout WITHOUT forcing a magic-link login first.
    """
    session_id = str(payload.get("session_id") or "").strip()
    email = str(payload.get("email") or "").strip().lower()

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")

    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        # Ensure session exists
        db.execute(
            text(
                "insert into chat_sessions (session_id, is_anonymous) "
                "values (:sid, true) on conflict (session_id) do nothing"
            ),
            {"sid": session_id},
        )
        db.commit()

        # Find user by email (or create)
        row = db.execute(
            text("select user_id from users where email=:e"),
            {"e": email},
        ).fetchone()

        if row and row[0]:
            user_id = row[0]
        else:
            user_id = uuid.uuid4()

            # If your users table requires extra columns, add defaults here.
            # This assumes (user_id, email) is sufficient.
            db.execute(
                text("insert into users (user_id, email) values (:uid, :e)"),
                {"uid": user_id, "e": email},
            )
            db.commit()

        # Attach session to user
        db.execute(
            text(
                "update chat_sessions set user_id=:uid, is_anonymous=false "
                "where session_id=:sid"
            ),
            {"uid": user_id, "sid": session_id},
        )
        db.commit()

        billing_repo.ensure_wallet_and_plan(db, user_id)

        return {"ok": True, "user_id": str(user_id)}
    finally:
        if db:
            db.close()


# ----------------------------
# Optional: quick browser probe to confirm routing is live
# (Stripe will POST to /webhook/stripe, so this doesn't affect webhooks)
# ----------------------------
@router.get("/webhook/stripe")
async def stripe_webhook_probe():
    return {"ok": True}


# ----------------------------
# Checkout
# ----------------------------
@router.post("/checkout")
async def create_checkout(session_id: str, plan: str):
    """
    Create a Stripe Checkout Session (Stripe-hosted page) for subscriptions.
    Returns: { ok: true, url: "https://checkout.stripe.com/..." }
    """
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY not set")

    tier = _normalize_plan(plan)

    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        # Must be attached via login OR /billing/start
        row = db.execute(
            text("select user_id from chat_sessions where session_id=:sid"),
            {"sid": session_id},
        ).fetchone()
        user_id = row[0] if row and row[0] else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Not logged in")

        billing_repo.ensure_wallet_and_plan(db, user_id)

        import stripe  # type: ignore
        stripe.api_key = settings.stripe_secret_key

        price_id = _plan_to_price(tier)

        # Existing stripe customer?
        row2 = db.execute(
            text("select stripe_customer_id from users where user_id=:uid"),
            {"uid": user_id},
        ).fetchone()
        stripe_customer_id = row2[0] if row2 and row2[0] else None

        if not stripe_customer_id:
            cust = stripe.Customer.create(metadata={"user_id": str(user_id)})
            stripe_customer_id = cust["id"]
            db.execute(
                text("update users set stripe_customer_id=:cid where user_id=:uid"),
                {"cid": stripe_customer_id, "uid": user_id},
            )
            db.commit()

        # IMPORTANT:
        # We want the frontend success page to know BOTH:
        # - stripe_session_id (cs_...) for display/troubleshooting
        # - seekle_session_id (your UUID) so it can call /billing/status correctly
        success_url = _safe_frontend_url(
            f"/billing/success?stripe_session_id={{CHECKOUT_SESSION_ID}}&session_id={session_id}"
        )
        cancel_url = _safe_frontend_url("/billing/cancel")

        checkout = stripe.checkout.Session.create(
            mode="subscription",
            customer=stripe_customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            allow_promotion_codes=True,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user_id),
                "tier": tier,
                "price_id": price_id,
                # nice to have for debugging (not required)
                "seekle_session_id": session_id,
            },
        )

        return {"ok": True, "url": checkout["url"]}
    finally:
        if db:
            db.close()


# ----------------------------
# Stripe Webhook
# ----------------------------
@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Subscription webhooks:
    - checkout.session.completed -> record paid + tier
    - customer.subscription.updated/deleted -> keep plan accurate
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
        raise HTTPException(
            status_code=400,
            detail=f"Stripe signature verification failed: {type(e).__name__}",
        )

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

        # Record event first (truncate raw)
        db.execute(
            text("insert into stripe_events (event_id, type, raw_json) values (:eid, :t, :raw)"),
            {"eid": event_id, "t": event_type, "raw": payload.decode("utf-8")[:5000]},
        )
        db.commit()

        def _user_id_from_customer(customer_id: str) -> Optional[uuid.UUID]:
            row = db.execute(
                text("select user_id from users where stripe_customer_id=:cid"),
                {"cid": customer_id},
            ).fetchone()
            return row[0] if row and row[0] else None

        # checkout.session.completed
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            md = session.get("metadata") or {}

            user_id_str = md.get("user_id")
            tier = (md.get("tier") or "").lower().strip() or None

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
            sub_id = session.get("subscription")
            if sub_id:
                billing_repo.set_user_plan_and_tier(db, user_id, "paid", tier)
                return {
                    "ok": True,
                    "event": event_type,
                    "user_id": str(user_id),
                    "plan": "paid",
                    "tier": tier,
                    "sub": sub_id,
                }

            return {"ok": True, "event": event_type, "note": "no subscription on session"}

        # subscription lifecycle
        if event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            sub = event["data"]["object"]
            customer_id = sub.get("customer")
            status = (sub.get("status") or "").lower()

            if not customer_id:
                return {"ok": True, "ignored": "no_customer"}

            user_id = _user_id_from_customer(str(customer_id))
            if not user_id:
                return {"ok": True, "ignored": "unknown_customer"}

            is_active = status in ("active", "trialing")

            if is_active:
                # keep existing tier (set in checkout.session.completed)
                existing_tier = billing_repo.get_user_tier(db, user_id)
                billing_repo.set_user_plan_and_tier(db, user_id, "paid", existing_tier)
                return {
                    "ok": True,
                    "event": event_type,
                    "user_id": str(user_id),
                    "status": status,
                    "plan": "paid",
                    "tier": existing_tier,
                }

            # not active -> free + clear tier
            billing_repo.set_user_plan_and_tier(db, user_id, "free", None)
            return {
                "ok": True,
                "event": event_type,
                "user_id": str(user_id),
                "status": status,
                "plan": "free",
                "tier": None,
            }

        return {"ok": True, "ignored": event_type}

    finally:
        if db:
            db.close()
