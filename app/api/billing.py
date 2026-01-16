# app/api/billing.py
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Body
from sqlalchemy import text

from app.config import settings
from app.db.session import get_session
from app.db import billing_repo

router = APIRouter(prefix="/billing", tags=["billing"])


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
        base = "https://www.seekle.io"
    return base.rstrip("/") + path


def _get_user_id_from_session(db, session_id: str):
    row = db.execute(
        text("select user_id from chat_sessions where session_id=:sid"),
        {"sid": session_id},
    ).fetchone()
    return row[0] if row and row[0] else None


def _get_stripe_customer_id(db, user_id):
    row = db.execute(
        text("select stripe_customer_id from users where user_id=:uid"),
        {"uid": user_id},
    ).fetchone()
    return row[0] if row and row[0] else None


# ----------------------------
# Diagnostics (helps a LOT)
# ----------------------------
@router.get("/diagnostics/stripe")
async def stripe_diagnostics():
    """
    Quick visibility:
    - are keys set?
    - do we have prices set?
    Does NOT call Stripe (safe).
    """
    return {
        "ok": True,
        "stripe_secret_key_set": bool(settings.stripe_secret_key),
        "stripe_webhook_secret_set": bool(settings.stripe_webhook_secret),
        "stripe_secret_key_prefix": (settings.stripe_secret_key[:7] if settings.stripe_secret_key else ""),
        "price_ids": {
            "starter": settings.stripe_price_starter,
            "plus": settings.stripe_price_plus,
            "power": settings.stripe_price_power,
        },
        "frontend_base_url": settings.frontend_base_url,
    }


# ----------------------------
# Status
# ----------------------------
@router.get("/status")
async def billing_status(session_id: str):
    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        user_id = _get_user_id_from_session(db, session_id)
        if not user_id:
            raise HTTPException(status_code=401, detail="Not logged in")

        billing_repo.ensure_wallet_and_plan(db, user_id)
        bal = billing_repo.get_balance(db, user_id)
        plan = billing_repo.get_user_plan(db, user_id)

        tier = None
        try:
            tier = billing_repo.get_user_tier(db, user_id)
        except Exception:
            tier = None

        return {
            "ok": True,
            "user_id": str(user_id),
            "plan": plan,  # free|paid
            "tier": tier,  # starter|plus|power|null
            "credits_balance": bal,
        }
    finally:
        if db:
            db.close()


# ----------------------------
# Start billing (upgrade-first)
# Frontend calls POST /api/billing/start with { session_id, email }
# ----------------------------
@router.post("/start")
async def billing_start(payload: dict = Body(...)):
    """
    Attach an email/user to a session so checkout can work even if they haven't done the free flow.
    """
    session_id = (payload.get("session_id") or "").strip()
    email = (payload.get("email") or "").strip().lower()

    if not session_id or not email:
        raise HTTPException(status_code=400, detail="session_id and email are required")

    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        # Ensure chat session exists
        db.execute(
            text(
                "insert into chat_sessions (session_id, is_anonymous) "
                "values (:sid, true) on conflict (session_id) do nothing"
            ),
            {"sid": session_id},
        )
        db.commit()

        # get or create user
        row = db.execute(
            text("select user_id from users where email=:e"),
            {"e": email},
        ).fetchone()

        if row and row[0]:
            user_id = row[0]
        else:
            user_id = uuid.uuid4()
            db.execute(
                text("insert into users (user_id, email) values (:uid, :e)"),
                {"uid": user_id, "e": email},
            )
            db.commit()

        # attach user to session
        db.execute(
            text("update chat_sessions set user_id=:uid, is_anonymous=false where session_id=:sid"),
            {"uid": user_id, "sid": session_id},
        )
        db.commit()

        billing_repo.ensure_wallet_and_plan(db, user_id)

        return {"ok": True, "user_id": str(user_id)}
    finally:
        if db:
            db.close()


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
    price_id = _plan_to_price(tier)

    if not price_id:
        raise HTTPException(
            status_code=500,
            detail=f"Missing Stripe price id for plan '{tier}'. Set STRIPE_PRICE_{tier.upper()}",
        )

    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        user_id = _get_user_id_from_session(db, session_id)
        if not user_id:
            raise HTTPException(status_code=401, detail="Not logged in")

        billing_repo.ensure_wallet_and_plan(db, user_id)

        import stripe  # type: ignore
        stripe.api_key = settings.stripe_secret_key

        stripe_customer_id = _get_stripe_customer_id(db, user_id)

        def _create_and_store_customer() -> str:
            cust = stripe.Customer.create(metadata={"user_id": str(user_id)})
            cid = cust["id"]
            db.execute(
                text("update users set stripe_customer_id=:cid where user_id=:uid"),
                {"cid": cid, "uid": user_id},
            )
            db.commit()
            return cid

        if not stripe_customer_id:
            stripe_customer_id = _create_and_store_customer()
        else:
            try:
                stripe.Customer.retrieve(stripe_customer_id)
            except Exception:
                stripe_customer_id = _create_and_store_customer()

        success_url = _safe_frontend_url("/billing/success?stripe_session_id={CHECKOUT_SESSION_ID}")
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
                "seekle_session_id": session_id,
            },
        )

        return {"ok": True, "url": checkout["url"]}
    finally:
        if db:
            db.close()


