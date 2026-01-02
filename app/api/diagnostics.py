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


@router.get("/diagnostics/claude_ping")
async def diagnostics_claude_ping():
    if not settings.anthropic_api_key:
        return {"ok": False, "error": "ANTHROPIC_API_KEY not set"}

    base_url = (settings.anthropic_base_url or "https://api.anthropic.com").rstrip("/")
    # Anthropic doesn’t provide a simple /models list like OpenAI.
    # So we do a tiny, low-cost messages call.
    url = f"{base_url}/v1/messages"

    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 8,
        "temperature": 0,
        "system": "Ping",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Ping"}]}],
    }

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(url, headers=headers, json=payload)
        return {"ok": r.status_code == 200, "status_code": r.status_code, "body_excerpt": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "detail": str(e)}
