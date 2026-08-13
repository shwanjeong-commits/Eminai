from dataclasses import dataclass
import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"


@dataclass(frozen=True)
class Settings:
    telegram_api_id: str
    telegram_api_hash: str
    telegram_channels: list[str]
    telegram_session_path: str
    openai_api_key: str
    ai_provider: str
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str
    azure_openai_api_version: str
    google_api_key: str
    google_ai_model: str
    github_models_token: str
    github_models_model: str
    ai_fallback_providers: list[str]
    telegram_bot_token: str
    telegram_alert_chat_id: str
    alert_min_impact: float
    alert_keywords: list[str]
    vapid_public_key: str
    vapid_private_key: str
    vapid_subject: str
    database_url: str


def normalize_channel(value: str) -> str:
    channel = value.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if channel.startswith(prefix):
            channel = channel.removeprefix(prefix)
    return channel.strip().lstrip("@").rstrip("/")


def load_dotenv(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_settings() -> Settings:
    load_dotenv()
    channels = [
        normalize_channel(channel)
        for channel in os.getenv("TELEGRAM_CHANNELS", "").split(",")
        if normalize_channel(channel)
    ]

    return Settings(
        telegram_api_id=os.getenv("TELEGRAM_API_ID", ""),
        telegram_api_hash=os.getenv("TELEGRAM_API_HASH", ""),
        telegram_channels=channels,
        telegram_session_path=os.getenv("TELEGRAM_SESSION_PATH", "telegram_news_session"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        ai_provider=os.getenv("AI_PROVIDER", "openai").lower(),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        google_api_key=os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_AI_API_KEY", ""),
        google_ai_model=os.getenv("GOOGLE_AI_MODEL", "gemini-2.5-flash"),
        github_models_token=os.getenv("GITHUB_MODELS_TOKEN", "") or os.getenv("GITHUB_TOKEN", ""),
        github_models_model=os.getenv(
            "GITHUB_MODELS_MODEL", "meta/llama-3.3-70b-instruct"
        ),
        ai_fallback_providers=[
            provider.strip().lower()
            for provider in os.getenv("AI_FALLBACK_PROVIDERS", "github").split(",")
            if provider.strip()
        ],
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_alert_chat_id=os.getenv("TELEGRAM_ALERT_CHAT_ID", ""),
        alert_min_impact=float(os.getenv("ALERT_MIN_IMPACT", "8") or 8),
        alert_keywords=[
            keyword.strip()
            for keyword in os.getenv("ALERT_KEYWORDS", "호르무즈,금리,반도체,이란,연준").split(",")
            if keyword.strip()
        ],
        vapid_public_key=os.getenv("VAPID_PUBLIC_KEY", ""),
        vapid_private_key=os.getenv("VAPID_PRIVATE_KEY", ""),
        vapid_subject=os.getenv("VAPID_SUBJECT", "mailto:admin@example.com"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/news.db"),
    )


def validate_settings(require_openai: bool = False) -> list[str]:
    settings = load_settings()
    missing = []

    if not settings.telegram_api_id:
        missing.append("TELEGRAM_API_ID")
    if not settings.telegram_api_hash:
        missing.append("TELEGRAM_API_HASH")
    if not settings.telegram_channels:
        missing.append("TELEGRAM_CHANNELS")
    if require_openai:
        if settings.ai_provider == "azure":
            if not settings.azure_openai_endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
            if not settings.azure_openai_api_key:
                missing.append("AZURE_OPENAI_API_KEY")
            if not settings.azure_openai_deployment:
                missing.append("AZURE_OPENAI_DEPLOYMENT")
        elif settings.ai_provider == "google":
            if not settings.google_api_key:
                missing.append("GEMINI_API_KEY")
        elif settings.ai_provider == "github":
            if not settings.github_models_token:
                missing.append("GITHUB_MODELS_TOKEN")
        elif not settings.openai_api_key:
            missing.append("OPENAI_API_KEY")

    return missing


if __name__ == "__main__":
    missing_settings = validate_settings()
    if missing_settings:
        print("missing: " + ", ".join(missing_settings))
    else:
        settings = load_settings()
        print(f"telegram channels: {', '.join(settings.telegram_channels)}")
        print(f"ai provider: {settings.ai_provider}")
        print(f"database: {settings.database_url}")
