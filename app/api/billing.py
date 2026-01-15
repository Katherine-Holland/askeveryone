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
    def _mask(s: str) -> str:
        if not s:
            return ""
        return s[:6] + "…" + s[-4:]

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

        # if you have tier support in repo/models
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
    This expects your auth flow already supports creating user + linking to session,
    but we keep it minimal here: require session exists, and require user is already linked.
    If you already implemented a more complete version elsewhere, keep that one.
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

        # If your auth system links users to sessions via magic link,
        # this endpoint can just return ok and the UI will continue after login.
        # But your UI wants upgrade-first, so we create/get a user by email here.

        # 1) get or create user
        row = db.execute(
            text("select user_id from users where email=:e"),
            {"e": email},
        ).fetchone()

        if row and row[0]:
            user_id = row[0]
        else:
            # create user minimal (passwordless)
            user_id = uuid.uuid4()
            db.execute(
                text(
                    "insert into users (user_id, email) values (:uid, :e)"
                ),
                {"uid": user_id, "e": email},
            )
            db.commit()

        # 2) attach user to session
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

        # Resolve user from session (must be logged in / attached)
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

        # Fetch stripe_customer_id
        row2 = db.execute(
            text("select stripe_customer_id from users where user_id=:uid"),
            {"uid": user_id},
        ).fetchone()
        stripe_customer_id = row2[0] if row2 and row2[0] else None

        # Helper: create + persist a customer (fresh for current mode)
        def _create_and_store_customer() -> str:
            cust = stripe.Customer.create(
                metadata={"user_id": str(user_id)},
            )
            cid = cust["id"]
            db.execute(
                text("update users set stripe_customer_id=:cid where user_id=:uid"),
                {"cid": cid, "uid": user_id},
            )
            db.commit()
            return cid

        # If missing, create
        if not stripe_customer_id:
            stripe_customer_id = _create_and_store_customer()
        else:
            # Validate customer exists in current mode; if not, recreate.
            try:
                stripe.Customer.retrieve(stripe_customer_id)
            except Exception:
                # This is the exact “No such customer … exists in test/live mode” issue.
                stripe_customer_id = _create_and_store_customer()

        # Stripe-hosted Checkout success/cancel
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
                # helpful when debugging:
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

        # record event
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

            # store customer id
            stripe_customer_id = session.get("customer")
            if stripe_customer_id:
                db.execute(
                    text("update users set stripe_customer_id=:cid where user_id=:uid"),
                    {"cid": stripe_customer_id, "uid": user_id},
                )
                db.commit()

            sub_id = session.get("subscription")
            if sub_id:
                # requires your repo method; if not available, fall back to plan only
                try:
                    billing_repo.set_user_plan_and_tier(db, user_id, "paid", tier)
                except Exception:
                    billing_repo.set_user_plan(db, user_id, "paid")

                return {"ok": True, "event": event_type, "user_id": str(user_id), "plan": "paid", "tier": tier, "sub": sub_id}

            return {"ok": True, "event": event_type, "note": "no subscription on session"}

        # subscription lifecycle
        if event_type in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
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
                # keep current tier
                existing_tier = None
                try:
                    existing_tier = billing_repo.get_user_tier(db, user_id)
                    billing_repo.set_user_plan_and_tier(db, user_id, "paid", existing_tier)
                except Exception:
                    billing_repo.set_user_plan(db, user_id, "paid")

                return {"ok": True, "event": event_type, "user_id": str(user_id), "status": status, "plan": "paid", "tier": existing_tier}

            # inactive -> free, clear tier
            try:
                billing_repo.set_user_plan_and_tier(db, user_id, "free", None)
            except Exception:
                billing_repo.set_user_plan(db, user_id, "free")

            return {"ok": True, "event": event_type, "user_id": str(user_id), "status": status, "plan": "free", "tier": None}

        return {"ok": True, "ignored": event_type}

    finally:
        if db:
            db.close()