# ----------------------------
# ✅ Stripe Customer Portal (Manage plan / cancel / update card)
# ----------------------------
@router.post("/portal")
async def billing_portal(session_id: str):
    """
    Returns a Stripe Customer Portal URL so the user can:
    - cancel subscription
    - update payment method
    - view invoices
    """
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY not set")

    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        user_id = _get_user_id_from_session(db, session_id)
        if not user_id:
            raise HTTPException(status_code=401, detail="Not logged in")

        import stripe  # type: ignore
        stripe.api_key = settings.stripe_secret_key

        stripe_customer_id = _get_stripe_customer_id(db, user_id)
        if not stripe_customer_id:
            raise HTTPException(status_code=400, detail="No Stripe customer found for user")

        return_url = _safe_frontend_url("/")  # where to return after portal

        portal = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return {"ok": True, "url": portal["url"]}
    finally:
        if db:
            db.close()


# ----------------------------
# (Optional) Simple cancel endpoint
# If you add a UI button, this can cancel at period end.
# ----------------------------
@router.post("/cancel")
async def billing_cancel(session_id: str):
    """
    Cancels the active subscription at period end (keeps access until end of cycle).
    Prefer using the Portal in most cases.
    """
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY not set")

    db = None
    try:
        db = get_session()
        if not db:
            raise HTTPException(status_code=500, detail="DB not configured")

        user_id = _get_user_id_from_session(db, session_id)
        if not user_id:
            raise HTTPException(status_code=401, detail="Not logged in")

        import stripe  # type: ignore
        stripe.api_key = settings.stripe_secret_key

        # Try to find the subscription via Stripe customer (most reliable)
        stripe_customer_id = _get_stripe_customer_id(db, user_id)
        if not stripe_customer_id:
            raise HTTPException(status_code=400, detail="No Stripe customer found")

        subs = stripe.Subscription.list(customer=stripe_customer_id, status="all", limit=5)
        sub_id = None
        for s in (subs.get("data") or []):
            st = (s.get("status") or "").lower()
            if st in ("active", "trialing", "past_due"):
                sub_id = s.get("id")
                break

        if not sub_id:
            return {"ok": True, "note": "no_active_subscription"}

        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        return {"ok": True, "cancel_at_period_end": True, "subscription_id": sub_id}
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

    IMPORTANT:
    We *fail-open* on stripe_events logging so Stripe doesn't retry forever due to schema mismatch.
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

        # ✅ Safe event logging (fail-open)
        raw = payload.decode("utf-8")[:5000]
        try:
            db.execute(
                text("insert into stripe_events (event_id, type, raw_json) values (:eid, :t, :raw)"),
                {"eid": event_id, "t": event_type, "raw": raw},
            )
            db.commit()
        except Exception:
            db.rollback()
            try:
                db.execute(
                    text("insert into stripe_events (event_id, raw_json) values (:eid, :raw)"),
                    {"eid": event_id, "raw": raw},
                )
                db.commit()
            except Exception:
                db.rollback()
                # do not crash webhook

        def _user_id_from_customer(customer_id: str) -> Optional[uuid.UUID]:
            row = db.execute(
                text("select user_id from users where stripe_customer_id=:cid"),
                {"cid": customer_id},
            ).fetchone()
            return row[0] if row and row[0] else None

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

            stripe_customer_id = session.get("customer")
            if stripe_customer_id:
                try:
                    db.execute(
                        text("update users set stripe_customer_id=:cid where user_id=:uid"),
                        {"cid": stripe_customer_id, "uid": user_id},
                    )
                    db.commit()
                except Exception:
                    db.rollback()

            sub_id = session.get("subscription")
            if sub_id:
                try:
                    billing_repo.set_user_plan_and_tier(db, user_id, "paid", tier)
                except Exception:
                    try:
                        billing_repo.set_user_plan(db, user_id, "paid")
                    except Exception:
                        pass

                return {
                    "ok": True,
                    "event": event_type,
                    "user_id": str(user_id),
                    "plan": "paid",
                    "tier": tier,
                    "sub": sub_id,
                }

            return {"ok": True, "event": event_type, "note": "no subscription on session"}

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

            user_id = _user_id_from_customer(customer_id)
            if not user_id:
                return {"ok": True, "ignored": "unknown_customer"}

            is_active = status in ("active", "trialing")

            if is_active:
                existing_tier = None
                try:
                    existing_tier = billing_repo.get_user_tier(db, user_id)
                except Exception:
                    existing_tier = None

                try:
                    billing_repo.set_user_plan_and_tier(db, user_id, "paid", existing_tier)
                except Exception:
                    try:
                        billing_repo.set_user_plan(db, user_id, "paid")
                    except Exception:
                        pass

                return {
                    "ok": True,
                    "event": event_type,
                    "user_id": str(user_id),
                    "status": status,
                    "plan": "paid",
                    "tier": existing_tier,
                }

            try:
                billing_repo.set_user_plan_and_tier(db, user_id, "free", None)
            except Exception:
                try:
                    billing_repo.set_user_plan(db, user_id, "free")
                except Exception:
                    pass

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
