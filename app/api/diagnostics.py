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

@router.get("/diagnostics/claude_models")
async def diagnostics_claude_models():
    """
    Lists Anthropic models available to the configured API key.
    Safe: returns IDs only (no keys).
    """
    if not settings.anthropic_api_key:
        return {"ok": False, "error": "ANTHROPIC_API_KEY not set"}

    base_url = (settings.anthropic_base_url or "https://api.anthropic.com").rstrip("/")
    url = f"{base_url}/v1/models"

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url, headers=headers)

        if r.status_code != 200:
            return {"ok": False, "status_code": r.status_code, "body_excerpt": r.text[:300]}

        data = r.json()
        ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
        return {
            "ok": True,
            "count": len(ids),
            "configured_model": settings.anthropic_model,
            "ids": ids[:50],  # cap output
        }
    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "detail": str(e)}

@router.get("/diagnostics/gemini_ping")
async def diagnostics_gemini_ping():
    if not settings.gemini_api_key:
        return {"ok": False, "error": "GEMINI_API_KEY not set"}

    base_url = (settings.gemini_base_url or "https://generativelanguage.googleapis.com").rstrip("/")
    configured = settings.gemini_model or "gemini-1.5-pro"

    url = f"{base_url}/v1beta/models"
    params = {"key": settings.gemini_api_key}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url, params=params)

        if r.status_code != 200:
            return {"ok": False, "status_code": r.status_code, "body_excerpt": r.text[:300]}

        data = r.json()
        models = data.get("models", [])

        # names are like "models/gemini-..."
        names = [m.get("name") for m in models if m.get("name")]

        # supportedGenerationMethods may exist (best signal)
        gen_models = []
        for m in models:
            methods = m.get("supportedGenerationMethods") or []
            if "generateContent" in methods:
                gen_models.append(m.get("name"))

        configured_full = f"models/{configured}"
        configured_found = configured_full in names
        configured_supports_generate = configured_full in gen_models

        # Return a helpful shortlist (strip "models/" prefix)
        gen_short = [(n or "").replace("models/", "") for n in gen_models[:25]]

        return {
            "ok": True,
            "status_code": 200,
            "configured_model": configured,
            "configured_model_found": configured_found,
            "configured_model_supports_generateContent": configured_supports_generate,
            "generateContent_models_suggested": gen_short,
        }

    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "detail": str(e)}

@router.get("/diagnostics/perplexity_ping")
async def diagnostics_perplexity_ping():
    if not settings.perplexity_api_key:
        return {"ok": False, "error": "PERPLEXITY_API_KEY not set"}

    base_url = (settings.perplexity_base_url or "https://api.perplexity.ai").rstrip("/")
    url = f"{base_url}/models"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {settings.perplexity_api_key}"})

        ok = r.status_code == 200
        excerpt = r.text[:250]

        configured = settings.perplexity_model or "sonar-pro"
        configured_found = None

        if ok:
            try:
                data = r.json()
                # Perplexity returns list-like models; normalize ids
                ids = []
                if isinstance(data, dict) and "data" in data:
                    ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
                elif isinstance(data, list):
                    ids = [m.get("id") for m in data if isinstance(m, dict) and m.get("id")]
                configured_found = configured in ids if ids else None
            except Exception:
                configured_found = None

        return {
            "ok": ok,
            "status_code": r.status_code,
            "configured_model": configured,
            "configured_model_found": configured_found,
            "body_excerpt": excerpt,
        }
    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "detail": str(e)}
