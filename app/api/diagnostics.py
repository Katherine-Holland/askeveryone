from fastapi import APIRouter
import httpx
from app.config import settings

router = APIRouter(tags=["diagnostics"])


@router.get("/diagnostics/grok_ping")
async def diagnostics_grok_ping():
    if not settings.grok_api_key:
        return {"ok": False, "error": "GROK_API_KEY not set"}

    base_url = (settings.grok_base_url or "https://api.x.ai").rstrip("/")
    url = f"{base_url}/v1/models"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {settings.grok_api_key}"})
        return {"ok": r.status_code == 200, "status_code": r.status_code, "body_excerpt": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "detail": str(e)}
