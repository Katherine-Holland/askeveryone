# app/api/shop.py

import os
import time
from typing import Any, Dict, List, Optional

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
    Catalog API expects ISO 3166-1 alpha-2 country codes.
    Users commonly type UK; Shopify expects GB.
    """
    c = (country or "").strip().upper()
    if not c:
        return c

    # Common aliases → ISO alpha-2
    if c in {"UK", "U.K.", "U K", "UNITED KINGDOM", "GREAT BRITAIN", "BRITAIN", "ENGLAND"}:
        return "GB"

    # Accept already-valid 2-letter codes as-is
    if len(c) == 2 and c.isalpha():
        return c

    # A few helpful extras (optional)
    if c in {"USA", "UNITED STATES", "UNITED STATES OF AMERICA"}:
        return "US"
    if c in {"UAE", "UNITED ARAB EMIRATES"}:
        return "AE"

    # If they pass something unexpected, just return uppercased raw.
    # Shopify may reject it; that's okay and will surface as a 502 with details.
    return c


async def _get_bearer_token() -> str:
    """
    Get (and cache) a bearer token using client_credentials.
    POST https://api.shopify.com/auth/access_token with:
      { client_id, client_secret, grant_type: "client_credentials" }
    """
    global _cached_token, _cached_expiry_epoch

    now = time.time()

    # Refresh a bit early to avoid edge expiry
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

    # expires_in is seconds until expiry
    try:
        _cached_expiry_epoch = now + float(expires_in)
    except Exception:
        _cached_expiry_epoch = now + 3000  # safe fallback

    return token


def _extract_image_url(up: Dict[str, Any]) -> str:
    """
    Catalog payload image shapes vary. Be tolerant:
      - direct string fields: image_url, thumbnail_url, etc.
      - image as dict or string
      - images as list[str] or list[dict]
      - offer-level images
    """
    image_url = ""

    # 1) direct string fields on universal product
    for k in (
        "image_url",
        "imageUrl",
        "thumbnail_url",
        "thumbnailUrl",
        "primary_image_url",
        "primaryImageUrl",
    ):
        v = up.get(k)
        if isinstance(v, str) and v.strip():
            image_url = v.strip()
            break

    # 2) "image" could be a dict OR a string URL
    if not image_url:
        img = up.get("image") or up.get("featured_image")
        if isinstance(img, str) and img.strip():
            image_url = img.strip()
        elif isinstance(img, dict):
            image_url = str(
                img.get("url") or img.get("src") or img.get("originalSrc") or ""
            ).strip()

    # 3) "images" could be list[dict] or list[str]
    if not image_url:
        imgs = up.get("images")
        if isinstance(imgs, list) and imgs:
            first = imgs[0]
            if isinstance(first, str) and first.strip():
                image_url = first.strip()
            elif isinstance(first, dict):
                image_url = str(
                    first.get("url") or first.get("src") or first.get("originalSrc") or ""
                ).strip()

    # 4) sometimes the offer carries the image
    if not image_url:
        offers = up.get("offers") or up.get("products") or up.get("variants") or []
        if isinstance(offers, list) and offers:
            o = offers[0] if isinstance(offers[0], dict) else {}

            for k in ("image_url", "imageUrl", "thumbnail_url", "thumbnailUrl"):
                v = o.get(k)
                if isinstance(v, str) and v.strip():
                    image_url = v.strip()
                    break

            if not image_url:
                oi = o.get("image")
                if isinstance(oi, str) and oi.strip():
                    image_url = oi.strip()
                elif isinstance(oi, dict):
                    image_url = str(
                        oi.get("url") or oi.get("src") or oi.get("originalSrc") or ""
                    ).strip()

            if not image_url:
                oimgs = o.get("images")
                if isinstance(oimgs, list) and oimgs:
                    f = oimgs[0]
                    if isinstance(f, str) and f.strip():
                        image_url = f.strip()
                    elif isinstance(f, dict):
                        image_url = str(
                            f.get("url") or f.get("src") or f.get("originalSrc") or ""
                        ).strip()

    return image_url


def _to_shop_product(up: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal mapping to your frontend ShopProduct type:
      { id, title, price, merchant, imageUrl, href, badges? }

    Catalog returns "Universal Products" that may contain offers.
    We'll pick a best-effort first offer if present.
    """
    upid = str(
        up.get("id") or up.get("upid") or up.get("universal_product_id") or ""
    )
    title = str(up.get("title") or up.get("name") or "Product")

    image_url = _extract_image_url(up)

    merchant = "Shopify"
    price_str = ""
    href = ""
    badges: List[str] = []

    offers = up.get("offers") or up.get("products") or up.get("variants") or []
    if isinstance(offers, list) and offers:
        o = offers[0] if isinstance(offers[0], dict) else {}

        merchant = str(
            o.get("shop_name")
            or o.get("merchant")
            or o.get("shop")
            or o.get("store_name")
            or merchant
        )

        # price fields vary; best-effort extraction
        price = (
            o.get("price")
            or o.get("amount")
            or o.get("min_price")
            or o.get("price_min")
            or o.get("minPrice")
        )
        currency = o.get("currency") or o.get("currency_code") or o.get("currencyCode") or "USD"

        if isinstance(price, dict):
            amount = price.get("amount") or price.get("value")
            currency = price.get("currency_code") or price.get("currencyCode") or currency
            if amount is not None:
                price_str = f"{amount} {currency}"
        elif price is not None:
            price_str = f"{price} {currency}"

        href = str(o.get("url") or o.get("product_url") or o.get("href") or "")

        # Sale badge (best-effort)
        compare_at = o.get("compare_at_price") or o.get("compareAtPrice") or o.get("compare_at")
        if compare_at:
            badges.append("Sale")

    # Fallbacks if missing
    if not price_str:
        price_str = "—"
    if not href:
        href = "#"
    if not image_url:
        image_url = "/window.svg"

    return {
        "id": upid or title,
        "title": title,
        "price": price_str,
        "merchant": merchant,
        "imageUrl": image_url,
        "href": href,
        "badges": badges,
    }


@router.get("/shop/search")
async def shop_search(
    q: str = Query(..., description="Search query from UI (frontend uses q=...)"),
    country: Optional[str] = Query(
        None, description="ISO 3166-1 alpha-2 (e.g. GB, US). UK will be normalized to GB."
    ),
    saleOnly: Optional[bool] = Query(None),
    pricePreset: Optional[str] = Query(None),
    giftMode: Optional[bool] = Query(None),
    limit: int = Query(10, ge=1, le=10),
) -> Dict[str, Any]:
    """
    Proxies Seekle Shop search to Shopify Catalog API global search.
    GET /global/v2/search?query=... with Authorization: Bearer <token>.
    """
    token = await _get_bearer_token()

    params: Dict[str, Any] = {
        "query": q,               # Catalog API expects `query`
        "available_for_sale": 1,  # aligns with “purchasable”
        "limit": limit,
        "products_limit": 10,
    }

    # Normalize country (UK -> GB, etc.) then send to Shopify as ships_to
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

    data = r.json()

    # Shopify Catalog search can return:
    #  - a top-level list of universal products
    #  - OR an object with a list under a key (results/universal_products/etc.)
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

    # Phase 1: leave saleOnly/pricePreset/giftMode for future filtering/ranking.
    return {
        "ok": True,
        "message": "Catalog API search",
        "query": q,
        "results": mapped,
    }
