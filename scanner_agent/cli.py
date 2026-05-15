from __future__ import annotations

import argparse
import sys

from .config import Settings
from .runner import Scanner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crypto futures scanner and paper-trade agent.")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit.")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=None, help="Run without live execution.")
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="Disable the dry-run label. Live order placement is still not implemented.",
    )
    parser.add_argument("--min-volume", type=float, help="Minimum 24h quote volume in USD.")
    parser.add_argument("--limit", type=int, help="Maximum symbols per exchange.")
    args = parser.parse_args(argv)

    if not args.once:
        parser.error("Only scanner mode is available. Use --once.")

    settings = Settings.from_env()
    if args.dry_run is not None:
        settings = Settings(
            dry_run=args.dry_run,
            min_quote_volume_usd=settings.min_quote_volume_usd,
            max_symbols_per_exchange=settings.max_symbols_per_exchange,
            output_dir=settings.output_dir,
            telegram_bot_token=settings.telegram_bot_token,
            telegram_chat_id=settings.telegram_chat_id,
            cryptopanic_api_key=settings.cryptopanic_api_key,
            newsapi_key=settings.newsapi_key,
            http_timeout_seconds=settings.http_timeout_seconds,
        )
    if args.min_volume is not None:
        settings = Settings(
            dry_run=settings.dry_run,
            min_quote_volume_usd=args.min_volume,
            max_symbols_per_exchange=settings.max_symbols_per_exchange,
            output_dir=settings.output_dir,
            telegram_bot_token=settings.telegram_bot_token,
            telegram_chat_id=settings.telegram_chat_id,
            cryptopanic_api_key=settings.cryptopanic_api_key,
            newsapi_key=settings.newsapi_key,
            http_timeout_seconds=settings.http_timeout_seconds,
        )
    if args.limit is not None:
        settings = Settings(
            dry_run=settings.dry_run,
            min_quote_volume_usd=settings.min_quote_volume_usd,
            max_symbols_per_exchange=args.limit,
            output_dir=settings.output_dir,
            telegram_bot_token=settings.telegram_bot_token,
            telegram_chat_id=settings.telegram_chat_id,
            cryptopanic_api_key=settings.cryptopanic_api_key,
            newsapi_key=settings.newsapi_key,
            http_timeout_seconds=settings.http_timeout_seconds,
        )

    try:
        results, artifacts = Scanner(settings).run_once()
    except Exception as exc:  # noqa: BLE001 - CLI should produce a useful terminal error.
        print(f"scan failed: {exc}", file=sys.stderr)
        return 1

    print_summary(results, artifacts)
    return 0


def print_summary(results, artifacts: dict[str, str]) -> None:
    print(f"Scanned {len(results)} futures markets.")
    print(f"Mode: {'DRY-RUN' if artifacts.get('dry_run') == 'true' else 'NON-DRY-RUN'}")
    for result in results[:10]:
        print(
            f"{result.exchange:7} {result.symbol:14} {result.signal:8} "
            f"{result.score:3}/100 price={result.last_price:g} volume=${result.quote_volume_24h:,.0f}"
        )
    print(f"JSON: {artifacts['json']}")
    print(f"CSV: {artifacts['csv']}")
    print(f"Latest: {artifacts['latest']}")
    print(f"Paper trades: {artifacts['paper_trades']}")
    if artifacts.get("telegram_sent"):
        print(f"Telegram alerts sent: {artifacts['telegram_sent']}")
