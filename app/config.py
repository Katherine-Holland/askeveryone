from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # App
    app_env: str = os.getenv("APP_ENV", "dev")
    app_name: str = os.getenv("APP_NAME", "askeveryone")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_router_model: str = os.getenv("OPENAI_ROUTER_MODEL", "gpt-4o-mini")
    openai_ranker_model: str = os.getenv("OPENAI_RANKER_MODEL", "gpt-4o-mini")
    openai_answer_model: str = os.getenv("OPENAI_ANSWER_MODEL", "gpt-4o-mini")

    # Perplexity
    perplexity_api_key: str = os.getenv("PERPLEXITY_API_KEY", "")
    perplexity_base_url: str = os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
    perplexity_model: str = os.getenv("PERPLEXITY_MODEL", "sonar-pro")

    # Grok (xAI)
    grok_api_key: str = os.getenv("GROK_API_KEY", "")
    grok_base_url: str = os.getenv("GROK_BASE_URL", "https://api.x.ai")
    grok_model: str = os.getenv("GROK_MODEL", "grok-beta")

    # Anthropic (Claude)
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_base_url: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

    # Gemini (Google)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_base_url: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

    # LLaMA (via provider / OpenAI-compatible endpoint)
    llama_api_key: str = os.getenv("LLAMA_API_KEY", "")
    llama_base_url: str = os.getenv("LLAMA_BASE_URL", "")  # e.g. https://<provider>/v1
    llama_model: str = os.getenv("LLAMA_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct")

    # HuggingFace
    huggingface_api_key: str = os.getenv("HUGGINGFACE_API_KEY", "")
    huggingface_base_url: str = os.getenv("HUGGINGFACE_BASE_URL", "https://api-inference.huggingface.co")
    huggingface_model: str = os.getenv("HUGGINGFACE_MODEL", "google/flan-t5-large")

    # Database (Neon)
    database_url: str = os.getenv("DATABASE_URL", "")

settings = Settings()
