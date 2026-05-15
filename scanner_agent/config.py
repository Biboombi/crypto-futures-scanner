from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    dry_run: bool
    min_quote_volume_usd: float
    max_symbols_per_exchange: int
    output_dir: Path
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    cryptopanic_api_key: str | None
    newsapi_key: str | None
    http_timeout_seconds: float = 12.0

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            dry_run=env_bool("DRY_RUN", True),
            min_quote_volume_usd=env_float("MIN_QUOTE_VOLUME_USD", 50_000_000),
            max_symbols_per_exchange=env_int("MAX_SYMBOLS_PER_EXCHANGE", 50),
            output_dir=Path(os.getenv("OUTPUT_DIR", "data")),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
            cryptopanic_api_key=os.getenv("CRYPTOPANIC_API_KEY") or None,
            newsapi_key=os.getenv("NEWSAPI_KEY") or None,
        )
