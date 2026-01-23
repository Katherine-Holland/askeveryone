# app/api/shop.py

import os
import time
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# --- Shopify Catalog endpoints (per docs) ---
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

# Simple in-process token cache
_cached_token: Optional[str] = None
_cached_expiry_epoch: float = 0.0  # epoch seconds


def _normalize_country_to_iso2(country: str) -> str:
    """
    Catalog API expects ISO 3166-1 alpha-2 codes.
    Users type UK; Shopify expects GB.
    """
    c = (country or "").strip().upper()
    if not c:
        return ""

    if c in {"UK", "U.K.", "U K", "UNITED KINGDOM", "GREAT BRITAIN", "BRITAIN", "ENGLAND"}:
        return "GB"

    # Accept already-valid 2-letter codes
    if len(c) == 2 and c.isalpha():
        return c

    if c in {"USA", "UNITED STATES", "UNITED STATES OF AMERICA"}:
        return "US"
    if c in {"UAE", "UNITED ARAB EMIRATES"}:
        return "AE"

    return c


async def _get_bearer_token() -> str:
    """
    Get (and cache) a bearer token using client_credentials.
    """
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
        raise HTTPException(status_code=502, detail="Shopify token response missing access_token.")

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


def _extract_shop(up: Dict[str, Any]) -> Dict[str, Any]:
    """
    In your response, merchant is coming through as an object.
    Try common locations for shop/merchant details.
    """
    shop = up.get("shop") or up.get("merchant") or up.get("store")
    if isinstance(shop, dict):
        return shop

    # Sometimes the "offer" carries shop info
    offers = up.get("offers") or up.get("products") or up.get("variants") or []
    if isinstance(offers, list) and offers and isinstance(offers[0], dict):
        o = offers[0]
        s = o.get("shop") or o.get("merchant") or o.get("store")
        if isinstance(s, dict):
            return s

    return {}


def _extract_image_url(up: Dict[str, Any]) -> str:
    """
    Catalog payloads vary a lot. Try:
    - direct string keys (image_url etc.)
    - image dict
    - images list
    - offer-level image
    - nested media/featuredImage patterns
    """
    # 1) direct strings
    for k in (
        "image_url",
        "imageUrl",
        "thumbnail_url",
        "thumbnailUrl",
        "primary_image_url",
        "primaryImageUrl",
        "featured_image_url",
        "featuredImageUrl",
    ):
        v = up.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    # 2) image may be string or dict
    img = up.get("image") or up.get("featured_image") or up.get("featuredImage")
    if isinstance(img, str) and img.strip():
        return img.strip()
    if isinstance(img, dict):
        u = _first_str(img.get("url"), img.get("src"), img.get("originalSrc"))
        if u:
            return u

    # 3) images list
    imgs = up.get("images")
    if isinstance(imgs, list) and imgs:
        first = imgs[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, dict):
            u = _first_str(first.get("url"), first.get("src"), first.get("originalSrc"))
            if u:
                return u

    # 4) nested "media"
    media = up.get("media")
    if isinstance(media, dict):
        nodes = media.get("nodes") or media.get("edges")
        if isinstance(nodes, list) and nodes:
            first = nodes[0]
            if isinstance(first, dict):
                if "node" in first and isinstance(first["node"], dict):
                    first = first["node"]
                preview = first.get("previewImage") or first.get("image")
                if isinstance(preview, dict):
                    u = _first_str(preview.get("url"), preview.get("src"), preview.get("originalSrc"))
                    if u:
                        return u

    # 5) offer-level image fields
    offers = up.get("offers") or up.get("products") or up.get("variants") or []
    if isinstance(offers, list) and offers and isinstance(offers[0], dict):
        o = offers[0]
        for k in ("image_url", "imageUrl", "thumbnail_url", "thumbnailUrl"):
            v = o.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        oi = o.get("image") or o.get("featuredImage")
        if isinstance(oi, str) and oi.strip():
            return oi.strip()
        if isinstance(oi, dict):
            u = _first_str(oi.get("url"), oi.get("src"), oi.get("originalSrc"))
            if u:
                return u

    return ""


def _format_price(amount: Any, currency: str) -> str:
    """
    Your response shows integers like 15799 USD.
    That looks like minor units (cents/pence) in many commerce APIs.
    We'll do a safe heuristic:
      - if int and >= 1000 => treat as minor units, divide by 100
      - if already decimal/string => keep
    """
    cur = (currency or "").strip().upper() or "USD"

    # dict case: {amount, currency_code}
    if isinstance(amount, dict):
        a = amount.get("amount") or amount.get("value")
        c = amount.get("currency_code") or amount.get("currencyCode") or cur
        return _format_price(a, str(c))

    if isinstance(amount, (int, float)):
        if isinstance(amount, int) and abs(amount) >= 1000:
            val = amount / 100.0
            return f"{val:.2f} {cur}"
        return f"{amount} {cur}"

    if isinstance(amount, str) and amount.strip():
        return f"{amount.strip()} {cur}"

    return f"— {cur}"


def _to_shop_product(up: Dict[str, Any]) -> Dict[str, Any]:
    upid = str(up.get("id") or up.get("upid") or up.get("universal_product_id") or "")
    title = str(up.get("title") or up.get("name") or "Product")

    shop = _extract_shop(up)
    merchant_name = _first_str(shop.get("name"), shop.get("shop_name"), shop.get("merchant"))
    merchant_url = _first_str(shop.get("onlineStoreUrl"), shop.get("online_store_url"), shop.get("url"))

    image_url = _extract_image_url(up)

    # Offers
    offers = up.get("offers") or up.get("products") or up.get("variants") or []
    href = ""
    price_str = "— USD"
    badges: List[str] = []

    if isinstance(offers, list) and offers and isinstance(offers[0], dict):
        o = offers[0]

        # Prefer offer URL if present
        href = _first_str(o.get("url"), o.get("product_url"), o.get("href"))

        # Currency + price extraction
        currency = _first_str(o.get("currency"), o.get("currency_code"), o.get("currencyCode")) or "USD"
        raw_price = (
            o.get("price")
            or o.get("amount")
            or o.get("min_price")
            or o.get("price_min")
            or o.get("minPrice")
        )
        price_str = _format_price(raw_price, currency)

        # Sale badge
        compare_at = o.get("compare_at_price") or o.get("compareAtPrice") or o.get("compare_at")
        if compare_at:
            badges.append("Sale")

        # Offer shop override (if present)
        oshop = o.get("shop") or o.get("merchant") or o.get("store")
        if isinstance(oshop, dict):
            merchant_name = _first_str(oshop.get("name")) or merchant_name
            merchant_url = _first_str(oshop.get("onlineStoreUrl"), oshop.get("url")) or merchant_url

        # Offer image override
        if not image_url:
            image_url = _extract_image_url({"offers": [o]})  # reuse logic safely

    # If no offer URL, at least send them to the merchant store
    if not href:
        href = merchant_url or "#"

    if not merchant_name:
        merchant_name = "Shopify"

    if not image_url:
        image_url = "/window.svg"

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
    country: Optional[str] = Query(None, description="ISO alpha-2 (e.g. GB, US). UK will normalize to GB."),
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
        "products_limit": 10,
    }

    if country:
        iso2 = _normalize_country_to_iso2(country)
        if iso2:
            params["ships_to"] = iso2  # docs: ISO 3166 country code :contentReference[oaicite:1]{index=1}

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

    # API can return top-level list OR object wrapper. :contentReference[oaicite:2]{index=2}
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
