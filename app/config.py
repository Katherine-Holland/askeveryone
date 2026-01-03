from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    # --------------------------------------------------
    # App
    # --------------------------------------------------
    app_env: str = os.getenv("APP_ENV", "dev")
    app_name: str = os.getenv("APP_NAME", "askeveryone")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    app_base_url: str = os.getenv("APP_BASE_URL", "https://seekle.ai")

    # --------------------------------------------------
    # OpenAI
    # --------------------------------------------------
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_router_model: str = os.getenv("OPENAI_ROUTER_MODEL", "gpt-4o-mini")
    openai_ranker_model: str = os.getenv("OPENAI_RANKER_MODEL", "gpt-4o-mini")
    openai_answer_model: str = os.getenv("OPENAI_ANSWER_MODEL", "gpt-4o-mini")

    # --------------------------------------------------
    # Perplexity
    # --------------------------------------------------
    perplexity_api_key: str = os.getenv("PERPLEXITY_API_KEY", "")
    perplexity_base_url: str = os.getenv(
        "PERPLEXITY_BASE_URL", "https://api.perplexity.ai"
    )
    perplexity_model: str = os.getenv("PERPLEXITY_MODEL", "sonar-pro")

    # --------------------------------------------------
    # Grok (xAI)
    # --------------------------------------------------
    grok_api_key: str = os.getenv("GROK_API_KEY", "")
    grok_base_url: str = os.getenv("GROK_BASE_URL", "https://api.x.ai")
    grok_model: str = os.getenv("GROK_MODEL", "grok-beta")

    # --------------------------------------------------
    # Anthropic (Claude)
    # --------------------------------------------------
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_base_url: str = os.getenv(
        "ANTHROPIC_BASE_URL", "https://api.anthropic.com"
    )
    anthropic_model: str = os.getenv(
        "ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"
    )

    # --------------------------------------------------
    # Gemini (Google)
    # --------------------------------------------------
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_base_url: str = os.getenv(
        "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"
    )
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

    # --------------------------------------------------
    # LLaMA (Together / OpenAI-compatible)
    # --------------------------------------------------
    llama_api_key: str = os.getenv("LLAMA_API_KEY", "")
    llama_base_url: str = os.getenv("LLAMA_BASE_URL", "")
    llama_model: str = os.getenv(
        "LLAMA_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct"
    )

    # --------------------------------------------------
    # HuggingFace (optional / paused)
    # --------------------------------------------------
    huggingface_api_key: str = os.getenv("HUGGINGFACE_API_KEY", "")
    huggingface_base_url: str = os.getenv(
        "HUGGINGFACE_BASE_URL", "https://api-inference.huggingface.co"
    )
    huggingface_model: str = os.getenv(
        "HUGGINGFACE_MODEL", "google/flan-t5-large"
    )

    # --------------------------------------------------
    # Database (Neon)
    # --------------------------------------------------
    database_url: str = os.getenv("DATABASE_URL", "")

    # --------------------------------------------------
    # Usage limits & billing logic
    # --------------------------------------------------
    free_daily_limit: int = int(os.getenv("FREE_DAILY_LIMIT", "5"))
    paid_daily_limit: int = int(os.getenv("PAID_DAILY_LIMIT", "50"))

    max_tokens_free: int = int(os.getenv("MAX_TOKENS_FREE", "500"))
    max_tokens_paid: int = int(os.getenv("MAX_TOKENS_PAID", "2000"))

    credits_per_query: int = int(os.getenv("CREDITS_PER_QUERY", "1"))
    internal_cost_per_credit_usd: float = float(
        os.getenv("INTERNAL_COST_PER_CREDIT_USD", "0.005")
    )

    # --------------------------------------------------
    # Stripe (payments)
    # --------------------------------------------------
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    stripe_price_id_starter: str = os.getenv("STRIPE_PRICE_ID_STARTER", "")
    stripe_price_id_plus: str = os.getenv("STRIPE_PRICE_ID_PLUS", "")
    stripe_price_id_power: str = os.getenv("STRIPE_PRICE_ID_POWER", "")


settings = Settings()
