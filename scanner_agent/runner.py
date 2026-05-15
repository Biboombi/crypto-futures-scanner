from __future__ import annotations

from datetime import datetime, timezone

from .config import Settings
from .exchanges import BinanceFuturesClient, BybitFuturesClient, ExchangeClient
from .models import MarketSnapshot, ScanResult
from .news import NewsClient
from .persistence import append_paper_trades, save_scan
from .scoring import score_snapshot
from .telegram import TelegramClient


class Scanner:
    def __init__(self, settings: Settings, exchanges: list[ExchangeClient] | None = None) -> None:
        self.settings = settings
        self.exchanges = exchanges or [
            BinanceFuturesClient(timeout=settings.http_timeout_seconds),
            BybitFuturesClient(timeout=settings.http_timeout_seconds),
        ]
        self.news = NewsClient(
            cryptopanic_api_key=settings.cryptopanic_api_key,
            newsapi_key=settings.newsapi_key,
            timeout=settings.http_timeout_seconds,
        )
        self.telegram = TelegramClient(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            timeout=settings.http_timeout_seconds,
        )

    def run_once(self) -> tuple[list[ScanResult], dict[str, str]]:
        results: list[ScanResult] = []
        for exchange in self.exchanges:
            markets = exchange.high_volume_markets(
                self.settings.min_quote_volume_usd,
                self.settings.max_symbols_per_exchange,
            )
            for market in markets:
                snapshot = exchange.build_snapshot(market)
                catalyst = self.news.catalyst_for(snapshot.base_asset)
                snapshot = _with_news(snapshot, catalyst)
                results.append(score_snapshot(snapshot))

        results.sort(key=lambda result: (result.score, result.quote_volume_24h), reverse=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        json_path, csv_path, latest_path = save_scan(results, self.settings.output_dir, stamp)
        paper_path = append_paper_trades(results, self.settings.output_dir)
        sent = self.telegram.send_alerts(results)
        artifacts = {
            "dry_run": str(self.settings.dry_run).lower(),
            "json": str(json_path),
            "csv": str(csv_path),
            "latest": str(latest_path),
            "paper_trades": str(paper_path),
            "telegram_sent": ", ".join(sent),
        }
        return results, artifacts


def _with_news(snapshot: MarketSnapshot, catalyst: str | None) -> MarketSnapshot:
    if catalyst == snapshot.news_catalyst:
        return snapshot
    return MarketSnapshot(
        exchange=snapshot.exchange,
        symbol=snapshot.symbol,
        base_asset=snapshot.base_asset,
        quote_asset=snapshot.quote_asset,
        last_price=snapshot.last_price,
        quote_volume_24h=snapshot.quote_volume_24h,
        price_change_15m=snapshot.price_change_15m,
        price_change_1h=snapshot.price_change_1h,
        price_change_4h=snapshot.price_change_4h,
        price_change_24h=snapshot.price_change_24h,
        volume_change_1h=snapshot.volume_change_1h,
        funding_rate=snapshot.funding_rate,
        open_interest=snapshot.open_interest,
        open_interest_change_1h=snapshot.open_interest_change_1h,
        support=snapshot.support,
        resistance=snapshot.resistance,
        breakout=snapshot.breakout,
        breakdown=snapshot.breakdown,
        news_catalyst=catalyst,
        data_warnings=snapshot.data_warnings,
    )
