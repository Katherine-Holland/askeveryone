# app/api/shop.py

import os
import time
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

TOKEN_URL = os.getenv(
    "SHOPIFY_CATALOG_TOKEN_URL",
    "https://api.shopify.com/auth/access_token",
)
SEARCH_BASE = os.getenv(
    "SHOPIFY_CATALOG_SEARCH_BASE",
    "https://discover.shopifyapps.com",
)
SEARCH_URL = f"{SEARCH_BASE.rstrip('/')}/global/v2/search"

CLIENT_ID = os.getenv("SHOPIFY_CATALOG_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SHOPIFY_CATALOG_CLIENT_SECRET", "")

_cached_token: Optional[str] = None
_cached_expiry_epoch: float = 0.0


def _normalize_country_to_iso2(country: str) -> str:
    c = (country or "").strip().upper()
    if not c:
        return ""

    if c in {"UK", "U.K.", "U K", "UNITED KINGDOM", "GREAT BRITAIN", "BRITAIN", "ENGLAND"}:
        return "GB"

    if len(c) == 2 and c.isalpha():
        return c

    if c in {"USA", "UNITED STATES", "UNITED STATES OF AMERICA"}:
        return "US"

    return c


async def _get_bearer_token() -> str:
    global _cached_token, _cached_expiry_epoch

    now = time.time()
    if _cached_token and now < (_cached_expiry_epoch - 30):
        return _cached_token

    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Missing SHOPIFY_CATALOG_CLIENT_ID/SHOPIFY_CATALOG_CLIENT_SECRET in environment.",
        )

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            TOKEN_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        if r.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Shopify token request failed ({r.status_code}): {r.text}",
            )
        data = r.json()

    token = data.get("access_token")
    expires_in = data.get("expires_in", 0)

    if not token:
        raise HTTPException(
            status_code=502,
            detail="Shopify token response missing access_token.",
        )

    _cached_token = token
    try:
        _cached_expiry_epoch = now + float(expires_in)
    except Exception:
        _cached_expiry_epoch = now + 3000

    return token


def _first_str(*vals: Any) -> str:
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _format_price(amount: Any, currency: str) -> str:
    cur = (currency or "").strip().upper() or "USD"

    if isinstance(amount, dict):
        a = amount.get("amount") or amount.get("value")
        c = amount.get("currency") or amount.get("currency_code") or amount.get("currencyCode") or cur
        return _format_price(a, str(c))

    if isinstance(amount, (int, float)):
        if isinstance(amount, int) and abs(amount) >= 1000:
            return f"{amount/100.0:.2f} {cur}"
        return f"{amount} {cur}"

    if isinstance(amount, str) and amount.strip():
        return f"{amount.strip()} {cur}"

    return f"— {cur}"


def _extract_media_url(media: Any) -> str:
    """
    Tries multiple shapes seen in Shopify payloads.
    media can be:
      - [ { url: "..." } ]
      - [ { src: "..." } ]
      - [ { image: { url: "..." } } ]
      - [ { previewImage: { url: "..." } } ]
      - [ "https://..." ]
    """
    if isinstance(media, list) and media:
        first = media[0]

        if isinstance(first, str) and first.strip():
            return first.strip()

        if isinstance(first, dict):
            return _first_str(
                first.get("url"),
                first.get("src"),
                (first.get("image") or {}).get("url") if isinstance(first.get("image"), dict) else "",
                (first.get("previewImage") or {}).get("url") if isinstance(first.get("previewImage"), dict) else "",
            )
    return ""


def _extract_variant(up: Dict[str, Any]) -> Dict[str, Any]:
    variants = up.get("variants")
    if isinstance(variants, list) and variants and isinstance(variants[0], dict):
        return variants[0]
    return {}


def _to_shop_product(up: Dict[str, Any]) -> Dict[str, Any]:
    upid = str(up.get("id") or up.get("upid") or up.get("universal_product_id") or "")
    title = str(up.get("title") or up.get("name") or "Product")

    variant = _extract_variant(up)

    shop = variant.get("shop") if isinstance(variant.get("shop"), dict) else {}
    merchant_name = _first_str(shop.get("name")) or "Shopify"
    merchant_url = _first_str(shop.get("onlineStoreUrl"))

    image_url = _extract_media_url(up.get("media"))
    if not image_url:
        image_url = _extract_media_url(variant.get("media"))
    if not image_url:
        image_url = "/window.svg"

    pr = up.get("priceRange")
    if isinstance(pr, dict) and isinstance(pr.get("min"), dict):
        price_amount = pr["min"].get("amount")
        price_currency = pr["min"].get("currency") or "USD"
        price_str = _format_price(price_amount, str(price_currency))
    else:
        vp = variant.get("price")
        if isinstance(vp, dict):
            price_str = _format_price(vp.get("amount"), str(vp.get("currency") or "USD"))
        else:
            price_str = "— USD"

    href = _first_str(
        variant.get("variantUrl"),
        variant.get("checkoutUrl"),
        up.get("lookupUrl"),
        merchant_url,
    ) or "#"

    badges: List[str] = []

    return {
        "id": upid or title,
        "title": title,
        "price": price_str,
        "merchant": merchant_name,
        "imageUrl": image_url,
        "href": href,
        "badges": badges,
    }


@router.get("/shop/search")
async def shop_search(
    q: str = Query(..., description="Search query from UI (frontend uses q=...)"),
    country: Optional[str] = Query(None, description="ISO alpha-2 (e.g. GB, US). UK normalizes to GB."),
    gender: Optional[str] = Query(None),
    size: Optional[str] = Query(None),
    saleOnly: Optional[bool] = Query(None),
    pricePreset: Optional[str] = Query(None),
    giftMode: Optional[bool] = Query(None),
    limit: int = Query(10, ge=1, le=10),
    debug: bool = Query(False),
) -> Dict[str, Any]:
    token = await _get_bearer_token()

    params: Dict[str, Any] = {
        "query": q,
        "available_for_sale": 1,
        "limit": limit,
        "products_limit": limit,  # ✅ IMPORTANT: keep hydration consistent
    }

    if country:
        iso2 = _normalize_country_to_iso2(country)
        if iso2:
            params["ships_to"] = iso2

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            SEARCH_URL,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Shopify Catalog search failed ({r.status_code}): {r.text}",
        )

    data: Union[List[Any], Dict[str, Any]] = r.json()

    items: List[Dict[str, Any]] = []
    if isinstance(data, list):
        items = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        for key in ("results", "universal_products", "products", "data", "items"):
            v = data.get(key)
            if isinstance(v, list):
                items = [x for x in v if isinstance(x, dict)]
                break

    mapped = [_to_shop_product(x) for x in items[:limit]]

    if debug:
        return {
            "ok": True,
            "message": "DEBUG raw sample (first item only)",
            "query": q,
            "ships_to": params.get("ships_to"),
            "raw_first_item": items[0] if items else None,
            "mapped_first_item": mapped[0] if mapped else None,
        }

    return {
        "ok": True,
        "message": "Catalog API search",
        "query": q,
        "results": mapped,
    }
