import httpx
from typing import Dict, Any
from app.config import settings
from .base import BaseProvider, ProviderError

class HuggingFaceProvider(BaseProvider):
    name = "HUGGINGFACE"

    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        if not settings.huggingface_api_key:
            raise ProviderError("HUGGINGFACE_API_KEY not set")

        # Simple text2text generation endpoint
        url = settings.huggingface_base_url.rstrip("/") + f"/models/{settings.huggingface_model}"

        payload = {
            "inputs": query,
            "parameters": {
                "max_new_tokens": 300,
                "return_full_text": False,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.huggingface_api_key}"},
                json=payload,
            )
            r.raise_for_status()
            data = r.json()

            # HF can return list[{"generated_text": "..."}] or dict errors
            if isinstance(data, list) and data:
                return data[0].get("generated_text", "").strip()
            if isinstance(data, dict) and "generated_text" in data:
                return str(data["generated_text"]).strip()
            return str(data).strip()
