# app/config.py
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except Exception:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)).strip())
    except Exception:
        return default


def _env_str(key: str, default: str = "") -> str:
    return os.getenv(key, default)


class Settings(BaseModel):
    # App
    app_env: str = _env_str("APP_ENV", "dev")
    app_name: str = _env_str("APP_NAME", "askeveryone")
    log_level: str = _env_str("LOG_LEVEL", "INFO")

    # OpenAI
    openai_api_key: str = _env_str("OPENAI_API_KEY", "")
    openai_router_model: str = _env_str("OPENAI_ROUTER_MODEL", "gpt-4o-mini")
    openai_ranker_model: str = _env_str("OPENAI_RANKER_MODEL", "gpt-4o-mini")
    openai_answer_model: str = _env_str("OPENAI_ANSWER_MODEL", "gpt-4o-mini")

    # Perplexity
    perplexity_api_key: str = _env_str("PERPLEXITY_API_KEY", "")
    perplexity_base_url: str = _env_str("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
    perplexity_model: str = _env_str("PERPLEXITY_MODEL", "sonar-pro")

    # Grok (xAI)
    grok_api_key: str = _env_str("GROK_API_KEY", "")
    grok_base_url: str = _env_str("GROK_BASE_URL", "https://api.x.ai")
    grok_model: str = _env_str("GROK_MODEL", "grok-beta")

    # Anthropic (Claude)
    anthropic_api_key: str = _env_str("ANTHROPIC_API_KEY", "")
    anthropic_base_url: str = _env_str("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    anthropic_model: str = _env_str("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    # Gemini (Google)
    gemini_api_key: str = _env_str("GEMINI_API_KEY", "")
    gemini_base_url: str = _env_str("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")
    gemini_model: str = _env_str("GEMINI_MODEL", "gemini-1.5-pro")

    # LLaMA (future)
    llama_api_key: str = _env_str("LLAMA_API_KEY", "")
    llama_base_url: str = _env_str("LLAMA_BASE_URL", "")
    llama_model: str = _env_str("LLAMA_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct")

    # HuggingFace (optional)
    huggingface_api_key: str = _env_str("HUGGINGFACE_API_KEY", "")
    huggingface_base_url: str = _env_str("HUGGINGFACE_BASE_URL", "https://api-inference.huggingface.co")
    huggingface_model: str = _env_str("HUGGINGFACE_MODEL", "google/flan-t5-large")

    # Database (Neon)
    database_url: str = _env_str("DATABASE_URL", "")

    # ---- Billing / credits ----
    # You asked: logged-in users get 5 free/day, anonymous gets 0 free.
    free_daily_limit: int = _env_int("FREE_DAILY_LIMIT", 5)         # free queries/day for logged-in free users
    credits_per_query: int = _env_int("CREDITS_PER_QUERY", 1)       # 1 credit = 1 query
    assumed_cost_per_query_usd: float = _env_float("ASSUMED_COST_PER_QUERY_USD", 0.005)

    # Hard anti-rinse limits (until we trust usage)
    # free users: cap per 24h (defaults to FREE_DAILY_LIMIT, but can be higher if you want)
    free_daily_cap: int = _env_int("FREE_DAILY_CAP", 5)
    # paid users: still capped per 24h initially
    paid_daily_cap: int = _env_int("PAID_DAILY_CAP", 50)

    # Token caps by tier (providers read meta["max_tokens"])
    # Keep these modest for now; you can increase later.
    max_tokens_free: int = _env_int("MAX_TOKENS_FREE", 350)
    max_tokens_paid: int = _env_int("MAX_TOKENS_PAID", 800)

    # Circuit breaker cooldown
    provider_cooldown_minutes: int = _env_int("PROVIDER_COOLDOWN_MINUTES", 10)

    # Stripe
    stripe_secret_key: str = _env_str("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = _env_str("STRIPE_WEBHOOK_SECRET", "")

    # Price IDs -> credits
    stripe_price_starter: str = _env_str("STRIPE_PRICE_STARTER", "")
    stripe_price_plus: str = _env_str("STRIPE_PRICE_PLUS", "")
    stripe_price_power: str = _env_str("STRIPE_PRICE_POWER", "")

    credits_starter: int = _env_int("CREDITS_STARTER", 200)
    credits_plus: int = _env_int("CREDITS_PLUS", 450)
    credits_power: int = _env_int("CREDITS_POWER", 1200)


settings = Settings()
