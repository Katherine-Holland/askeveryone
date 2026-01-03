from fastapi import APIRouter, HTTPException, Request
from app.config import settings

router = APIRouter(tags=["billing"])

@router.post("/billing/create-checkout-session")
async def create_checkout_session(pack: str, user_id: str):
    """
    Skeleton. We'll wire Stripe once keys + price IDs are set.
    pack: "starter" | "plus" | "power"
    """
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    # TODO: implement with stripe SDK
    return {"ok": False, "todo": "Implement Stripe checkout session creation"}

@router.post("/billing/webhook")
async def stripe_webhook(req: Request):
    """
    Skeleton webhook handler.
    Verify signature, then on successful payment:
      - add credits to wallet
      - set plan to paid if you want
    """
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook not configured")

    payload = await req.body()
    # TODO: verify stripe signature and parse events
    return {"ok": False, "todo": "Implement Stripe webhook verification + credit grant"}
